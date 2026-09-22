#!/usr/bin/env python3
"""Render a finished demo video from an edit plan. Deterministic ffmpeg, nothing else.

  render.py plan.json
  render.py --patch rendered.mp4 leftover.json final.mp4

The finished video is a designed piece, not a screen dump: a hook card, a title on the first
beat drop, numbered chapters with the footage in a rounded card beside a large caption, a
stats interstitial with counting numbers, an end card that asks a question, a progress bar
along the bottom, and every cut on a beat of the music.

Plan (JSON):
{
  "output": "output/media/demo.mp4",
  "size": [1920, 1080], "fps": 30,
  "bpm": 125,                            # the beat grid; scene lengths are given in beats
  "brand": {"name": "AI Job Orient", "day": "Day 2/30"},      # small footer while chapters play
  "theme": {"accent": "0xF59E0B", "accent2": "0x2DD4BF"},     # optional
  "font": "...Bold.ttf", "font_regular": "...", "font_mono": "...",   # optional; defaults found
  "music": {"file": "output/media/music.mp3", "volume_db": 0},       # from compose.py, or a licensed track

  "hook":  {"lines": ["Applying to jobs", "is a full-time job."],
            "sub": "So I built one that does it. And asks before every submit.", "beats": 6},
  "title": {"text": "AI Job Orient",
            "sub": ["Finds the jobs, scores them, tailors your resume,",
                    "and waits for your yes before anything is submitted."], "beats": 6},
  "scenes": [
    {"type": "footage", "layout": "side", "chapter": "Search",
     "src": "output/media/raw-screen.mov", "start": 118.0, "end": 136.0,
     "crop": {"x": 1480, "y": 300, "w": 1900, "h": 1300},    # source px; fitted to the card
     "caption": ["Searches LinkedIn", "and Naukri, logs", "every posting"],
     "beats": 10, "blur": "output/media/blur-118-136.json"},
    {"type": "stats", "label": "This run, start to finish",
     "items": [[4, "postings found"], [3, "shortlisted"], [1, "below threshold"], [0, "auto-submitted"]],
     "highlight": 3, "note": "Every 'Awaiting approval' status still needs a human yes.", "beats": 8},
    {"type": "footage", "layout": "wide", "chapter": "Approve", "src": "...", "start": 466, "end": 480,
     "crop": {"x": 0, "y": 0, "w": 3456, "h": 1480},
     "caption": ["Three tailored packages wait for approval.", "Nothing goes out without my yes."],
     "beats": 10}
  ],
  "end": {"text": "Day 2/30", "sub": "#buildinpublic",
          "question": "Would you let it press Apply for you?", "beats": 8}
}

A footage scene's speed is derived: (end - start) / scene length, so cuts always land on the
grid. Blur boxes from redact.py are applied in source coordinates and source time, before the
speed change and the crop, so they stay on the text. "layout": "side" puts a 1180x780 card on
the right with up to four caption lines on the left; "wide" puts a 1680x720 card on top with
one or two caption lines under it (for terminal output that spans the whole screen).
"""
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

BOLD_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    "/usr/share/fonts/opentype/urw-base35/NimbusSans-Bold.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
REGULAR_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    "/usr/share/fonts/opentype/urw-base35/NimbusSans-Regular.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
MONO_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/opentype/urw-base35/NimbusMonoPS-Bold.otf",
]

WHITE, MUTED, INK = "white", "0x9AA3B8", "0x0B1020"
PREROLL = 45.0   # seconds decoded before a scene so a sparse recording has a frame to show


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stderr[-4000:])
        sys.exit(f"render.py: command failed: {' '.join(cmd[:3])} ...")
    return r.stdout


def probe(path, entry):
    return sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               entry, "-of", "csv=p=0", path]).strip()


def pick(plan_key, candidates, plan):
    for f in [plan.get(plan_key)] + candidates:
        if f and os.path.exists(f):
            return f
    sys.exit(f"render.py: no usable font found; set \"{plan_key}\" in the plan")


