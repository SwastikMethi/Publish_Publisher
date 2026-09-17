#!/usr/bin/env python3
"""Render a finished demo video from an edit plan. Deterministic ffmpeg, nothing else.

  render.py plan.json

Plan (JSON):
{
  "output": "output/media/demo.mp4",
  "size": [1920, 1080],                 # output frame; zoom regions are fitted to this aspect
  "fps": 30,
  "transition": 0.5,                    # crossfade seconds between segments
  "font": "/System/Library/Fonts/Supplemental/Arial Bold.ttf",   # optional; a default is found
  "title": {"text": "Project Publisher", "sub": "repo to LinkedIn draft, one command", "duration": 2.5},
  "end":   {"text": "Day 1/30", "sub": "#buildinpublic", "duration": 2.0},
  "music": {"file": "assets/music/calm-01.mp3", "volume_db": -20},   # optional
  "segments": [
    {
      "src": "output/media/screen.mov",
      "start": 150.0, "end": 162.0,      # seconds in the source
      "speed": 1.0,                       # >1 fast-forwards; 6 turns a minute into ten seconds
      "zoom": {"x": 0, "y": 0, "w": 1200, "h": 640, "ease": 1.2},   # source px; region to land on
      "caption": "It reads the repo and writes a brief",
      "blur": "output/media/blur-150-162.json"   # from redact.py, or an inline list of boxes
    }
  ]
}

Every segment is rendered to its own intermediate, then the intermediates are joined with
crossfades, then music is mixed under the whole thing with fades. Boxes from redact.py are
blurred in source coordinates before the zoom, so they stay on the text as the frame moves.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stderr[-4000:])
        sys.exit(f"render.py: command failed: {' '.join(cmd[:3])} ...")
    return r.stdout


def probe(path, entry):
    return sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               entry, "-of", "csv=p=0", path]).strip()


def pick_font(plan):
    for f in [plan.get("font")] + FONT_CANDIDATES:
        if f and os.path.exists(f):
            return f
    sys.exit("render.py: no usable font found; set \"font\" in the plan")


def textfile(tmp, name, text):
    p = os.path.join(tmp, name + ".txt")
    with open(p, "w") as fh:
        fh.write(text)
    return p


def fit_region(z, sw, sh_, ow, oh):
    """Expand the zoom region to the output aspect, keeping its centre, inside the source."""
    cx, cy = z["x"] + z["w"] / 2, z["y"] + z["h"] / 2
    target = ow / oh
    w, h = z["w"], z["h"]
    if w / h < target:
        w = h * target
    else:
        h = w / target
    w, h = min(w, sw), min(h, sh_)
    x = min(max(0, cx - w / 2), sw - w)
    y = min(max(0, cy - h / 2), sh_ - h)
    return int(x) // 2 * 2, int(y) // 2 * 2, int(w) // 2 * 2, int(h) // 2 * 2


def card(tmp, out, plan, spec, font, fps, W, H):
    d = spec.get("duration", 2.5)
    title = textfile(tmp, out + "-t", spec["text"])
    chain = [f"color=c=0x0f1115:s={W}x{H}:r={fps}:d={d}",
             f"drawtext=fontfile='{font}':textfile='{title}':fontsize={int(H*0.075)}:"
             f"fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-{int(H*0.04)}"]
    if spec.get("sub"):
        sub = textfile(tmp, out + "-s", spec["sub"])
        chain.append(f"drawtext=fontfile='{font}':textfile='{sub}':fontsize={int(H*0.034)}:"
                     f"fontcolor=0xb9c0cc:x=(w-text_w)/2:y=(h/2)+{int(H*0.05)}")
    chain += [f"fade=t=in:d=0.4", f"fade=t=out:st={d-0.5}:d=0.5", "format=yuv420p"]
    path = os.path.join(tmp, out + ".mp4")
    sh(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", ",".join(chain),
        "-t", str(d), "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", path])
    return path, d


def segment(tmp, idx, seg, plan, font, fps, W, H):
    src = seg["src"]
    sw, sh_ = (int(v) for v in probe(src, "stream=width,height").split(",")[:2])
    start, end = float(seg["start"]), float(seg["end"])
    speed = float(seg.get("speed", 1.0))
    dur = (end - start) / speed

    boxes = seg.get("blur") or []
    if isinstance(boxes, str):
        with open(boxes) as fh:
            boxes = json.load(fh)
    # Keep only boxes that overlap this segment's source window.
    boxes = [b for b in boxes if b["t1"] > start and b["t0"] < end]

    # 1. Blur in source coordinates and source-local time (t runs from 0 at `start`).
    local = [{**b, "t0": max(0.0, b["t0"] - start), "t1": min(end - start, b["t1"] - start)}
             for b in boxes]
    parts, cur = blur_chain(local, "0:v", "k")

    # 2. Speed, then zoom (crop eases from the full frame to the region in output time).
    chain = [f"setpts=PTS/{speed}", f"fps={fps}"]
    z = seg.get("zoom")
    if z:
        zx, zy, zw, zh = fit_region(z, sw, sh_, W, H)
        ease = float(z.get("ease", 1.2))
        if ease > 0:
            s = f"(min(t/{ease},1)*min(t/{ease},1)*(3-2*min(t/{ease},1)))"
            chain.append(f"crop=w='iw-(iw-{zw})*{s}':h='ih-(ih-{zh})*{s}':x='{zx}*{s}':y='{zy}*{s}'")
        else:
            chain.append(f"crop={zw}:{zh}:{zx}:{zy}")
    chain.append(f"scale={W}:{H}:flags=lanczos,setsar=1")

    # 3. Caption bar and fade-in.
    cap = seg.get("caption")
    if cap:
        cf = textfile(tmp, f"cap{idx}", cap)
        bar = int(H * 0.11)
        chain.append(f"drawbox=x=0:y=ih-{bar}:w=iw:h={bar}:color=black@0.55:t=fill")
        chain.append(f"drawtext=fontfile='{font}':textfile='{cf}':fontsize={int(H*0.04)}:"
                     f"fontcolor=white:x={int(W*0.03)}:y=h-{int(bar*0.68)}:alpha='min(t/0.5,1)'")
    if speed > 1.5:
        ff = textfile(tmp, f"ff{idx}", f"{speed:g}x")
        chain.append(f"drawtext=fontfile='{font}':textfile='{ff}':fontsize={int(H*0.03)}:"
                     f"fontcolor=white@0.85:x=w-text_w-{int(W*0.02)}:y={int(H*0.03)}")
    chain.append("format=yuv420p")
    parts.append(f"[{cur}]" + ",".join(chain) + "[out]")

    path = os.path.join(tmp, f"seg{idx:02d}.mp4")
    sh(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(end - start), "-i", src,
        "-filter_complex", ";".join(parts), "-map", "[out]", "-an", "-r", str(fps),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", path])
    return path, dur, len(boxes)


def blur_chain(boxes, label_in, prefix):
    """Filter-graph parts that blur `boxes` ({x,y,w,h,t0,t1}) on stream label_in; returns
    (parts, final_label). Times are in the stream's own timeline."""
    parts, cur = [], label_in
    for i, b in enumerate(boxes):
        bw, bh = max(2, int(b["w"]) // 2 * 2), max(2, int(b["h"]) // 2 * 2)
        parts.append(f"[{cur}]split[{prefix}{i}a][{prefix}{i}b]")
        parts.append(f"[{prefix}{i}b]crop={bw}:{bh}:{int(b['x'])}:{int(b['y'])},"
                     f"boxblur=luma_radius=14:luma_power=2:chroma_radius=7[{prefix}{i}c]")
        parts.append(f"[{prefix}{i}a][{prefix}{i}c]overlay={int(b['x'])}:{int(b['y'])}:"
                     f"enable='between(t,{b['t0']:.3f},{b['t1']:.3f})'[{prefix}v{i}]")
        cur = f"{prefix}v{i}"
    return parts, cur


def patch(video, boxes_file, out):
    """Blur leftover boxes found by redact.py on a rendered video, in output coordinates and
    output time. Audio is copied through untouched."""
    with open(boxes_file) as fh:
        boxes = json.load(fh)
    if not boxes:
        shutil.copyfile(video, out)
        print("render.py --patch: no boxes, copied unchanged")
        return
    parts, last = blur_chain(boxes, "0:v", "p")
    parts.append(f"[{last}]format=yuv420p[out]")
    has_audio = "audio" in sh(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
                               "-of", "csv=p=0", video])
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", video, "-filter_complex", ";".join(parts),
           "-map", "[out]"] + (["-map", "0:a", "-c:a", "copy"] if has_audio else []) + \
          ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-movflags", "+faststart", out]
    sh(cmd)
    print(f"render.py --patch: blurred {len(boxes)} leftover boxes -> {out}")


