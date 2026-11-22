#!/usr/bin/env python3
"""Join the rendered frames and the music into the finished video.

  assemble.py plan.json [--frames DIR]

The frames are the animation's, one PNG per frame, named f00000.png, f00001.png and so on, in
DIR (default: a "frames" folder beside the plan). The plan gives the size, the frame rate and
the length: its beats at its bpm. Every frame must be there and be the plan's size, or nothing
is written. The video is plan "output": H.264 with AAC sound, ready for a feed.

The music is plan music.file, cut to the video's length and faded out over its last second
and a half; a track shorter than the video is looped. With no such file the video is silent,
and the script says so.

A plan that leaves out bpm, or the beats of any scene, is refused: the animation, the music
and this script must all count the same beats, and a default is where they would part.

Requires ffmpeg and ffprobe on PATH.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys


def fail(message):
    sys.exit("assemble.py: " + message)


def total_beats(plan):
    parts = [("hook", plan.get("hook")), ("title", plan.get("title"))]
    parts += [(f"scene {i + 1}", scene) for i, scene in enumerate(plan.get("scenes") or [])]
    parts.append(("end", plan.get("end")))
    total = 0
    for name, spec in parts:
        if spec is None:
            continue
        beats = spec.get("beats")
        if not isinstance(beats, (int, float)) or beats <= 0:
            fail(f'the plan\'s {name} has no "beats"; give every part its beats')
        total += beats
    if total == 0:
        fail("the plan has no hook, title, scenes or end")
    return total


def frame_size(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0:s=x", path], capture_output=True, text=True).stdout.strip()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--frames", default=None)
    args = ap.parse_args()
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            fail(f"{tool} not found on PATH")
    with open(args.plan) as fh:
        plan = json.load(fh)
    for key in ("output", "size", "fps", "bpm"):
        if not plan.get(key):
            fail(f'the plan has no "{key}"')
    folder = args.frames or os.path.join(os.path.dirname(os.path.abspath(args.plan)), "frames")
    width, height = plan["size"]
    fps = plan["fps"]
    seconds = total_beats(plan) * 60.0 / plan["bpm"]
    count = int(seconds * fps + 0.5)          # rounded as the animation rounds it

    def frame(n):
        return os.path.join(folder, f"f{n:05d}.png")

    missing = [n for n in range(count) if not os.path.exists(frame(n))]
    if missing:
        fail(f"{len(missing)} of {count} frames are missing from {folder}; the first is "
             f"{os.path.basename(frame(missing[0]))}. Render them, then run this again.")
    if os.path.exists(frame(count)):
        fail(f"{folder} holds more frames than the plan's {count}. If the plan changed after "
             "rendering, empty the folder and render again.")
    for n in (0, count // 2, count - 1):
        size = frame_size(frame(n))
        if size != f"{width}x{height}":
            fail(f"{os.path.basename(frame(n))} is {size}, and the plan says {width}x{height}. Set the "
                 "browser's viewport to the plan's size and take screenshots with scale 'css'.")

    out = plan["output"]
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", os.path.join(folder, "f%05d.png")]
    music = plan.get("music") or {}
    track = music.get("file")
    if track and os.path.exists(track):
        volume = float(music.get("volume_db", 0))
        cmd += ["-stream_loop", "-1", "-i", track, "-filter:a",
                f"atrim=0:{seconds:.3f},asetpts=PTS-STARTPTS,volume={volume}dB,"
                f"afade=t=in:d=0.05,afade=t=out:st={max(0.0, seconds - 1.5):.3f}:d=1.5",
                "-c:a", "aac", "-b:a", "192k"]
    else:
        cmd += ["-an"]
        print("  music: " + (f"{track} not found, " if track else "none in the plan, ") + "the video is silent")
    cmd += ["-frames:v", str(count), "-t", f"{seconds:.3f}", "-r", str(fps), "-c:v", "libx264",
            "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode:
        if os.path.exists(out):
            os.remove(out)
        fail("ffmpeg failed:\n" + done.stderr[-2000:])
    print(f"assemble.py: {out}  {count} frames  {seconds:.1f}s  {width}x{height} at {fps} fps")


if __name__ == "__main__":
    main()
