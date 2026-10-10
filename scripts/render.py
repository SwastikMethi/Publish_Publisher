#!/usr/bin/env python3
"""Render a finished demo video from an edit plan. Deterministic ffmpeg, nothing else.

  render.py plan.json
  render.py --patch rendered.mp4 leftover.json final.mp4

The finished video is a designed piece, not a screen dump. The plan says what is in it (a
hook, a title, chapters of footage with captions, a stats card, an end question); the theme's
format says how it is staged, in what order, with which transitions, and for how long:

  cards     (midnight, volt) hook card, title on the drop, numbered chapters with the footage
            in a card beside a big caption, stats, end card; hard cuts; scene beats from the plan
  magazine  (paper) a cover, one page per chapter with the footage as a photo on alternating
            sides, an "at a glance" box, a pull-quote; pages push in from the right
  console   (console) a terminal session: typed boot lines, a banner, a step checklist beside a
            window of footage, a typed readout, a [y/n] prompt; pixelated cuts
  keynote   (keynote) a statement, the reveal, then per chapter one big word and the footage on
            a laptop with a slow push-in, the numbers in a grid, the question; crossfades

Every cut lands on a beat of the music, and a progress bar runs along the bottom.

Plan (JSON):
{
  "output": "output/media/demo.mp4",
  "size": [1920, 1080], "fps": 30,
  "bpm": 125,                            # the beat grid; scene lengths are given in beats
  "brand": {"name": "AI Job Orient", "day": "Day 2/30"},      # small footer while chapters play
  "theme": "volt",                       # volt | paper | console | keynote; midnight is the default
                                         # or {"name": "volt", "accent": "0x..."} to override keys
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
speed change and the crop, so they stay on the text. In the cards format, "layout": "side"
puts a 1180x780 card on the right with up to four caption lines on the left; "wide" puts a
1680x720 card on top with one or two caption lines under it. Other formats ignore "layout" and
every "beats" key: their scene lengths are part of the format (see FORMAT_BEATS).
"""
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap

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

SUPP = "/System/Library/Fonts/Supplemental/"

MENLO = "/System/Library/Fonts/Menlo.ttc"

# A theme is the whole look and the format that stages it. Every value is read through ctx.th,
# so a plan's theme dict can override any single key.
#   format  how the plan's content is staged: cards | magazine | console | keynote
#   cut     (xfade transition, seconds) between scenes, or None for hard cuts
#   bg      vertical gradient top->bottom, soft glows (rgb, x, y, strength), optional grid,
#           scanlines (scan), noise
#   shadow  (colour, blur sigma, dx, dy, opacity); sigma 0 is a hard offset shadow
#   motion  how text enters: rise | slide | snap
#   align   hook, title and end cards of the cards format: left | center
#   size    headline scale against Arial Bold; upper puts headline text in capitals
#   flash   a full-frame flash on every cut, or None
#   beat_text  caption lines land half a beat apart instead of a fixed stagger
THEMES = {
    # The original look. Plans without a theme render as this; it is out of the rotation.
    "midnight": dict(
        format="cards", cut=None,
        bg={"top": (12, 16, 34), "bottom": (7, 9, 20), "noise": 5,
            "glows": [((245, 158, 11), 0.78, 0.14, 0.22), ((45, 212, 191), 0.10, 0.93, 0.16)]},
        ink="white", muted="0x9AA3B8", accent="0xF59E0B", accent2="0x2DD4BF",
        fonts=BOLD_CANDIDATES, fonts_regular=REGULAR_CANDIDATES,
        radius=22, shadow=("black", 26, 0, 18, 0.72), motion="rise", align="left",
        upper=False, size=1.0, flash=None, beat_text=False),
    "volt": dict(
        format="cards", cut=None,
        bg={"top": (8, 8, 8), "bottom": (0, 0, 0), "noise": 7,
            "glows": [((198, 255, 0), 0.88, 0.08, 0.07)]},
        ink="white", muted="0x8C8C8C", accent="0xC6FF00", accent2="0xE9FF9A",
        fonts=[SUPP + "Impact.ttf"] + BOLD_CANDIDATES, fonts_regular=REGULAR_CANDIDATES,
        radius=4, shadow=("0xC6FF00", 0, 14, 14, 1.0), motion="snap", align="center",
        upper=True, size=1.12, flash="white@0.55", beat_text=True),
    "paper": dict(
        format="magazine", cut=("slideleft", 0.45),
        bg={"top": (246, 241, 230), "bottom": (234, 227, 211), "noise": 9},
        ink="0x141414", muted="0x6B6358", accent="0xE63A1E", accent2="0x2448D8",
        fonts=[SUPP + "Arial Black.ttf"] + BOLD_CANDIDATES,
        fonts_regular=[SUPP + "Georgia.ttf"] + REGULAR_CANDIDATES,
        italic=SUPP + "Georgia Italic.ttf",
        radius=0, shadow=("0x141414", 0, 14, 14, 1.0), motion="slide", align="left",
        upper=False, size=0.95, flash=None, beat_text=True),
    "console": dict(
        format="console", cut=("pixelize", 0.3),
        bg={"top": (8, 20, 12), "bottom": (2, 7, 4), "noise": 6, "scan": True,
            "glows": [((57, 255, 20), 0.5, 0.45, 0.05)]},
        ink="0x39FF14", muted="0x1F8A35", accent="0x39FF14", accent2="0xFFB000",
        fonts=[MENLO] + BOLD_CANDIDATES, fonts_regular=[MENLO] + REGULAR_CANDIDATES,
        radius=0, shadow=("black", 0, 0, 0, 0.0), motion="rise", align="left",
        upper=False, size=1.0, flash=None, beat_text=True),
    "keynote": dict(
        format="keynote", cut=("fade", 0.5),
        bg={"top": (246, 248, 252), "bottom": (225, 230, 240), "noise": 2,
            "glows": [((255, 255, 255), 0.5, 0.3, 0.2)]},
        ink="0x0F1729", muted="0x5B6B8C", accent="0x4F6BFF", accent2="0x8A5CFF",
        fonts=["/System/Library/Fonts/Avenir Next.ttc"] + BOLD_CANDIDATES,
        fonts_regular=["/System/Library/Fonts/Avenir.ttc"] + REGULAR_CANDIDATES,
        radius=6, shadow=("0x0F1729", 34, 0, 30, 0.35), motion="rise", align="center",
        upper=False, size=1.0, flash=None, beat_text=True),
}

# Scene lengths, in beats, for the formats that own their timing. The cards format reads them
# from the plan instead, so old plans keep their cut.
FORMAT_BEATS = {
    "magazine": dict(intro=4, title=6, chapter=12, stats=8, end=8),
    "console": dict(intro=6, title=6, chapter=14, stats=8, end=8),
    "keynote": dict(intro=6, title=6, word=2, chapter=10, stats=8, end=8),
}


def theme_of(plan):
    """(name, theme) for a plan: a theme name, or a dict with an optional "name" and overrides."""
    theme = plan.get("theme") or {}
    if isinstance(theme, str):
        theme = {"name": theme}
    name = theme.get("name", "midnight")
    if name not in THEMES:
        sys.exit(f"render.py: unknown theme {name!r}; use one of {', '.join(THEMES)}")
    return name, {**THEMES[name], **theme}