def main():
    if len(sys.argv) == 5 and sys.argv[1] == "--patch":
        patch(sys.argv[2], sys.argv[3], sys.argv[4])
        return
    if len(sys.argv) != 2:
        sys.exit(__doc__ + "\n  render.py --patch rendered.mp4 leftover.json final.mp4")
    with open(sys.argv[1]) as fh:
        plan = json.load(fh)
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"render.py: {tool} not found on PATH")

    W, H = plan.get("size", [1920, 1080])
    fps = int(plan.get("fps", 30))
    T = float(plan.get("transition", 0.5))
    font = pick_font(plan)
    out = plan["output"]
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    tmp = tempfile.mkdtemp(prefix="pp-render-")
    try:
        clips = []
        if plan.get("title"):
            clips.append(card(tmp, "title", plan, plan["title"], font, fps, W, H))
        for i, seg in enumerate(plan["segments"]):
            p, d, nb = segment(tmp, i, seg, plan, font, fps, W, H)
            clips.append((p, d))
            print(f"  segment {i}: {d:.1f}s  speed {seg.get('speed', 1)}x  blur boxes {nb}"
                  f"  {seg.get('caption', '')}")
        if plan.get("end"):
            clips.append(card(tmp, "end", plan, plan["end"], font, fps, W, H))

        # Join with crossfades.
        inputs, parts = [], []
        for i, (p, _) in enumerate(clips):
            inputs += ["-i", p]
        cum = clips[0][1]
        prev = "0:v"
        for i in range(1, len(clips)):
            off = max(0.0, cum - T)
            lab = f"x{i}"
            parts.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={T}:offset={off:.3f}[{lab}]")
            prev = lab
            cum = cum + clips[i][1] - T
        total = cum
        video_label = f"[{prev}]" if parts else "[0:v]"

        # Music under everything, ducked and faded.
        music = plan.get("music") or {}
        mfile = music.get("file")
        if mfile and os.path.exists(mfile):
            inputs += ["-stream_loop", "-1", "-i", mfile]
            mi = len(clips)
            vol = float(music.get("volume_db", -20))
            parts.append(f"[{mi}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,volume={vol}dB,"
                         f"afade=t=in:d=1.5,afade=t=out:st={max(0, total-2.5):.3f}:d=2.5[a]")
            amap = ["-map", "[a]", "-c:a", "aac", "-b:a", "160k"]
        else:
            if mfile:
                print(f"  music file not found, rendering silent: {mfile}")
            amap = ["-an"]

        cmd = ["ffmpeg", "-v", "error", "-y"] + inputs
        if parts:
            cmd += ["-filter_complex", ";".join(parts), "-map", video_label]
        else:
            cmd += ["-map", "0:v"]
        cmd += amap + ["-r", str(fps), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                       "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-t", f"{total:.3f}", out]
        sh(cmd)
        print(f"render.py: {out}  {total:.1f}s  {W}x{H}@{fps}  {len(clips)} clips")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