class Ctx:
    """Everything a scene needs: sizes, fonts, colours, the beat, temp dir, design scale."""

    def __init__(self, plan, tmp):
        self.W, self.H = plan.get("size", [1920, 1080])
        self.fps = int(plan.get("fps", 30))
        self.bpm = float(plan.get("bpm", 125))
        self.beat = 60.0 / self.bpm
        self.k = self.W / 1920.0                     # design scale; layout is drawn at 1920x1080
        self.bold = pick("font", BOLD_CANDIDATES, plan)
        self.regular = pick("font_regular", REGULAR_CANDIDATES, plan)
        self.mono = pick("font_mono", MONO_CANDIDATES, plan)
        theme = plan.get("theme") or {}
        self.accent = theme.get("accent", "0xF59E0B")
        self.accent2 = theme.get("accent2", "0x2DD4BF")
        self.tmp = tmp
        self.n = 0
        self.bg = self.make_bg()
        self.cards = {}

    def px(self, v):
        return int(round(v * self.k))

    def textfile(self, text):
        self.n += 1
        p = os.path.join(self.tmp, f"t{self.n}.txt")
        with open(p, "w") as fh:
            fh.write(text)
        return p

    # ---- static assets, built once with ffmpeg ----
    def make_bg(self):
        """Deep navy gradient with an amber glow top-right, a teal glow bottom-left, fine noise."""
        W, H = self.W, self.H
        p = os.path.join(self.tmp, "bg.png")
        r = f"clip(12-5*Y/{H} + 245*0.22*exp(-((X-{W*0.78})^2+(Y-{H*0.14})^2)/({W*0.47})^2) + 45*0.16*exp(-((X-{W*0.10})^2+(Y-{H*0.93})^2)/({W*0.47})^2),0,255)"
        g = f"clip(16-7*Y/{H} + 158*0.22*exp(-((X-{W*0.78})^2+(Y-{H*0.14})^2)/({W*0.47})^2) + 212*0.16*exp(-((X-{W*0.10})^2+(Y-{H*0.93})^2)/({W*0.47})^2),0,255)"
        b = f"clip(34-14*Y/{H} + 11*0.22*exp(-((X-{W*0.78})^2+(Y-{H*0.14})^2)/({W*0.47})^2) + 191*0.16*exp(-((X-{W*0.10})^2+(Y-{H*0.93})^2)/({W*0.47})^2),0,255)"
        sh(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r=1:d=1",
            "-vf", f"format=rgb24,geq=r='{r}':g='{g}':b='{b}',noise=alls=5:allf=u", "-frames:v", "1", p])
        return p

    def card_assets(self, cw, ch):
        """Rounded mask and soft shadow for a footage card of cw x ch."""
        if (cw, ch) in self.cards:
            return self.cards[(cw, ch)]
        r = self.px(22)
        mask = os.path.join(self.tmp, f"mask{cw}x{ch}.png")
        rr = (f"if(gt(hypot(max(0\\,abs(X-W/2)-(W/2-{r}))\\,max(0\\,abs(Y-H/2)-(H/2-{r})))\\,{r})\\,0\\,255)")
        sh(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=white:s={cw}x{ch}:r=1:d=1",
            "-vf", f"format=gray,geq=lum='{rr}'", "-frames:v", "1", mask])
        pad = self.px(60)
        shadow = os.path.join(self.tmp, f"shadow{cw}x{ch}.png")
        sw, shh = cw + 2 * pad, ch + 2 * pad
        sh(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", "1", "-i", mask,
            "-f", "lavfi", "-t", "1", "-i", f"color=c=black:s={sw}x{shh}:r=1",
            "-filter_complex", f"[0:v]format=gray,pad={sw}:{shh}:{pad}:{pad+self.px(18)}:black,"
                               f"gblur=sigma={self.px(26)},lutyuv=y='val*0.72'[a];[1:v][a]alphamerge[out]",
            "-map", "[out]", "-frames:v", "1", shadow])
        self.cards[(cw, ch)] = (mask, shadow)
        return mask, shadow