INK = "0x0B1020"
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
        self.th = th = theme_of(plan)[1]
        self.bold = pick("font", th["fonts"], plan)
        self.regular = pick("font_regular", th["fonts_regular"], plan)
        self.italic = th.get("italic") if os.path.exists(th.get("italic") or "") else self.regular
        self.mono = pick("font_mono", MONO_CANDIDATES, plan)
        # With a transition every clip runs on past its beat by the transition's length, and the
        # next clip starts over that tail, so cuts still begin on the beat.
        self.tail = th["cut"][1] if th["cut"] else 0.0
        self.accent, self.accent2 = th["accent"], th["accent2"]
        self.ink, self.muted = th["ink"], th["muted"]
        self.tmp = tmp
        self.n = 0
        self.bg = self.make_bg()
        self.cards = {}

    def px(self, v):
        return int(round(v * self.k))

    def tx(self, x):
        """Text x: as given, or centred when the theme centres its cards."""
        return "(w-text_w)/2" if self.th["align"] == "center" else x

    def bx(self, x, w):
        """Accent bar x in output pixels, centred like the text when the theme centres."""
        return (self.W - w) // 2 if self.th["align"] == "center" else x

    def at(self, base, step, i):
        """Start of the i-th line: a fixed stagger, or on the half-beat grid."""
        return (i + 1) * self.beat / 2 if self.th["beat_text"] else base + i * step

    def textfile(self, text):
        self.n += 1
        p = os.path.join(self.tmp, f"t{self.n}.txt")
        with open(p, "w") as fh:
            fh.write(text)
        return p

    # ---- static assets, built once with ffmpeg ----
    def make_bg(self):
        """The theme's vertical gradient with soft colour glows, an optional grid, fine noise."""
        W, H = self.W, self.H
        bg = self.th["bg"]
        p = os.path.join(self.tmp, "bg.png")

        def chan(c):
            top, drop = bg["top"][c], bg["top"][c] - bg["bottom"][c]
            e = f"{top}-{drop}*Y/{H}" if drop >= 0 else f"{top}+{-drop}*Y/{H}"
            for col, gx, gy, s in bg.get("glows", []):
                e += f" + {col[c]}*{s}*exp(-((X-{W*gx})^2+(Y-{H*gy})^2)/({W*0.47})^2)"
            return f"clip({e},0,255)"

        grid = (f",drawgrid=w={self.px(96)}:h={self.px(96)}:t={max(1, self.px(2))}:c={bg['grid']}"
                if bg.get("grid") else "")
        if bg.get("scan"):           # CRT scanlines and a darkened edge
            grid += f",drawgrid=w=iw:h={max(2, self.px(4))}:t=1:c=black@0.35,vignette=PI/4"
        sh(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r=1:d=1",
            "-vf", f"format=rgb24,geq=r='{chan(0)}':g='{chan(1)}':b='{chan(2)}'{grid},"
                   f"noise=alls={bg.get('noise', 5)}:allf=u", "-frames:v", "1", p])
        return p

    def card_assets(self, cw, ch, radius=None):
        """Rounded mask and the theme's shadow for a footage card of cw x ch."""
        radius = self.th["radius"] if radius is None else radius
        if (cw, ch, radius) in self.cards:
            return self.cards[(cw, ch, radius)]
        r = self.px(radius)
        color, sigma, dx, dy, opacity = self.th["shadow"]
        mask = os.path.join(self.tmp, f"mask{cw}x{ch}r{radius}.png")
        rr = (f"if(gt(hypot(max(0\\,abs(X-W/2)-(W/2-{r}))\\,max(0\\,abs(Y-H/2)-(H/2-{r})))\\,{r})\\,0\\,255)")
        sh(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=white:s={cw}x{ch}:r=1:d=1",
            "-vf", f"format=gray,geq=lum='{rr}'", "-frames:v", "1", mask])
        pad = self.px(60)
        shadow = os.path.join(self.tmp, f"shadow{cw}x{ch}r{radius}.png")
        sw, shh = cw + 2 * pad, ch + 2 * pad
        blur = f"gblur=sigma={self.px(sigma)}," if sigma else ""
        sh(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", "1", "-i", mask,
            "-f", "lavfi", "-t", "1", "-i", f"color=c={color}:s={sw}x{shh}:r=1",
            "-filter_complex", f"[0:v]format=gray,pad={sw}:{shh}:{pad+self.px(dx)}:{pad+self.px(dy)}:black,"
                               f"{blur}lutyuv=y='val*{opacity}'[a];[1:v][a]alphamerge[out]",
            "-map", "[out]", "-frames:v", "1", shadow])
        self.cards[(cw, ch, radius)] = (mask, shadow)
        return mask, shadow

    def slab(self, w, h, r, color):
        """A solid rounded rectangle with alpha, for drawn props like the keynote laptop."""
        p = os.path.join(self.tmp, f"slab{w}x{h}r{r}{color}.png")
        rr = (f"if(gt(hypot(max(0\\,abs(X-W/2)-(W/2-{r}))\\,max(0\\,abs(Y-H/2)-(H/2-{r})))\\,{r})\\,0\\,255)")
        sh(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s={w}x{h}:r=1:d=1",
            "-f", "lavfi", "-i", f"color=c=white:s={w}x{h}:r=1:d=1",
            "-filter_complex", f"[1:v]format=gray,geq=lum='{rr}'[a];[0:v][a]alphamerge[out]",
            "-map", "[out]", "-frames:v", "1", p])
        return p


# ---------- text and bars (all animate in, in the theme's motion) ----------
def text(ctx, s, size, color, x, y, font=None, t0=0.0, rise=26, dur=0.35, extra="", motion=None):
    font = font or ctx.bold
    if ctx.th["upper"] and font == ctx.bold:
        s = s.upper()
    xx = x if isinstance(x, str) else str(ctx.px(x))
    yy, T, on = str(ctx.px(y)), f"(t-{t0:.3f})", f"gte(t\\,{t0:.3f})"
    motion = motion or ctx.th["motion"]
    if motion == "still":              # page furniture: there from the first frame
        a = "1"
    elif motion == "slide":            # hard cut in from the left, no fade
        a = on
        xx = f"{xx}-{ctx.px(140)}*pow(max(0\\,1-{T}/0.3)\\,3)"
    elif motion == "snap":             # appears on its beat and settles with a small bounce
        a = on
        yy = f"{yy}-{ctx.px(rise)}*exp(-max(0\\,{T})*10)*cos(max(0\\,{T})*30)"
    else:                              # rise: fade in while rising into place
        a = f"min(1\\,max(0\\,(t-{t0:.3f})/{dur}))"
        yy = f"{ctx.px(y)}+{ctx.px(rise)}*pow(max(0\\,1-(t-{t0:.3f})/{dur})\\,2)"
    return (f"drawtext=fontfile='{font}':textfile='{ctx.textfile(s)}':fontsize={ctx.px(size)}"
            f":fontcolor={color}:x='{xx}':y='{yy}':alpha='{a}'{extra}")


