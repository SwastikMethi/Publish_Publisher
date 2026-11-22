#!/usr/bin/env python3
"""Checks assemble.py against small made-up frame folders. Run: python3 scripts/test_assemble.py

Needs ffmpeg and ffprobe, as assemble.py does. Everything is written to a temporary folder.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def frames(folder, count, size="320x180", skip=()):
    """Plain grey frames f00000.png ... in folder, leaving out the numbers in skip."""
    os.makedirs(folder, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=gray:s={size}:r=30",
                    "-frames:v", str(count), "-start_number", "0", os.path.join(folder, "f%05d.png")],
                   check=True)
    for n in skip:
        os.remove(os.path.join(folder, f"f{n:05d}.png"))


def plan(folder, **changes):
    """A two-second plan: 4 beats at 120 bpm, 30 fps, so 60 frames."""
    spec = {"output": os.path.join(folder, "demo.mp4"), "size": [320, 180], "fps": 30, "bpm": 120,
            "hook": {"lines": ["a"], "beats": 1}, "title": {"text": "b", "beats": 1},
            "scenes": [{"type": "chapter", "chapter": "c", "beats": 1}], "end": {"beats": 1}}
    spec.update(changes)
    path = os.path.join(folder, "plan.json")
    with open(path, "w") as fh:
        json.dump(spec, fh)
    return path


def assemble(plan_path):
    return subprocess.run([sys.executable, os.path.join(HERE, "assemble.py"), plan_path],
                          capture_output=True, text=True)


def probe(path, entries):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", entries, "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return out.split()


def main():
    with tempfile.TemporaryDirectory() as tmp:
        ok = os.path.join(tmp, "ok")
        frames(os.path.join(ok, "frames"), 60)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
                        os.path.join(ok, "music.mp3")], check=True)
        r = assemble(plan(ok, music={"file": os.path.join(ok, "music.mp3")}))
        assert r.returncode == 0, r.stderr
        video = os.path.join(ok, "demo.mp4")
        assert probe(video, "stream=codec_name") == ["h264", "aac"], probe(video, "stream=codec_name")
        assert probe(video, "stream=nb_frames")[0] == "60"
        assert abs(float(probe(video, "format=duration")[0]) - 2.0) < 0.06     # music cut to the video

        silent = os.path.join(tmp, "silent")
        frames(os.path.join(silent, "frames"), 60)
        r = assemble(plan(silent))
        assert r.returncode == 0, r.stderr
        assert "silent" in r.stdout
        assert probe(os.path.join(silent, "demo.mp4"), "stream=codec_name") == ["h264"]

        gap = os.path.join(tmp, "gap")
        frames(os.path.join(gap, "frames"), 60, skip=(17,))
        r = assemble(plan(gap))
        assert r.returncode != 0 and "f00017.png" in r.stderr, r.stderr
        assert not os.path.exists(os.path.join(gap, "demo.mp4"))

        extra = os.path.join(tmp, "extra")
        frames(os.path.join(extra, "frames"), 61)
        r = assemble(plan(extra))
        assert r.returncode != 0 and "more frames" in r.stderr, r.stderr

        big = os.path.join(tmp, "big")
        frames(os.path.join(big, "frames"), 60, size="640x360")
        r = assemble(plan(big))
        assert r.returncode != 0 and "640x360" in r.stderr, r.stderr

        loose = os.path.join(tmp, "loose")
        frames(os.path.join(loose, "frames"), 60)
        r = assemble(plan(loose, end={}))
        assert r.returncode != 0 and "beats" in r.stderr, r.stderr
        r = assemble(plan(loose, bpm=None))
        assert r.returncode != 0 and "bpm" in r.stderr, r.stderr
    print("test_assemble.py: all checks passed")


if __name__ == "__main__":
    main()
