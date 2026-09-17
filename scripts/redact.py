#!/usr/bin/env python3
"""Find sensitive text in a screen recording and emit blur boxes for render.py.

Samples frames from a time range, runs tesseract on each, matches every word against a set
of regular expressions, and writes a JSON list of boxes in source pixels with the source-time
window during which each must be blurred. Deterministic, no network, no browser.

Usage:
  redact.py --input rec.mov --start 150 --end 210 --out boxes.json
            [--fps 2] [--pad 10] [--time-pad 0.6] [--pattern REGEX ...] [--user NAME]

Requires: ffmpeg, ffprobe, tesseract on PATH.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

DEFAULT_PATTERNS = [
    r"/Users/",                 # macOS home paths
    r"/home/",                  # Linux home paths
    r"~/",                      # tilde paths
    r"[\w.+-]{2,}@[A-Za-z][\w-]*\.[A-Za-z]{2,}",  # email addresses (OCR reads a01 as a@1)
    r"github\.com/",            # repo URLs
    r"[\w-]+/[\w.-]+\.git",     # owner/repo.git
    r"(sk|ghp|xox[bap]|AKIA)[-_A-Za-z0-9]{8,}",  # token shapes
    r"eyJ[A-Za-z0-9_-]{10,}",   # JWT start
    r"\b\d{1,3}(\.\d{1,3}){3}\b",  # IPv4
    r"Bearer\s",
]


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def probe_size(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=width,height", "-of", "csv=p=0", path]).stdout.strip()
    w, h = out.split(",")[:2]
    return int(w), int(h)


def ocr_words(png):
    """Return [(x, y, w, h, text)] for a frame."""
    tsv = run(["tesseract", png, "-", "--psm", "6", "tsv"]).stdout
    words = []
    for line in tsv.splitlines()[1:]:
        cols = line.split("\t")
        if len(cols) < 12 or not cols[11].strip():
            continue
        try:
            x, y, w, h = (int(cols[6]), int(cols[7]), int(cols[8]), int(cols[9]))
        except ValueError:
            continue
        words.append((x, y, w, h, cols[11]))
    return words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--start", type=float, required=True)
    ap.add_argument("--end", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=float, default=4.0,
                    help="frames sampled per second of SOURCE time. Terminal text scrolls in "
                         "jumps, so sample densely: 4 covers a jump within a quarter second")
    ap.add_argument("--pad", type=int, default=12, help="pixels added around each box")
    ap.add_argument("--time-pad", type=float, default=-1,
                    help="seconds added before/after each hit; default is half a sample step, "
                         "so a box covers the gap to its neighbours but does not linger after "
                         "the text has scrolled away")
    ap.add_argument("--pattern", action="append", default=[], help="extra regex (repeatable)")
    ap.add_argument("--user", default="", help="username to redact wherever it appears")
    ap.add_argument("--ocr-scale", type=float, default=0.5,
                    help="downscale frames before OCR for speed; 0.5 is fine for terminal text")
    args = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe", "tesseract"):
        if not shutil.which(tool):
            sys.exit(f"redact.py: {tool} not found on PATH")

    patterns = [re.compile(p, re.I) for p in DEFAULT_PATTERNS + args.pattern]
    if args.user:
        patterns.append(re.compile(re.escape(args.user), re.I))

    W, H = probe_size(args.input)
    is_image = args.input.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    tmp = tempfile.mkdtemp(prefix="pp-redact-")
    try:
        k = args.ocr_scale
        if is_image:
            # A still is one frame; --start/--end/--fps are ignored and one box set is emitted.
            run(["ffmpeg", "-v", "error", "-y", "-i", args.input, "-vf", f"scale=iw*{k}:-1",
                 os.path.join(tmp, "f00001.png")])
            args.start, args.end, args.fps = 0.0, 1.0, 1.0
        else:
            run(["ffmpeg", "-v", "error", "-y", "-ss", str(args.start), "-t",
                 str(args.end - args.start), "-i", args.input,
                 "-vf", f"fps={args.fps},scale=iw*{k}:-1", os.path.join(tmp, "f%05d.png")])
        frames = sorted(f for f in os.listdir(tmp) if f.endswith(".png"))
        if not frames:
            sys.exit("redact.py: no frames extracted; check --start/--end against the file")
        raw = []
        for i, f in enumerate(frames):
            t = args.start + i / args.fps
            for x, y, w, h, text in ocr_words(os.path.join(tmp, f)):
                if any(p.search(text) for p in patterns):
                    raw.append({"x": int(x / k), "y": int(y / k), "w": int(w / k) + 2,
                                "h": int(h / k) + 2, "t": t, "text": text})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # Merge hits that sit in the same place on consecutive samples into one interval.
    step = 1.0 / args.fps
    if args.time_pad < 0:
        # Bias toward over-blurring. A box that lingers on harmless text for half a second is
        # invisible at fast-forward speed; a path that shows for one frame is a leak.
        args.time_pad = max(0.6, 2 * step + 0.05)
    merged = []
    for hit in sorted(raw, key=lambda r: (r["t"], r["y"], r["x"])):
        for m in merged:
            same_place = abs(m["x"] - hit["x"]) < 12 and abs(m["y"] - hit["y"]) < 8
            # Bridge up to two missed samples: OCR drops a static word now and then.
            adjacent = hit["t"] - m["t1"] <= 3 * step + 1e-6
            if same_place and adjacent:
                m["t1"] = hit["t"]
                m["w"] = max(m["w"], hit["w"])
                m["h"] = max(m["h"], hit["h"])
                break
        else:
            merged.append({**hit, "t0": hit["t"], "t1": hit["t"]})

    boxes = []
    for m in merged:
        x = max(0, m["x"] - args.pad)
        y = max(0, m["y"] - args.pad)
        w = min(W - x, m["w"] + 2 * args.pad)
        h = min(H - y, m["h"] + 2 * args.pad)
        boxes.append({
            "x": x, "y": y, "w": w, "h": h,
            "t0": round(max(args.start, m["t0"] - args.time_pad), 2),
            "t1": round(min(args.end, m["t1"] + step + args.time_pad), 2),
            "why": m["text"][:60],
        })

    with open(args.out, "w") as fh:
        json.dump(boxes, fh, indent=1)
    print(f"redact.py: {len(raw)} hits in {len(frames)} frames -> {len(boxes)} boxes -> {args.out}")
    for b in boxes[:12]:
        print(f"  {b['t0']:>7.1f}-{b['t1']:<7.1f} ({b['x']},{b['y']} {b['w']}x{b['h']})  {b['why']}")
    if len(boxes) > 12:
        print(f"  ... {len(boxes) - 12} more")


if __name__ == "__main__":
    main()