def countup(ctx, val, size, color, x, t0, y):
    """A whole number counting up from 0 at seven steps a second; x is in output pixels or an
    expression."""
    e = f"%{{eif\\:min({int(val)}\\,floor(max(0\\,(t-{t0:.3f}))*7))\\:d}}"
    return (f"drawtext=fontfile='{ctx.bold}':text='{e}':fontsize={ctx.px(size)}:fontcolor={color}"
            f":x={x}:y={ctx.px(y)}:alpha='min(1\\,max(0\\,(t-{t0:.3f})/0.3))'")


def whole(val):
    return isinstance(val, (int, float)) and float(val).is_integer()


def typed(ctx, s, size, color, x, y, t0, cps=30, font=None):
    """A line that types itself out at cps characters a second: one drawtext per prefix, each
    shown until the next takes over. Returns (filters, time the last character lands)."""
    font = font or ctx.bold
    out, n = [], len(s)
    for i in range(1, n + 1):
        a, b = t0 + (i - 1) / cps, (t0 + i / cps if i < n else 1e6)
        out.append(f"drawtext=fontfile='{font}':textfile='{ctx.textfile(s[:i])}':fontsize={ctx.px(size)}"
                   f":fontcolor={color}:x={ctx.px(x)}:y={ctx.px(y)}:enable='between(t\\,{a:.3f}\\,{b:.3f})'")
    return out, t0 + n / cps


def cursor(ctx, size, color, x, y, t0):
    """A blinking block cursor from t0 on."""
    return (f"drawtext=fontfile='{ctx.bold}':textfile='{ctx.textfile(chr(0x2588))}':fontsize={ctx.px(size)}"
            f":fontcolor={color}:x={ctx.px(x)}:y={ctx.px(y)}:enable='gte(t\\,{t0:.3f})*lt(mod(t\\,0.6)\\,0.32)'")


def box(ctx, x, y, w, h, color, t="fill"):
    """A drawbox filter in design pixels; t is a line thickness in design pixels, or fill."""
    tt = t if t == "fill" else max(1, ctx.px(t))
    return f"drawbox=x={ctx.px(x)}:y={ctx.px(y)}:w={ctx.px(w)}:h={ctx.px(h)}:color={color}:t={tt}"


class Bars:
    """Accent bars that grow in. Each becomes a colour input, scaled per frame, overlaid."""

    def __init__(self):
        self.items = []

    def add(self, x, y, w, h, color, t0=0.0, dur=0.45):
        self.items.append((x, y, w, h, color, t0, dur))