# ---------- text and bars (all animate in: fade + rise) ----------
def text(ctx, s, size, color, x, y, font=None, t0=0.0, rise=26, dur=0.35, extra=""):
    font = font or ctx.bold
    a = f"min(1\\,max(0\\,(t-{t0:.3f})/{dur}))"
    yy = f"{ctx.px(y)}+{ctx.px(rise)}*pow(max(0\\,1-(t-{t0:.3f})/{dur})\\,2)"
    xx = x if isinstance(x, str) else str(ctx.px(x))
    return (f"drawtext=fontfile='{font}':textfile='{ctx.textfile(s)}':fontsize={ctx.px(size)}"
            f":fontcolor={color}:x={xx}:y='{yy}':alpha='{a}'{extra}")


class Bars:
    """Accent bars that grow in. Each becomes a colour input, scaled per frame, overlaid."""

    def __init__(self):
        self.items = []

    def add(self, x, y, w, h, color, t0=0.0, dur=0.45):
        self.items.append((x, y, w, h, color, t0, dur))


def render_scene(ctx, out, dur, inputs, graph, layers, bars):
    """graph must end in [base]; layers are drawtext filters applied to it; bars overlaid last."""
    fc = graph + ";[base]" + ",".join(["null"] + [l for l in layers if l]) + "[v0]"
    inputs = list(inputs)
    cur = "v0"
    for i, (x, y, w, h, color, t0, d) in enumerate(bars.items):
        idx = inputs.count("-i")
        inputs += ["-f", "lavfi", "-t", f"{dur+0.5:.3f}", "-i", f"color=c={color}:s={w}x{h}:r={ctx.fps}"]
        fc += (f";[{idx}:v]scale=w='max(2\\,{w}*min(1\\,max(0\\,(t-{t0:.3f})/{d})))':h={h}:eval=frame[bar{i}];"
               f"[{cur}][bar{i}]overlay=x={x}:y={y}:eval=frame:shortest=1[v{i+1}]")
        cur = f"v{i+1}"
    fc += f";[{cur}]format=yuv420p[v]"
    sh(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", fc, "-map", "[v]",
        "-t", f"{dur:.3f}", "-r", str(ctx.fps), "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "17", "-pix_fmt", "yuv420p", out])


def bg_inputs(ctx, dur):
    return ["-loop", "1", "-framerate", str(ctx.fps), "-t", f"{dur+0.5:.3f}", "-i", ctx.bg]


# ---------- card scenes ----------
def scene_hook(ctx, spec, out):
    dur = spec.get("beats", 6) * ctx.beat
    lines = spec.get("lines") or [spec.get("text", "")]
    bars, layers = Bars(), []
    bars.add(ctx.px(80), ctx.px(300), ctx.px(120), ctx.px(6), ctx.accent, 0.05)
    size = 96 if max(len(l) for l in lines) <= 22 else 80
    for i, l in enumerate(lines[:3]):
        layers.append(text(ctx, l, size, WHITE, 80, 340 + i * (size + 14), t0=0.15 + i * 0.2, rise=40))
    if spec.get("sub"):
        layers.append(text(ctx, spec["sub"], 40, MUTED, 80, 340 + len(lines[:3]) * (size + 14) + 50,
                           font=ctx.regular, t0=0.35 + len(lines[:3]) * 0.2 + 0.4, rise=20))
    render_scene(ctx, out, dur, bg_inputs(ctx, dur), "[0:v]null[base]", layers, bars)
    return dur


def scene_title(ctx, spec, out, brand):
    dur = spec.get("beats", 6) * ctx.beat
    sub = spec.get("sub") or []
    if isinstance(sub, str):
        sub = [sub]
    size = 150 if len(spec["text"]) <= 16 else (120 if len(spec["text"]) <= 22 else 96)
    bars, layers = Bars(), []
    layers.append(text(ctx, spec["text"], size, WHITE, 80, 330, t0=0.05, rise=50, dur=0.45))
    bars.add(ctx.px(80), ctx.px(520), ctx.px(1760), ctx.px(5), ctx.accent, 0.25, 0.7)
    for i, s in enumerate(sub[:2]):
        layers.append(text(ctx, s, 42, MUTED, 80, 560 + i * 56, font=ctx.regular, t0=0.55 + i * 0.15, rise=20))
    foot = "  ·  ".join(x for x in (brand.get("day"), brand.get("tag", "#buildinpublic")) if x)
    if foot:
        layers.append(text(ctx, foot, 28, ctx.accent2, 80, 960, t0=1.0, rise=10))
    render_scene(ctx, out, dur, bg_inputs(ctx, dur), "[0:v]null[base]", layers, bars)
    return dur


def scene_stats(ctx, spec, out):
    dur = spec.get("beats", 8) * ctx.beat
    items = spec["items"][:4]
    hl = spec.get("highlight")
    bars, layers = Bars(), []
    layers.append(text(ctx, spec.get("label", "This run"), 30, ctx.accent2, 80, 200, t0=0.1, rise=12))
    bars.add(ctx.px(80), ctx.px(246), ctx.px(140), ctx.px(4), ctx.accent, 0.15)
    colw = 1760 // max(1, len(items))
    for i, (val, label) in enumerate(items):
        x, t0 = 80 + i * colw, 0.3 + i * 0.15
        if isinstance(val, (int, float)) and float(val).is_integer():
            # count up from 0 at seven steps a second
            e = f"%{{eif\\:min({int(val)}\\,floor(max(0\\,(t-{t0:.3f}))*7))\\:d}}"
            layers.append(f"drawtext=fontfile='{ctx.bold}':text='{e}':fontsize={ctx.px(170)}:fontcolor={WHITE}"
                          f":x={ctx.px(x)}:y={ctx.px(380)}:alpha='min(1\\,max(0\\,(t-{t0:.3f})/0.3))'")
        else:
            layers.append(text(ctx, str(val), 170, WHITE, x, 380, t0=t0, rise=30))
        color = ctx.accent if hl == i else MUTED
        layers.append(text(ctx, label, 34, color, x, 590, font=ctx.regular, t0=t0 + 0.15, rise=14))
    if spec.get("note"):
        layers.append(text(ctx, spec["note"], 34, WHITE, 80, 800, font=ctx.regular, t0=1.6, rise=16))
    render_scene(ctx, out, dur, bg_inputs(ctx, dur), "[0:v]null[base]", layers, bars)
    return dur


def scene_end(ctx, spec, out):
    dur = spec.get("beats", 8) * ctx.beat
    bars, layers = Bars(), []
    layers.append(text(ctx, spec["text"], 170, WHITE, 80, 300, t0=0.05, rise=50, dur=0.45))
    bars.add(ctx.px(80), ctx.px(510), ctx.px(400), ctx.px(6), ctx.accent, 0.3, 0.5)
    if spec.get("sub"):
        layers.append(text(ctx, spec["sub"], 52, ctx.accent2, 80, 560, t0=0.5, rise=20))
    if spec.get("question"):
        layers.append(text(ctx, spec["question"], 40, MUTED, 80, 760, font=ctx.regular, t0=1.2, rise=20))
    render_scene(ctx, out, dur, bg_inputs(ctx, dur), "[0:v]null[base]", layers, bars)
    return dur


# ---------- footage scenes ----------
def fit_region(z, sw, sh_, ow, oh):
    """Expand the crop region to the card aspect, keeping its centre, inside the source."""
    cx, cy = z["x"] + z["w"] / 2, z["y"] + z["h"] / 2
    target = ow / oh
    w, h = z["w"], z["h"]
    if w / h < target:
        w = h * target
    else:
        h = w / target
    w, h = min(w, sw), min(h, sh_)
    if w / h > target + 1e-6:        # clamped by height: shrink width to keep aspect
        w = h * target
    elif w / h < target - 1e-6:
        h = w / target
    x = min(max(0, cx - w / 2), sw - w)
    y = min(max(0, cy - h / 2), sh_ - h)
    return int(x) // 2 * 2, int(y) // 2 * 2, int(w) // 2 * 2, int(h) // 2 * 2


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


def scene_footage(ctx, spec, out, index):
    dur = spec.get("beats", 10) * ctx.beat
    src = spec["src"]
    sw, sh_ = (int(v) for v in probe(src, "stream=width,height").split(",")[:2])
    start, end = float(spec["start"]), float(spec["end"])
    window = end - start
    speed = window / dur
    if speed < 1:                      # window shorter than the scene: play at 1x and hold the last frame
        speed = 1.0
    layout = spec.get("layout", "side")
    if layout == "wide":
        CX, CY, CW, CH = 120, 70, 1680, 720
    else:
        CX, CY, CW, CH = 680, 150, 1180, 780
    cx, cy, cw, ch = ctx.px(CX), ctx.px(CY), ctx.px(CW) // 2 * 2, ctx.px(CH) // 2 * 2
    mask, shadow = ctx.card_assets(cw, ch)

    boxes = spec.get("blur") or []
    if isinstance(boxes, str):
        with open(boxes) as fh:
            boxes = json.load(fh)
    boxes = [b for b in boxes if b["t1"] > start and b["t0"] < end]
    local = [{**b, "t0": max(0.0, b["t0"] - start), "t1": min(window, b["t1"] - start)} for b in boxes]
    # Screen recordings are variable frame rate: a still screen produces no frames for seconds
    # at a time. Seeking straight to `start` would drop the frame that covers it and leave the
    # card empty until the next change. So decode from a pre-roll, fill the gaps at a constant
    # rate, then trim to the window exactly.
    seek = max(0.0, start - PREROLL)
    parts = [f"[1:v]setpts=PTS-STARTPTS,fps={ctx.fps},trim=start={start-seek:.3f}:end={end-seek:.3f},"
             f"setpts=PTS-STARTPTS[pre]"]
    bparts, cur = blur_chain(local, "pre", "k")
    parts += bparts

    crop = spec.get("crop") or {"x": 0, "y": 0, "w": sw, "h": sh_}
    zx, zy, zw, zh = fit_region(crop, sw, sh_, cw, ch)
    slide = f"{ctx.px(260)}*pow(max(0\\,1-t/0.55)\\,2)"
    rise = f"{ctx.px(90)}*pow(max(0\\,1-t/0.55)\\,2)"
    parts.append(
        f"[{cur}]setpts=PTS/{speed:.5f},fps={ctx.fps},tpad=stop_mode=clone:stop_duration=2,"
        f"crop={zw}:{zh}:{zx}:{zy},scale={cw}:{ch}:flags=lanczos,"
        f"scale=w='{cw}*(1+0.05*t/{dur:.3f})':h=-1:eval=frame,crop={cw}:{ch},format=rgba[foot]")
    parts.append(f"[foot][3:v]alphamerge,fade=t=in:st=0:d=0.3:alpha=1[fa]")
    parts.append(f"[2:v]format=rgba,fade=t=in:st=0:d=0.4:alpha=1[shd]")
    pad = ctx.px(60)
    if layout == "wide":
        parts.append(f"[0:v]format=rgba[bg];[bg][shd]overlay=x={cx-pad}:y='{cy-pad}+{rise}':eval=frame[b1]")
        parts.append(f"[b1][fa]overlay=x={cx}:y='{cy}+{rise}':eval=frame[base]")
    else:
        parts.append(f"[0:v]format=rgba[bg];[bg][shd]overlay=x='{cx-pad}+{slide}':y={cy-pad}:eval=frame[b1]")
        parts.append(f"[b1][fa]overlay=x='{cx}+{slide}':y={cy}:eval=frame[base]")

    chapter = spec.get("chapter", "")
    num = f"{index:02d}"
    label = " ".join(chapter.upper())
    caption = spec.get("caption") or []
    if isinstance(caption, str):
        caption = [caption]
    bars, layers = Bars(), []
    if layout == "wide":
        layers.append(text(ctx, f"{num}  ·  {label}", 26, ctx.accent2, 120, 836, t0=0.2, rise=12))
        for i, l in enumerate(caption[:2]):
            layers.append(text(ctx, l, 50, WHITE if i == 0 else ctx.accent, 120, 872 + i * 60,
                               t0=0.35 + i * 0.15, rise=24))
    else:
        layers.append(text(ctx, num, 110, ctx.accent, 80, 140, t0=0.05, rise=30))
        layers.append(text(ctx, label, 26, ctx.accent2, 80, 262, t0=0.15, rise=12))
        bars.add(ctx.px(80), ctx.px(306), ctx.px(140), ctx.px(4), ctx.accent, 0.2)
        longest = max((len(l) for l in caption), default=0)
        size = 58 if longest <= 17 else (52 if longest <= 19 else (46 if longest <= 22 else 40))
        if len(caption) > 4:
            size = min(size, 50)
        for i, l in enumerate(caption[:5]):
            layers.append(text(ctx, l, size, WHITE, 80, 345 + i * (size + 12), t0=0.3 + i * 0.09, rise=28))
    if speed > 1.5:
        bw, bx, by = ctx.px(110), cx + cw - ctx.px(130), cy + ctx.px(18)
        show = "" if layout == "wide" else ":enable='gte(t\\,0.6)'"
        layers.append(f"drawbox=x={bx}:y={by}:w={bw}:h={ctx.px(38)}:color=black@0.7:t=fill{show}")
        layers.append(f"drawtext=fontfile='{ctx.mono}':text='{speed:.0f}x':fontsize={ctx.px(24)}:fontcolor=white"
                      f":x={bx}+({bw}-tw)/2:y={by+ctx.px(7)}{show}")

    inputs = bg_inputs(ctx, dur) + ["-ss", f"{seek:.3f}", "-t", f"{end-seek+0.5:.3f}", "-i", src,
                                    "-loop", "1", "-framerate", str(ctx.fps), "-t", f"{dur+0.5:.3f}", "-i", shadow,
                                    "-loop", "1", "-framerate", str(ctx.fps), "-t", f"{dur+0.5:.3f}", "-i", mask]
    render_scene(ctx, out, dur, inputs, ";".join(parts), layers, bars)
    return dur, speed, len(boxes)


# ---------- assembly ----------
def assemble(ctx, plan, clips, out):
    total = sum(d for _, d in clips)
    lst = os.path.join(ctx.tmp, "list.txt")
    with open(lst, "w") as fh:
        fh.write("".join(f"file '{p}'\n" for p, _ in clips))
    brand = plan.get("brand") or {}
    t_in = sum(d for _, d in clips[:plan["_chapter_from"]])
    t_out = total - clips[-1][1] if plan.get("end") else total
    parts = [f"[2:v]scale=w='max(2\\,{ctx.W}*t/{total:.3f})':h={ctx.px(12)}:eval=frame[pb]",
             f"[0:v][pb]overlay=x=0:y={ctx.H-ctx.px(12)}:eval=frame:shortest=1[p1]"]
    cur = "p1"
    en = f":enable='between(t\\,{t_in:.3f}\\,{t_out:.3f})'"
    if brand.get("name"):
        parts.append(f"[{cur}]drawtext=fontfile='{ctx.bold}':textfile='{ctx.textfile(brand['name'])}':fontsize={ctx.px(22)}"
                     f":fontcolor={MUTED}:x={ctx.px(80)}:y={ctx.px(1022)}{en}[p2]")
        cur = "p2"
    if brand.get("day"):
        parts.append(f"[{cur}]drawtext=fontfile='{ctx.bold}':textfile='{ctx.textfile(brand['day'])}':fontsize={ctx.px(22)}"
                     f":fontcolor={MUTED}:x=w-tw-{ctx.px(80)}:y={ctx.px(1022)}{en}[p3]")
        cur = "p3"
    parts.append(f"[{cur}]format=yuv420p[v]")

    inputs = ["-f", "concat", "-safe", "0", "-i", lst]
    music = plan.get("music") or {}
    mfile = music.get("file")
    if mfile and os.path.exists(mfile):
        inputs += ["-stream_loop", "-1", "-i", mfile]
        vol = float(music.get("volume_db", 0))
        parts.append(f"[1:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,volume={vol}dB,"
                     f"afade=t=in:d=0.05,afade=t=out:st={max(0, total-1.5):.3f}:d=1.5[a]")
        amap = ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    else:
        inputs += ["-f", "lavfi", "-t", "1", "-i", "anullsrc"]       # keeps input indices stable
        amap = ["-an"]
        print(f"  music: {'file not found, ' if mfile else ''}rendering silent"
              + (f" ({mfile})" if mfile else ""))
    inputs += ["-f", "lavfi", "-t", f"{total+0.5:.3f}", "-i", f"color=c={ctx.accent}:s={ctx.W}x{ctx.px(12)}:r={ctx.fps}"]
    sh(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", ";".join(parts), "-map", "[v]"] + amap
       + ["-t", f"{total:.3f}", "-r", str(ctx.fps), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
          "-pix_fmt", "yuv420p", "-movflags", "+faststart", out])
    return total


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


def upgrade_v1(plan):
    """Accept the old flat plan (title/segments/end with seconds) so earlier plans still render."""
    if "scenes" in plan or "segments" not in plan:
        return plan
    beat = 60.0 / float(plan.get("bpm", 125))
    scenes = []
    for seg in plan["segments"]:
        dur = (float(seg["end"]) - float(seg["start"])) / float(seg.get("speed", 1))
        words = (seg.get("caption") or "").split()
        lines, cur = [], ""
        for w in words:
            if len(cur) + len(w) + 1 > 18 and cur:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur:
            lines.append(cur)
        scenes.append({"type": "footage", "layout": "side", "chapter": "", "src": seg["src"],
                       "start": seg["start"], "end": seg["end"], "crop": seg.get("zoom"),
                       "caption": lines[:4], "beats": max(6, int(round(dur / beat))), "blur": seg.get("blur")})
    out = dict(plan)
    out["scenes"] = scenes
    if plan.get("title"):
        out["title"] = {"text": plan["title"]["text"], "sub": plan["title"].get("sub", ""), "beats": 6}
    if plan.get("end"):
        out["end"] = {"text": plan["end"]["text"], "sub": plan["end"].get("sub", ""), "beats": 8}
    print("render.py: old plan format detected; rendering it in the new style without hook or stats")
    return out


def main():
    if len(sys.argv) == 5 and sys.argv[1] == "--patch":
        patch(sys.argv[2], sys.argv[3], sys.argv[4])
        return
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    with open(sys.argv[1]) as fh:
        plan = upgrade_v1(json.load(fh))
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"render.py: {tool} not found on PATH")
    out = plan["output"]
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    tmp = tempfile.mkdtemp(prefix="pp-render-")
    try:
        ctx = Ctx(plan, tmp)
        brand = plan.get("brand") or {}
        clips = []
        if plan.get("hook"):
            p = os.path.join(tmp, "s00-hook.mp4")
            clips.append((p, scene_hook(ctx, plan["hook"], p)))
            print(f"  hook    {clips[-1][1]:.2f}s")
        if plan.get("title"):
            p = os.path.join(tmp, "s01-title.mp4")
            clips.append((p, scene_title(ctx, plan["title"], p, brand)))
            print(f"  title   {clips[-1][1]:.2f}s")
        plan["_chapter_from"] = len(clips)
        chapter = 0
        for i, sc in enumerate(plan["scenes"]):
            p = os.path.join(tmp, f"s{i+2:02d}-{sc.get('type','footage')}.mp4")
            if sc.get("type", "footage") == "footage":
                chapter += 1
                d, speed, nb = scene_footage(ctx, sc, p, chapter)
                print(f"  {chapter:02d} {sc.get('chapter',''):<10} {d:.2f}s  {speed:.1f}x  blur boxes {nb}  "
                      f"{' / '.join(sc.get('caption') or [])}")
            elif sc["type"] == "stats":
                d = scene_stats(ctx, sc, p)
                print(f"  stats   {d:.2f}s  {sc.get('items')}")
            else:
                sys.exit(f"render.py: unknown scene type {sc['type']!r}")
            clips.append((p, d))
        if plan.get("end"):
            p = os.path.join(tmp, "s99-end.mp4")
            clips.append((p, scene_end(ctx, plan["end"], p)))
            print(f"  end     {clips[-1][1]:.2f}s")
        total = assemble(ctx, plan, clips, out)
        print(f"render.py: {out}  {total:.1f}s  {ctx.W}x{ctx.H}@{ctx.fps}  {len(clips)} scenes  {ctx.bpm:g} bpm")
        if not 30 <= total <= 45:
            print(f"  note: {total:.1f}s is outside the 30-45s target; adjust beats in the plan")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