def render_scene(ctx, out, dur, inputs, graph, layers, bars):
    """graph must end in [base]; layers are drawtext filters applied to it; bars overlaid last."""
    if ctx.th["flash"]:
        layers = list(layers) + [f"drawbox=x=0:y=0:w=iw:h=ih:color={ctx.th['flash']}:t=fill"
                                 f":enable='lt(t\\,0.07)'"]
    fc = graph + ";[base]" + ",".join(["null"] + [l for l in layers if l]) + "[v0]"
    inputs = list(inputs)
    cur = "v0"
    for i, (x, y, w, h, color, t0, d) in enumerate(bars.items):
        idx = inputs.count("-i")
        inputs += ["-f", "lavfi", "-t", f"{dur+ctx.tail+0.5:.3f}", "-i", f"color=c={color}:s={w}x{h}:r={ctx.fps}"]
        fc += (f";[{idx}:v]scale=w='max(2\\,{w}*min(1\\,max(0\\,(t-{t0:.3f})/{d})))':h={h}:eval=frame[bar{i}];"
               f"[{cur}][bar{i}]overlay=x={x}:y={y}:eval=frame:shortest=1[v{i+1}]")
        cur = f"v{i+1}"
    fc += f";[{cur}]format=yuv420p[v]"
    sh(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", fc, "-map", "[v]",
        "-t", f"{dur+ctx.tail:.3f}", "-r", str(ctx.fps), "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "17", "-pix_fmt", "yuv420p", out])


def still(ctx, path, dur):
    """Input args that loop a still image for the length of a scene."""
    return ["-loop", "1", "-framerate", str(ctx.fps), "-t", f"{dur+ctx.tail+0.5:.3f}", "-i", path]


def bg_inputs(ctx, dur):
    return still(ctx, ctx.bg, dur)


# ---------- cards format (midnight, volt): every scene is (ctx, spec, out, dur, k) ----------
# k carries the scene's context: brand, chapter index, the chapter names, and the whole plan.
def scene_hook(ctx, spec, out, dur, k):
    lines = spec.get("lines") or [spec.get("text", "")]
    bars, layers = Bars(), []
    bars.add(ctx.bx(ctx.px(80), ctx.px(120)), ctx.px(300), ctx.px(120), ctx.px(6), ctx.accent, 0.05)
    size = (96 if max(len(l) for l in lines) <= 22 else 80) * ctx.th["size"]
    for i, l in enumerate(lines[:3]):
        layers.append(text(ctx, l, size, ctx.ink, ctx.tx(80), 340 + i * (size + 14),
                           t0=ctx.at(0.15, 0.2, i), rise=40))
    if spec.get("sub"):
        layers.append(text(ctx, spec["sub"], 40, ctx.muted, ctx.tx(80), 340 + len(lines[:3]) * (size + 14) + 50,
                           font=ctx.regular, t0=0.35 + len(lines[:3]) * 0.2 + 0.4, rise=20))
    render_scene(ctx, out, dur, bg_inputs(ctx, dur), "[0:v]null[base]", layers, bars)


def scene_title(ctx, spec, out, dur, k):
    brand = k["brand"]
    sub = spec.get("sub") or []
    if isinstance(sub, str):
        sub = [sub]
    size = (150 if len(spec["text"]) <= 16 else (120 if len(spec["text"]) <= 22 else 96)) * ctx.th["size"]
    bars, layers = Bars(), []
    layers.append(text(ctx, spec["text"], size, ctx.ink, ctx.tx(80), 330, t0=0.05, rise=50, dur=0.45))
    bars.add(ctx.bx(ctx.px(80), ctx.px(1760)), ctx.px(520), ctx.px(1760), ctx.px(5), ctx.accent, 0.25, 0.7)
    for i, s in enumerate(sub[:2]):
        layers.append(text(ctx, s, 42, ctx.muted, ctx.tx(80), 560 + i * 56, font=ctx.regular,
                           t0=0.55 + i * 0.15, rise=20))
    foot = "  ·  ".join(x for x in (brand.get("day"), brand.get("tag", "#buildinpublic")) if x)
    if foot:
        layers.append(text(ctx, foot, 28, ctx.accent2, ctx.tx(80), 960, t0=1.0, rise=10))
    render_scene(ctx, out, dur, bg_inputs(ctx, dur), "[0:v]null[base]", layers, bars)


def scene_stats(ctx, spec, out, dur, k):
    items = spec["items"][:4]
    hl = spec.get("highlight")
    bars, layers = Bars(), []
    layers.append(text(ctx, spec.get("label", "This run"), 30, ctx.accent2, 80, 200, t0=0.1, rise=12))
    bars.add(ctx.px(80), ctx.px(246), ctx.px(140), ctx.px(4), ctx.accent, 0.15)
    colw = 1760 // max(1, len(items))
    for i, (val, label) in enumerate(items):
        x, t0 = 80 + i * colw, ctx.at(0.3, 0.15, i)
        if whole(val):
            layers.append(countup(ctx, val, 170, ctx.ink, ctx.px(x), t0, 380))
        else:
            layers.append(text(ctx, str(val), 170, ctx.ink, x, 380, t0=t0, rise=30))
        color = ctx.accent if hl == i else ctx.muted
        layers.append(text(ctx, label, 34, color, x, 590, font=ctx.regular, t0=t0 + 0.15, rise=14))
    if spec.get("note"):
        layers.append(text(ctx, spec["note"], 34, ctx.ink, 80, 800, font=ctx.regular, t0=1.6, rise=16))
    render_scene(ctx, out, dur, bg_inputs(ctx, dur), "[0:v]null[base]", layers, bars)


def scene_end(ctx, spec, out, dur, k):
    bars, layers = Bars(), []
    layers.append(text(ctx, spec["text"], 170 * ctx.th["size"], ctx.ink, ctx.tx(80), 300, t0=0.05, rise=50, dur=0.45))
    bars.add(ctx.bx(ctx.px(80), ctx.px(400)), ctx.px(510), ctx.px(400), ctx.px(6), ctx.accent, 0.3, 0.5)
    if spec.get("sub"):
        layers.append(text(ctx, spec["sub"], 52, ctx.accent2, ctx.tx(80), 560, t0=0.5, rise=20))
    if spec.get("question"):
        layers.append(text(ctx, spec["question"], 40, ctx.muted, ctx.tx(80), 760, font=ctx.regular, t0=1.2, rise=20))
    render_scene(ctx, out, dur, bg_inputs(ctx, dur), "[0:v]null[base]", layers, bars)


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


def footage_src(ctx, spec, dur):
    """A footage scene's source window, blurred where redact.py found text and retimed to fill
    dur, as filter parts ending in [src]; the source must be the scene's input 1. Returns
    (input args, parts, (width, height), speed, blur box count)."""
    src = spec["src"]
    sw, sh_ = (int(v) for v in probe(src, "stream=width,height").split(",")[:2])
    start, end = float(spec["start"]), float(spec["end"])
    window = end - start
    speed = max(1.0, window / dur)     # a window shorter than the scene plays at 1x and holds
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
    parts.append(f"[{cur}]setpts=PTS/{speed:.5f},fps={ctx.fps},tpad=stop_mode=clone:stop_duration=2[src]")
    return ["-ss", f"{seek:.3f}", "-t", f"{end-seek+0.5:.3f}", "-i", src], parts, (sw, sh_), speed, len(boxes)


def fitted(spec, size, w, h, zoom):
    """From [src]: the crop region fitted to w x h and zoomed about its centre by `zoom` (an
    expression in t, 1 at rest), as an rgba stream [foot]."""
    crop = spec.get("crop") or {"x": 0, "y": 0, "w": size[0], "h": size[1]}
    zx, zy, zw, zh = fit_region(crop, *size, w, h)
    return (f"[src]crop={zw}:{zh}:{zx}:{zy},scale={w}:{h}:flags=lanczos,"
            f"scale=w='{w}*({zoom})':h=-1:eval=frame,crop={w}:{h},format=rgba[foot]")


def speed_badge(ctx, speed, x, y, show=""):
    """A small "4x" pill at (x, y) in output pixels, for fast-forwarded footage."""
    bw = ctx.px(110)
    return [f"drawbox=x={x}:y={y}:w={bw}:h={ctx.px(38)}:color=black@0.7:t=fill{show}",
            f"drawtext=fontfile='{ctx.mono}':text='{speed:.0f}x':fontsize={ctx.px(24)}:fontcolor=white"
            f":x={x}+({bw}-tw)/2:y={y+ctx.px(7)}{show}"]


def scene_footage(ctx, spec, out, dur, k):
    inputs, parts, size, speed, nb = footage_src(ctx, spec, dur)
    layout = spec.get("layout", "side")
    if layout == "wide":
        CX, CY, CW, CH = 120, 70, 1680, 720
    else:
        CX, CY, CW, CH = 680, 150, 1180, 780
    cx, cy, cw, ch = ctx.px(CX), ctx.px(CY), ctx.px(CW) // 2 * 2, ctx.px(CH) // 2 * 2
    mask, shadow = ctx.card_assets(cw, ch)
    slide = f"{ctx.px(260)}*pow(max(0\\,1-t/0.55)\\,2)"
    rise = f"{ctx.px(90)}*pow(max(0\\,1-t/0.55)\\,2)"
    parts.append(fitted(spec, size, cw, ch, f"1+0.05*t/{dur:.3f}"))
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
    num = f"{k['index']:02d}"
    label = " ".join(chapter.upper())
    caption = spec.get("caption") or []
    if isinstance(caption, str):
        caption = [caption]
    bars, layers = Bars(), []
    if layout == "wide":
        layers.append(text(ctx, f"{num}  ·  {label}", 26, ctx.accent2, 120, 836, t0=0.2, rise=12))
        size = 50 * ctx.th["size"]
        for i, l in enumerate(caption[:2]):
            layers.append(text(ctx, l, size, ctx.ink if i == 0 else ctx.accent, 120, 872 + i * (size + 10),
                               t0=ctx.at(0.35, 0.15, i), rise=24))
    else:
        layers.append(text(ctx, num, 110, ctx.accent, 80, 140, t0=0.05, rise=30))
        layers.append(text(ctx, label, 26, ctx.accent2, 80, 262, t0=0.15, rise=12))
        bars.add(ctx.px(80), ctx.px(306), ctx.px(140), ctx.px(4), ctx.accent, 0.2)
        longest = max((len(l) for l in caption), default=0)
        size = 58 if longest <= 17 else (52 if longest <= 19 else (46 if longest <= 22 else 40))
        if len(caption) > 4:
            size = min(size, 50)
        size *= ctx.th["size"]
        for i, l in enumerate(caption[:5]):
            layers.append(text(ctx, l, size, ctx.ink, 80, 345 + i * (size + 12), t0=ctx.at(0.3, 0.09, i), rise=28))
    if speed > 1.5:
        show = "" if layout == "wide" else ":enable='gte(t\\,0.6)'"
        layers += speed_badge(ctx, speed, cx + cw - ctx.px(130), cy + ctx.px(18), show)

    inputs = bg_inputs(ctx, dur) + inputs + still(ctx, shadow, dur) + still(ctx, mask, dur)
    render_scene(ctx, out, dur, inputs, ";".join(parts), layers, bars)
    return speed, nb


def lines_of(v):
    return [v] if isinstance(v, str) else list(v or [])


def card_scene(ctx, out, dur, layers, bars=None):
    render_scene(ctx, out, dur, bg_inputs(ctx, dur), "[0:v]null[base]", layers, bars or Bars())


# ---------- magazine format (paper): cover, pages, an "at a glance" box, a pull-quote ----------
def running_head(ctx, k, layers):
    """The strip across the top of an inside page: the name, a rule, the day and page number."""
    brand = k["brand"]
    layers.append(text(ctx, (brand.get("name") or "").upper(), 22, ctx.ink, 110, 62, motion="still"))
    right = "  ·  ".join(x for x in (brand.get("day"), f"p. {k['page']}") if x)
    layers.append(text(ctx, right, 26, ctx.muted, f"w-text_w-{ctx.px(110)}", 60, font=ctx.regular, motion="still"))
    layers.append(box(ctx, 110, 104, 1700, 3, ctx.ink))


def scene_cover(ctx, plan, out, dur, k):
    """The cover: a masthead, the hook as the standfirst under the riser, the headline on the drop."""
    hook, title, brand = plan.get("hook") or {}, plan.get("title") or {}, k["brand"]
    drop = FORMAT_BEATS["magazine"]["intro"] * ctx.beat
    bars, layers = Bars(), [text(ctx, "BUILD IN PUBLIC", 24, ctx.accent, 110, 96, motion="still")]
    if brand.get("day"):
        layers.append(text(ctx, brand["day"], 30, ctx.ink, f"w-text_w-{ctx.px(110)}", 92, font=ctx.regular, motion="still"))
    bars.add(ctx.px(110), ctx.px(146), ctx.px(1700), ctx.px(5), ctx.ink, 0.0, 0.5)
    lines = lines_of(hook.get("lines"))[:3]
    for i, l in enumerate(lines):
        layers.append(text(ctx, l, 60, ctx.ink, 110, 200 + i * 76, font=ctx.italic, t0=ctx.at(0.15, 0.2, i)))
    if hook.get("sub"):
        layers.append(text(ctx, hook["sub"], 30, ctx.muted, 110, 214 + len(lines) * 76, font=ctx.regular, t0=0.9))
    if title.get("text"):
        size = (150 if len(title["text"]) <= 16 else 120) * ctx.th["size"]
        layers.append(text(ctx, title["text"], size, ctx.ink, 110, 470, t0=drop))
        bars.add(ctx.px(110), ctx.px(470 + size + 36), ctx.px(260), ctx.px(8), ctx.accent, drop + 0.15)
        for i, s in enumerate(lines_of(title.get("sub"))[:2]):
            layers.append(text(ctx, s, 40, ctx.muted, 110, 700 + i * 54, font=ctx.regular, t0=drop + 0.35 + i * 0.12))
    card_scene(ctx, out, dur, layers, bars)


def scene_page(ctx, spec, out, dur, k):
    """A chapter as a page: the footage as a photo on alternating sides, the chapter word as the
    heading, the caption as body copy, a figure note under the photo."""
    n = k["index"]
    inputs, parts, size, speed, nb = footage_src(ctx, spec, dur)
    PW, PH = 1040, 650
    left = n % 2 == 1
    PX, PY = (110 if left else 1920 - 110 - PW), 200
    TX = 1230 if left else 110
    px_, py_, pw, ph = ctx.px(PX), ctx.px(PY), ctx.px(PW) // 2 * 2, ctx.px(PH) // 2 * 2
    mask, shadow = ctx.card_assets(pw, ph)
    pad = ctx.px(60)
    parts.append(fitted(spec, size, pw, ph, f"1+0.03*t/{dur:.3f}"))
    parts.append("[foot][3:v]alphamerge[fa]")
    parts.append(f"[0:v]format=rgba[bg];[bg][2:v]overlay=x={px_-pad}:y={py_-pad}[b1];[b1][fa]overlay=x={px_}:y={py_}[base]")
    bars, layers = Bars(), []
    running_head(ctx, k, layers)
    layers.append(box(ctx, PX, PY, PW, PH, ctx.ink, t=3))
    chapter = spec.get("chapter", "")
    layers.append(text(ctx, f"FIG. {n}  ·  {chapter.upper()}", 24, ctx.accent, TX, 230, t0=0.1))
    layers.append(text(ctx, f"{chapter}.", 92 * ctx.th["size"], ctx.ink, TX, 276, t0=0.2))
    bars.add(ctx.px(TX), ctx.px(400), ctx.px(120), ctx.px(6), ctx.accent, 0.3)
    for i, l in enumerate(textwrap.wrap(" ".join(lines_of(spec.get("caption"))), 25)[:6]):
        layers.append(text(ctx, l, 44, ctx.ink, TX, 440 + i * 60, font=ctx.regular, t0=ctx.at(0.35, 0.09, i)))
    note = f"Fig. {n}." + (f"  Shown at {speed:.0f}x speed." if speed > 1.5 else "")
    layers.append(text(ctx, note, 26, ctx.muted, PX, PY + PH + 24, font=ctx.italic, motion="still"))
    inputs = bg_inputs(ctx, dur) + inputs + still(ctx, shadow, dur) + still(ctx, mask, dur)
    render_scene(ctx, out, dur, inputs, ";".join(parts), layers, bars)
    return speed, nb


def scene_infobox(ctx, spec, out, dur, k):
    """The stats as an "at a glance" box: label and number per row, the highlighted row in red."""
    items, hl = spec["items"][:4], spec.get("highlight")
    layers = []
    running_head(ctx, k, layers)
    X, Y, W = 520, 170, 880
    H = 170 + 110 * len(items)
    layers.append(box(ctx, X, Y, W, H, ctx.ink, t=4))
    layers.append(text(ctx, "At a glance", 48, ctx.ink, X + 50, Y + 40, t0=0.05))
    if spec.get("label"):
        layers.append(text(ctx, spec["label"], 30, ctx.muted, X + 50, Y + 108, font=ctx.italic, t0=0.15))
    for i, (val, label) in enumerate(items):
        y, t0 = Y + 170 + i * 110, ctx.at(0.3, 0.15, i)
        color = ctx.accent if hl == i else ctx.ink
        layers.append(box(ctx, X + 50, y - 14, W - 100, 2, ctx.muted))
        layers.append(text(ctx, label, 44, color, X + 50, y + 20, font=ctx.regular, t0=t0))
        layers.append(text(ctx, str(val), 64, color, f"{ctx.px(X + W - 50)}-text_w", y + 8, t0=t0))
    if spec.get("note"):
        layers.append(text(ctx, spec["note"], 32, ctx.muted, "(w-text_w)/2", Y + H + 40, font=ctx.italic, t0=1.4))
    card_scene(ctx, out, dur, layers)


def scene_quote(ctx, spec, out, dur, k):
    """The closing question as a pull-quote, signed with the day."""
    q = spec.get("question") or (k["plan"].get("title") or {}).get("text", "")
    layers = []
    running_head(ctx, k, layers)
    layers.append(text(ctx, "“", 360, ctx.accent, 100, 150, font=ctx.regular, t0=0.05))
    rows = textwrap.wrap(q, 26)[:4]
    for i, l in enumerate(rows):
        layers.append(text(ctx, l, 88, ctx.ink, 260, 390 + i * 110, font=ctx.italic, t0=ctx.at(0.25, 0.12, i)))
    sig = "  ·  ".join(x for x in (spec.get("text"), spec.get("sub")) if x)
    if sig:
        layers.append(text(ctx, "— " + sig, 32, ctx.accent, 260, 440 + len(rows) * 110, t0=1.2))
    card_scene(ctx, out, dur, layers)


# ---------- console format: a terminal session ----------
MONO_EM = 0.602    # Menlo's advance width in ems, to place cursors and boxes after mono text


def scene_boot(ctx, spec, out, dur, k):
    """The hook typed at a prompt, the sub-line as a comment, a blinking cursor."""
    lines = (lines_of(spec.get("lines")) or [spec.get("text", "")])[:3]
    layers, t, S = [], 0.25, 72
    rows = [("> " if i == 0 else "  ") + l for i, l in enumerate(lines)]
    for i, r in enumerate(rows):
        f, t = typed(ctx, r, S, ctx.ink, 110, 330 + i * 100, t, cps=34)
        layers += f
    layers.append(cursor(ctx, S, ctx.ink, 110 + (len(rows[-1]) + 1) * MONO_EM * S, 330 + (len(rows) - 1) * 100, t))
    if spec.get("sub"):
        for i, l in enumerate(textwrap.wrap("# " + spec["sub"], 70)[:2]):
            layers.append(text(ctx, l, 32, ctx.muted, 110, 360 + len(rows) * 100 + i * 46, t0=t + 0.1, rise=10))
    card_scene(ctx, out, dur, layers)


def scene_banner(ctx, spec, out, dur, k):
    """The name boxed on the drop; what it does typed underneath as comments."""
    name = spec["text"]
    S = 110 if len(name) <= 20 else 80
    layers = [box(ctx, 80, 290, len(name) * MONO_EM * S + 80, S + 90, ctx.accent, t=4),
              text(ctx, name, S, ctx.ink, 120, 330, motion="still")]
    t = 0.3
    for i, l in enumerate(lines_of(spec.get("sub"))[:2]):
        f, t = typed(ctx, "# " + l, 34, ctx.muted, 110, 330 + S + 110 + i * 50, t, cps=90)
        layers += f
    foot = "  ·  ".join(x for x in (k["brand"].get("day"), "#buildinpublic") if x)
    layers.append(text(ctx, foot.lower(), 28, ctx.accent2, 110, 900, t0=t + 0.1, rise=8))
    card_scene(ctx, out, dur, layers)


def scene_terminal(ctx, spec, out, dur, k):
    """A chapter as a terminal: the run's steps as a checklist, the footage in a window, the
    caption typed underneath as a comment, a status bar along the bottom."""
    n, names = k["index"], [m.lower() for m in k["chapters"]]
    inputs, parts, size, speed, nb = footage_src(ctx, spec, dur)
    WX, WY, WW, WH = 700, 196, 1110, 624
    ww, wh = ctx.px(WW) // 2 * 2, ctx.px(WH) // 2 * 2
    parts.append(fitted(spec, size, ww, wh, f"1+0.03*t/{dur:.3f}"))
    parts.append(f"[0:v]format=rgba[bg];[bg][foot]overlay=x={ctx.px(WX)}:y={ctx.px(WY)}[base]")
    layers = [text(ctx, "$ steps", 30, ctx.muted, 110, 150, motion="still")]
    for j, m in enumerate(names):
        mark, color = ("x", ctx.muted) if j < n - 1 else ((">", ctx.ink) if j == n - 1 else (" ", ctx.muted))
        layers.append(text(ctx, f"[{mark}] {m}", 44, color, 110, 220 + j * 72, motion="still"))
    layers.append(cursor(ctx, 44, ctx.ink, 110 + (len(names[n - 1]) + 5) * MONO_EM * 44, 220 + (n - 1) * 72, 0.2))
    layers.append(box(ctx, WX, WY - 48, WW, 48, f"{ctx.accent}@0.16"))
    layers.append(text(ctx, f"● ● ●   {n:02d} {names[n - 1]}", 26, ctx.ink, WX + 18, WY - 38, motion="still"))
    layers.append(box(ctx, WX - 3, WY - 51, WW + 6, WH + 54, ctx.accent, t=3))
    if speed > 1.5:
        layers.append(text(ctx, f"{speed:.0f}x", 26, ctx.accent2, f"{ctx.px(WX + WW - 18)}-text_w", WY - 38, motion="still"))
    t = 0.4
    for i, l in enumerate(textwrap.wrap("# " + " ".join(lines_of(spec.get("caption"))), 50)[:3]):
        f, t = typed(ctx, l, 36, ctx.ink, WX, WY + WH + 30 + i * 50, t, cps=34)
        layers += f
    layers.append(box(ctx, 0, 1000, 1920, 50, f"{ctx.accent}@0.12"))
    tabs = "  ".join(f"{j + 1}:{m}{'*' if j == n - 1 else ''}" for j, m in enumerate(names))
    layers.append(text(ctx, f"[{(k['brand'].get('name') or 'run').lower()}]  {tabs}", 24, ctx.ink, 30, 1012, motion="still"))
    if k["brand"].get("day"):
        layers.append(text(ctx, k["brand"]["day"].lower(), 24, ctx.ink, f"w-text_w-{ctx.px(30)}", 1012, motion="still"))
    render_scene(ctx, out, dur, bg_inputs(ctx, dur) + inputs, ";".join(parts), layers, Bars())
    return speed, nb


def scene_readout(ctx, spec, out, dur, k):
    """The stats as a command's output, typed a row at a time; the highlighted row in amber."""
    items, hl = spec["items"][:4], spec.get("highlight")
    layers, t = typed(ctx, "$ stats --last-run", 40, ctx.muted, 110, 170, 0.1, cps=60)
    if spec.get("label"):
        layers.append(text(ctx, "# " + spec["label"].lower(), 32, ctx.muted, 110, 236, t0=t, rise=8))
    for i, (val, label) in enumerate(items):
        row = f"{label} ".ljust(26, ".") + f" {val}"
        f, t = typed(ctx, row, 60, ctx.accent2 if hl == i else ctx.ink, 110, 320 + i * 100, t + 0.05, cps=85)
        layers += f
    layers.append(cursor(ctx, 60, ctx.ink, 110, 320 + len(items) * 100, t))
    if spec.get("note"):
        layers.append(text(ctx, "# " + spec["note"], 32, ctx.muted, 110, 410 + len(items) * 100, t0=t + 0.1, rise=8))
    card_scene(ctx, out, dur, layers)


def scene_prompt(ctx, spec, out, dur, k):
    """The closing question at a prompt, waiting for a y or an n."""
    q = spec.get("question")
    rows = textwrap.wrap(f"> {q} [y/n]" if q else f"> {spec.get('text', '')}", 38, subsequent_indent="  ")[:3]
    layers, t = [], 0.3
    for i, r in enumerate(rows):
        f, t = typed(ctx, r, 64, ctx.ink, 110, 360 + i * 92, t, cps=30)
        layers += f
    layers.append(cursor(ctx, 64, ctx.ink, 110 + (len(rows[-1]) + 1) * MONO_EM * 64, 360 + (len(rows) - 1) * 92, t))
    sig = "  ·  ".join(x for x in ((spec.get("text") if q else None), spec.get("sub")) if x)
    if sig:
        layers.append(text(ctx, sig.lower(), 34, ctx.accent2, 110, 420 + len(rows) * 92, t0=0.2, rise=8))
    card_scene(ctx, out, dur, layers)


# ---------- keynote format: a launch keynote ----------
def centered(ctx, rows, size, color, y, font, t0, step, rise=30):
    return [text(ctx, r, size, color, "(w-text_w)/2", y + i * size * 1.18, font=font, t0=t0 + i * step, rise=rise)
            for i, r in enumerate(rows)]


def scene_statement(ctx, spec, out, dur, k):
    """The hook centred, a line on each beat."""
    lines = (lines_of(spec.get("lines")) or [spec.get("text", "")])[:3]
    size = 104 if max(len(l) for l in lines) <= 22 else 84
    y = 500 - len(lines) * size * 1.18 / 2
    layers = centered(ctx, lines, size, ctx.ink, y, ctx.bold, 0.15, ctx.beat)
    if spec.get("sub"):
        layers += centered(ctx, textwrap.wrap(spec["sub"], 64)[:2], 36, ctx.muted, y + len(lines) * size * 1.18 + 40,
                           ctx.regular, 0.4 + len(lines) * ctx.beat, 0.1, rise=12)
    card_scene(ctx, out, dur, layers)


def scene_reveal(ctx, spec, out, dur, k):
    """"Introducing", the name on the drop, then what it does."""
    name = spec["text"]
    size = 150 if len(name) <= 18 else 116
    layers = [text(ctx, "Introducing", 40, ctx.muted, "(w-text_w)/2", 330, font=ctx.regular, rise=16),
              text(ctx, name, size, ctx.ink, "(w-text_w)/2", 400, t0=0.12, rise=40, dur=0.5)]
    bars = Bars()
    bars.add((ctx.W - ctx.px(240)) // 2, ctx.px(400 + size + 40), ctx.px(240), ctx.px(6), ctx.accent, 0.4, 0.6)
    layers += centered(ctx, lines_of(spec.get("sub"))[:2], 38, ctx.muted, 400 + size + 90, ctx.regular, 0.7, 0.15, rise=12)
    foot = "  ·  ".join(x for x in (k["brand"].get("day"), "#buildinpublic") if x)
    layers.append(text(ctx, foot, 28, ctx.accent, "(w-text_w)/2", 960, font=ctx.regular, t0=1.1, rise=8))
    card_scene(ctx, out, dur, layers, bars)


def scene_word(ctx, spec, out, dur, k):
    """The chapter's verb alone and huge, its number above it."""
    card_scene(ctx, out, dur, [
        text(ctx, f"{k['index']:02d}", 44, ctx.accent, "(w-text_w)/2", 330, rise=12),
        text(ctx, spec.get("chapter", ""), 220, ctx.ink, "(w-text_w)/2", 400, t0=0.05, rise=36)])


def scene_device(ctx, spec, out, dur, k):
    """The footage on a laptop while the camera pushes in, the caption underneath."""
    inputs, parts, size, speed, nb = footage_src(ctx, spec, dur)
    SW_, SH_, B = 1152, 720, 18
    sw, shh = ctx.px(SW_) // 2 * 2, ctx.px(SH_) // 2 * 2
    X, Y = ctx.px((1920 - SW_) // 2), ctx.px(92)
    bez_w, bez_h = sw + 2 * ctx.px(B), shh + 2 * ctx.px(B)
    bx, by = X - ctx.px(B), Y - ctx.px(B)
    bezel = ctx.slab(bez_w, bez_h, ctx.px(26), "0x151A26")
    _, shadow = ctx.card_assets(bez_w, bez_h, radius=26)
    mask, _ = ctx.card_assets(sw, shh)
    base_w, notch_w = bez_w + ctx.px(180), ctx.px(200)
    base = ctx.slab(base_w, ctx.px(24), ctx.px(12), "0xC9CFDA")
    notch = ctx.slab(notch_w, ctx.px(8), ctx.px(4), "0xA9B1C2")
    pad = ctx.px(60)
    u = f"min(1\\,t/{dur:.3f})"
    parts.append(fitted(spec, size, sw, shh, f"1+0.22*pow({u}\\,2)*(3-2*{u})"))    # eased push-in
    parts.append("[foot][3:v]alphamerge[fa]")
    parts.append(f"[0:v]format=rgba[bg];[bg][2:v]overlay=x={bx-pad}:y={by-pad}[b1];[b1][4:v]overlay=x={bx}:y={by}[b2];"
                 f"[b2][fa]overlay=x={X}:y={Y}[b3];[b3][5:v]overlay=x={(ctx.W-base_w)//2}:y={by+bez_h}[b4];"
                 f"[b4][6:v]overlay=x={(ctx.W-notch_w)//2}:y={by+bez_h}[base]")
    rows = textwrap.wrap(" ".join(lines_of(spec.get("caption"))), 52)[:2]
    layers = centered(ctx, rows, 46, ctx.ink, 92 + SH_ + B + 64, ctx.bold, 0.3, ctx.beat / 2, rise=16)
    if speed > 1.5:
        layers += speed_badge(ctx, speed, X + sw - ctx.px(130), Y + ctx.px(18))
    inputs = (bg_inputs(ctx, dur) + inputs + still(ctx, shadow, dur) + still(ctx, mask, dur)
              + still(ctx, bezel, dur) + still(ctx, base, dur) + still(ctx, notch, dur))
    render_scene(ctx, out, dur, inputs, ";".join(parts), layers, Bars())
    return speed, nb


def scene_numbers(ctx, spec, out, dur, k):
    """The stats as a 2 x 2 grid of numbers counting up, the design detail in the accent."""
    items, hl = spec["items"][:4], spec.get("highlight")
    layers = [text(ctx, spec.get("label") or "By the numbers", 34, ctx.muted, "(w-text_w)/2", 120,
                   font=ctx.regular, rise=10)]
    for i, (val, label) in enumerate(items):
        cx, y, t0 = (560, 1360)[i % 2], (230, 560)[i // 2], ctx.at(0.25, 0.15, i)
        color = ctx.accent if hl == i else ctx.ink
        x = f"{ctx.px(cx)}-text_w/2"
        layers.append(countup(ctx, val, 150, color, x, t0, y) if whole(val) else text(ctx, str(val), 150, color, x, y, t0=t0))
        layers.append(text(ctx, label, 36, ctx.accent if hl == i else ctx.muted, x, y + 190, font=ctx.regular,
                           t0=t0 + 0.15, rise=10))
    if spec.get("note"):
        layers.append(text(ctx, spec["note"], 34, ctx.ink, "(w-text_w)/2", 900, font=ctx.regular, t0=1.6, rise=10))
    card_scene(ctx, out, dur, layers)


def scene_close(ctx, spec, out, dur, k):
    """The closing question centred, the day under it."""
    q = spec.get("question")
    rows = textwrap.wrap(q or spec.get("text", ""), 30)[:3]
    layers = centered(ctx, rows, 84, ctx.ink, 470 - len(rows) * 84 * 1.18 / 2, ctx.bold, 0.15, ctx.beat / 2)
    sig = "  ·  ".join(x for x in ((spec.get("text") if q else None), spec.get("sub")) if x)
    if sig:
        layers.append(text(ctx, sig, 38, ctx.accent, "(w-text_w)/2", 760, font=ctx.regular, t0=1.0, rise=10))
    card_scene(ctx, out, dur, layers)


SCENES = {
    "cards": dict(hook=scene_hook, title=scene_title, footage=scene_footage, stats=scene_stats, end=scene_end),
    "magazine": dict(cover=scene_cover, footage=scene_page, stats=scene_infobox, end=scene_quote),
    "console": dict(hook=scene_boot, title=scene_banner, footage=scene_terminal, stats=scene_readout,
                    end=scene_prompt),
    "keynote": dict(hook=scene_statement, title=scene_reveal, word=scene_word, footage=scene_device,
                    stats=scene_numbers, end=scene_close),
}


def timeline(plan, fmt):
    """The video in order, as the format stages it: one entry per clip, {kind, beats, spec,
    index, music}, where music lists the (name, beats, role) sections that compose.py lays the
    track over. Roles: intro, drop, groove, return (the groove dropping back in after the
    break), break, outro."""
    fb = FORMAT_BEATS.get(fmt, {})

    def beats(spec, key, default):
        return spec.get("beats", default) if fmt == "cards" else fb[key]

    out = []

    def add(kind, n, spec, music, index=0):
        out.append({"kind": kind, "beats": n, "spec": spec, "index": index, "music": music})

    hook, title = plan.get("hook"), plan.get("title")
    if fmt == "magazine":
        if hook or title:      # one cover: the standfirst under the riser, the headline on the drop
            add("cover", fb["intro"] + fb["title"], plan,
                [("hook", fb["intro"], "intro"), ("title", fb["title"], "drop")])
    else:
        if hook:
            n = beats(hook, "intro", 6)
            add("hook", n, hook, [("hook", n, "intro")])
        if title:
            n = beats(title, "title", 6)
            add("title", n, title, [("title", n, "drop")])
    after_break, chapter = False, 0
    for sc in plan.get("scenes", []):
        kind = sc.get("type", "footage")
        if kind == "stats":
            n = beats(sc, "stats", 8)
            add("stats", n, sc, [("stats", n, "break")])
            after_break = True
            continue
        if kind != "footage":
            sys.exit(f"render.py: unknown scene type {kind!r}")
        chapter += 1
        name, role = sc.get("chapter", "scene"), ("return" if after_break else "groove")
        if fmt == "keynote":   # the verb alone, then the footage
            add("word", fb["word"], sc, [(name, fb["word"], role)], chapter)
            add("footage", fb["chapter"], sc, [(name, fb["chapter"], "groove")], chapter)
        else:
            n = beats(sc, "chapter", 10)
            add("footage", n, sc, [(name, n, role)], chapter)
        after_break = False
    if plan.get("end"):
        n = beats(plan["end"], "end", 8)
        add("end", n, plan["end"], [("end", n, "outro")])
    return out


# ---------- assembly ----------
def assemble(ctx, plan, clips, out, lead):
    """Join the clips (hard cuts, or the theme's transition), lay the progress bar, the brand
    footer of the cards format, and the music over them. lead is how many clips come before the
    first chapter."""
    total = sum(d for _, d in clips)
    parts = []
    if ctx.tail:
        # Each clip runs on by the transition's length and the next starts over that tail, so
        # every scene still begins on its beat and the total stays the sum of the scenes.
        inputs, cur, t = [], "0:v", 0.0
        for p, _ in clips:
            inputs += ["-i", p]
        for i in range(1, len(clips)):
            t += clips[i - 1][1]
            parts.append(f"[{cur}][{i}:v]xfade=transition={ctx.th['cut'][0]}:duration={ctx.tail}:offset={t:.3f}[x{i}]")
            cur = f"x{i}"
    else:
        lst = os.path.join(ctx.tmp, "list.txt")
        with open(lst, "w") as fh:
            fh.write("".join(f"file '{p}'\n" for p, _ in clips))
        inputs, cur = ["-f", "concat", "-safe", "0", "-i", lst], "0:v"
    n = inputs.count("-i")             # music is input n, the progress bar n + 1
    brand = plan.get("brand") or {} if ctx.th["format"] == "cards" else {}
    t_in = sum(d for _, d in clips[:lead])
    t_out = total - clips[-1][1] if plan.get("end") else total
    parts += [f"[{n+1}:v]scale=w='max(2\\,{ctx.W}*t/{total:.3f})':h={ctx.px(12)}:eval=frame[pb]",
              f"[{cur}][pb]overlay=x=0:y={ctx.H-ctx.px(12)}:eval=frame:shortest=1[p1]"]
    cur = "p1"
    en = f":enable='between(t\\,{t_in:.3f}\\,{t_out:.3f})'"
    if brand.get("name"):
        parts.append(f"[{cur}]drawtext=fontfile='{ctx.bold}':textfile='{ctx.textfile(brand['name'])}':fontsize={ctx.px(22)}"
                     f":fontcolor={ctx.muted}:x={ctx.px(80)}:y={ctx.px(1022)}{en}[p2]")
        cur = "p2"
    if brand.get("day"):
        parts.append(f"[{cur}]drawtext=fontfile='{ctx.bold}':textfile='{ctx.textfile(brand['day'])}':fontsize={ctx.px(22)}"
                     f":fontcolor={ctx.muted}:x=w-tw-{ctx.px(80)}:y={ctx.px(1022)}{en}[p3]")
        cur = "p3"
    parts.append(f"[{cur}]format=yuv420p[v]")

    music = plan.get("music") or {}
    mfile = music.get("file")
    if mfile and os.path.exists(mfile):
        inputs += ["-stream_loop", "-1", "-i", mfile]
        vol = float(music.get("volume_db", 0))
        parts.append(f"[{n}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,volume={vol}dB,"
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
        fmt = ctx.th["format"]
        items = timeline(plan, fmt)
        k = {"brand": plan.get("brand") or {}, "plan": plan,
             "chapters": [it["spec"].get("chapter", "") for it in items if it["kind"] == "footage"]}
        clips = []
        for i, it in enumerate(items):
            kind, spec, dur = it["kind"], it["spec"], it["beats"] * ctx.beat
            p = os.path.join(tmp, f"s{i:02d}-{kind}.mp4")
            res = SCENES[fmt][kind](ctx, spec, p, dur, {**k, "index": it["index"], "page": i + 1})
            clips.append((p, dur))
            if kind == "footage":
                speed, nb = res
                print(f"  {it['index']:02d} {spec.get('chapter', ''):<10} {dur:.2f}s  {speed:.1f}x  blur boxes {nb}  "
                      f"{' / '.join(lines_of(spec.get('caption')))}")
            else:
                print(f"  {kind:<7} {dur:.2f}s" + (f"  {spec.get('items')}" if kind == "stats" else ""))
        lead = next((i for i, it in enumerate(items) if it["kind"] in ("footage", "word", "stats")), len(items))
        total = assemble(ctx, plan, clips, out, lead)
        print(f"render.py: {out}  {total:.1f}s  {ctx.W}x{ctx.H}@{ctx.fps}  {len(clips)} scenes  {ctx.bpm:g} bpm  {fmt}")
        if not 30 <= total <= 45:
            print(f"  note: {total:.1f}s is outside the 30-45s target; adjust beats in the plan")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
