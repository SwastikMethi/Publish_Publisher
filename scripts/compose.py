#!/usr/bin/env python3
"""Compose an original music track that follows the edit plan's beat grid.

  compose.py plan.json [--mood energetic|calm] [--seed N] [--out output/media/music.mp3]

Reads bpm, the hook/title/scenes/end structure and their beat counts from the plan, and
writes a track whose sections line up with the video: a filtered intro with a riser under the
hook, a drop on the first frame of the title, a full groove under the chapters, a break with a
riser under the stats card, a second drop on the chapter after it, and a tail that fades with
the end card. Every note is synthesised here, so the result is original and safe to publish;
nothing is sampled or downloaded. Runs in about a second.

Moods:
  energetic  120-130 bpm electro-pop: four-on-the-floor kick, claps, 16th hats, side-chained saw
             bass, supersaw stabs on the off-beats, a short lead hook. Default.
  calm       78-92 bpm lo-fi: felt-piano chords, soft sub bass, brushed drums, vinyl crackle.

Requires numpy (`python3 -m pip install numpy`). ffmpeg does the final compression and
loudness (-14 LUFS, the level social platforms expect from a music-only video).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave

try:
    import numpy as np
except ImportError:
    sys.exit("compose.py: numpy is required: python3 -m pip install numpy\n"
             "  (or drop a licensed track into assets/music/ and point the plan's music.file at it)")

SR = 44100


# ---------- shared synthesis helpers ----------
def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def lowpass(x, cutoff):
    """One-pole low-pass as a short convolution (no scipy)."""
    a = np.exp(-2 * np.pi * cutoff / SR)
    k = int(min(len(x), max(8, SR / cutoff * 8)))
    kern = (1 - a) * a ** np.arange(k)
    return np.convolve(x, kern)[:len(x)]


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def env_exp(n, tau):
    return np.exp(-np.arange(n) / SR / tau)


def saw(f, t, detune=(0,)):
    out = np.zeros_like(t)
    for d in detune:
        out += 2 * ((t * f * 2 ** (d / 1200)) % 1.0) - 1
    return out / len(detune)


class Track:
    def __init__(self, beats, bpm, tail=2.0):
        self.beat = 60.0 / bpm
        self.n = int((beats * self.beat + tail) * SR)
        self.stems = {}

    def stem(self, name):
        if name not in self.stems:
            self.stems[name] = np.zeros(self.n)
        return self.stems[name]

    def at(self, name, t, sig):
        buf = self.stem(name)
        i = int(t * SR)
        j = min(self.n, i + len(sig))
        if i < self.n:
            buf[i:j] += sig[:j - i]


# ---------- sections from the plan ----------
def sections_from_plan(plan):
    """Walk the plan in order and give every stretch of beats a musical role."""
    secs, b = [], 0

    def add(name, beats, **role):
        nonlocal b
        if beats > 0:
            secs.append({"name": name, "start": b, "end": b + beats, **role})
            b += beats

    if plan.get("hook"):
        add("hook", plan["hook"].get("beats", 6), drums=False, full=False, pad=True, riser=True)
    if plan.get("title"):
        add("title", plan["title"].get("beats", 6), drums=True, full=True, lead=False, impact=True)
    after_break = False
    for sc in plan.get("scenes", []):
        if sc.get("type", "footage") == "stats":
            add("stats", sc.get("beats", 8), drums=False, full=False, pad=True, riser=True)
            after_break = True
        else:
            add(sc.get("chapter", "scene"), sc.get("beats", 10), drums=True, full=True, lead=True,
                impact=after_break)
            after_break = False
    if plan.get("end"):
        add("end", plan["end"].get("beats", 8), drums=True, full=True, lead=False)
    return secs, b


def section_at(secs, beat):
    for s in secs:
        if s["start"] <= beat < s["end"]:
            return s
    return secs[-1]


# ---------- moods ----------
def energetic(tr, secs, total_beats, rng):
    B = tr.beat
    CH = [[57, 60, 64, 69], [53, 57, 60, 65], [55, 60, 64, 67], [55, 59, 62, 67]]   # Am F C G
    BASS = [45, 41, 48, 43]
    HOOK = [[76, None, 79, 81, None, 79, None, 76, 74, None, 72, None, 74, None, None, None],
            [77, None, 79, 81, None, 84, None, 81, 79, None, 77, None, 76, None, None, None]]
    for b in range(total_beats):
        t0, bar, pos = b * B, b // 4, b % 4
        sec = section_at(secs, b)
        drums, full = sec.get("drums", True), sec.get("full", True)
        chord, root = CH[bar % 4], BASS[bar % 4]
        if drums:
            n = int(0.4 * SR)
            tt = np.arange(n) / SR
            k = np.sin(2 * np.pi * (150 * np.exp(-tt * 40) + 48) * tt) * np.exp(-tt * 9)
            k += 0.4 * highpass(rng.normal(0, 1, n) * env_exp(n, 0.006), 2000)
            tr.at("kick", t0, np.tanh(k * 1.8) * 0.9)
            if pos in (1, 3):
                n = int(0.25 * SR)
                c = np.zeros(n)
                for off in (0, 0.012, 0.024):
                    i = int(off * SR)
                    c[i:] += rng.normal(0, 1, n - i) * env_exp(n - i, 0.045)
                c = highpass(c, 900) + 0.5 * np.sin(2 * np.pi * 190 * np.arange(n) / SR) * env_exp(n, 0.05)
                tr.at("snare", t0, c * 0.55)
            for s16 in range(4):
                if s16 == 2:
                    n = int(0.18 * SR)
                    h = highpass(rng.normal(0, 1, n) * env_exp(n, 0.07), 6000) * 0.28
                else:
                    n = int(0.05 * SR)
                    h = highpass(rng.normal(0, 1, n) * env_exp(n, 0.012), 6000) * (0.16 if s16 % 2 == 0 else 0.11)
                tr.at("hats", t0 + s16 * B / 4, h)
        if full:
            for e in range(2):
                f = midi(root + (12 if (pos == 3 and e == 1) else 0))
                n = int(B / 2 * SR * 0.95)
                tt = np.arange(n) / SR
                s = lowpass(saw(f, tt, (-6, 6)) * 0.6 + np.sin(2 * np.pi * f * tt) * 0.7, 520)
                amp = np.minimum(1, tt / 0.005) * (0.25 + 0.75 * np.minimum(1, tt / 0.09))
                tr.at("bass", t0 + e * B / 2, np.tanh(s * amp * 2.2) * 0.55)
            for e in (0, 1):
                if e == 0 and pos not in (0, 2):
                    continue
                n = int(B * 0.55 * SR)
                tt = np.arange(n) / SR
                s = sum(saw(midi(nn), tt, (-12, -5, 5, 12)) for nn in chord)
                s = lowpass(s, 2600) * env_exp(n, 0.16) * np.minimum(1, tt / 0.004)
                tr.at("chords", t0 + e * B / 2, s * 0.16)
            if sec.get("lead", True):
                pat = HOOK[(bar // 2) % 2]
                for s16 in range(4):
                    nn = pat[pos * 4 + s16]
                    if nn is None:
                        continue
                    n = int(B * 0.6 * SR)
                    tt = np.arange(n) / SR
                    s = (np.sin(2 * np.pi * midi(nn) * tt) + 0.25 * np.sign(np.sin(2 * np.pi * midi(nn) * tt))
                         + 0.3 * np.sin(2 * np.pi * midi(nn) * 2 * tt))
                    s = lowpass(s, 4500) * env_exp(n, 0.12) * np.minimum(1, tt / 0.003)
                    tr.at("lead", t0 + s16 * B / 4, s * 0.22)
                    tr.at("lead", t0 + s16 * B / 4 + B * 0.75, s * 0.09)
        elif sec.get("pad") and pos == 0:
            n = int(B * 4 * SR)
            tt = np.arange(n) / SR
            s = sum(saw(midi(nn), tt, (-10, 10)) for nn in chord)
            s = lowpass(s, 900) * np.minimum(1, tt / 0.4) * np.minimum(1, (B * 4 - tt) / 0.4)
            tr.at("chords", t0, s * 0.12)
        if sec.get("riser"):
            n = int(B * SR)
            prog = (b - sec["start"]) / max(1, sec["end"] - sec["start"])
            tr.at("fx", t0, highpass(rng.normal(0, 1, n), 800 + 6000 * prog) * (0.04 + 0.2 * prog))
        if sec.get("impact") and b == sec["start"]:
            n = int(1.2 * SR)
            tt = np.arange(n) / SR
            s = (np.sin(2 * np.pi * (90 * np.exp(-tt * 6) + 38) * tt) * np.exp(-tt * 3)
                 + highpass(rng.normal(0, 1, n), 1500) * np.exp(-tt * 5) * 0.4)
            tr.at("fx", t0, s * 0.8)
    mix = {"kick": 1.0, "snare": 0.9, "hats": 0.8, "bass": 1.0, "chords": 1.0, "lead": 1.0, "fx": 1.0}
    wide = {"chords": 0.35, "hats": 0.2, "lead": 0.25}
    return mix, wide, dict(highpass=30, comp="acompressor=threshold=-12dB:ratio=3:attack=5:release=120:makeup=2")


def calm(tr, secs, total_beats, rng):
    B = tr.beat
    CH = [[53, 60, 64, 67], [50, 57, 60, 65], [55, 58, 62, 65], [48, 55, 59, 64]]    # Fmaj7 Dm7 Gm7 Cmaj7
    BASS = [41, 38, 43, 36]
    for b in range(total_beats):
        t0, bar, pos = b * B, b // 4, b % 4
        sec = section_at(secs, b)
        drums, full = sec.get("drums", True), sec.get("full", True)
        chord, root = CH[bar % 4], BASS[bar % 4]
        if pos == 0:                                   # pad every bar, softer in breaks
            n = int((B * 4 + 1.5) * SR)
            tt = np.arange(n) / SR
            s = np.zeros(n)
            for nn in chord:
                for d in (-0.35, 0.35):
                    s += np.sin(2 * np.pi * midi(nn) * 2 ** (d / 1200) * tt + rng.uniform(0, 6.28)) * 0.5
            e = np.minimum(1, tt / 0.6) * np.minimum(1, np.maximum(0, (B * 4 + 1.4 - tt) / 1.4))
            tr.at("pad", t0, s * e * (0.18 if full else 0.12))
        if full:
            for off, ln in ((0, 1.6 * B), (2.5 * B, 1.2 * B)):
                if pos != 0:
                    break
                n = int((ln + 0.3) * SR)
                tt = np.arange(n) / SR
                s = np.sin(2 * np.pi * midi(root) * tt) + 0.25 * np.sin(2 * np.pi * 2 * midi(root) * tt)
                e = np.minimum(1, tt / 0.01) * np.minimum(1, np.maximum(0, (ln + 0.3 - tt) / 0.3))
                tr.at("bass", t0 + off, s * e * 0.32)
            pattern = [0, 1.5, 2.0, 3.25] if bar % 2 == 0 else [0.5, 1.75, 3.0]
            if pos == 0:
                for k, beat in enumerate(pattern):
                    f = midi(chord[(k + bar) % len(chord)] + 12)
                    n = int(1.2 * SR)
                    tt = np.arange(n) / SR
                    s = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) * np.exp(-tt * 6)
                         + 0.12 * np.sin(6 * np.pi * f * tt) * np.exp(-tt * 9)) * np.exp(-tt * 3.2)
                    tr.at("keys", t0 + beat * B + rng.uniform(-0.012, 0.012), s * 0.22)
        if drums:
            if pos in (0, 2):
                n = int(0.35 * SR)
                tt = np.arange(n) / SR
                tr.at("drums", t0, np.sin(2 * np.pi * (55 * np.exp(-tt * 18) + 40) * tt) * np.exp(-tt * 14) * 0.55)
            else:
                n = int(0.18 * SR)
                tr.at("drums", t0 + 0.01, rng.normal(0, 1, n) * env_exp(n, 0.036) * 0.10)
            for e in range(2):
                n = int(0.06 * SR)
                tr.at("drums", t0 + e * B / 2 + rng.uniform(-0.006, 0.006),
                      rng.normal(0, 1, n) * env_exp(n, 0.014) * (0.06 if e else 0.035))
        if sec.get("riser"):
            n = int(B * SR)
            prog = (b - sec["start"]) / max(1, sec["end"] - sec["start"])
            tr.at("fx", t0, highpass(rng.normal(0, 1, n), 1500 + 5000 * prog) * (0.01 + 0.06 * prog))
    crackle = rng.normal(0, 1, tr.n) * (rng.random(tr.n) < 0.0006) * 0.25 + rng.normal(0, 1, tr.n) * 0.004
    tr.stem("fx")[:] += crackle
    mix = {"pad": 1.0, "bass": 1.0, "keys": 1.0, "drums": 1.0, "fx": 1.0}
    wide = {"pad": 0.25, "keys": 0.2}
    return mix, wide, dict(highpass=40, comp="lowpass=f=6500,aecho=0.6:0.3:60|130:0.25|0.15,"
                                                 "acompressor=threshold=-14dB:ratio=2.5:attack=20:release=200")


MOODS = {"energetic": energetic, "calm": calm}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--mood", default=None, choices=sorted(MOODS))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if not shutil.which("ffmpeg"):
        sys.exit("compose.py: ffmpeg not found on PATH")
    with open(args.plan) as fh:
        plan = json.load(fh)
    music = plan.get("music") or {}
    mood = args.mood or music.get("mood", "energetic")
    out = args.out or music.get("file") or "output/media/music.mp3"
    seed = args.seed if args.seed is not None else int(music.get("seed", 7))
    bpm = float(plan.get("bpm", 125 if mood == "energetic" else 84))
    secs, total_beats = sections_from_plan(plan)
    if total_beats == 0:
        sys.exit("compose.py: the plan has no beats (no hook/title/scenes/end)")

    rng = np.random.default_rng(seed)
    tr = Track(total_beats, bpm)
    mix, wide, post = MOODS[mood](tr, secs, total_beats, rng)
    L = sum(tr.stem(k) * g for k, g in mix.items())
    R = L.copy()
    d1, d2 = int(0.009 * SR), int(0.013 * SR)
    for k, g in wide.items():
        s = tr.stem(k)
        L[d1:] += g * s[:-d1]
        R[d2:] += g * s[:-d2]
    peak = max(np.abs(L).max(), np.abs(R).max(), 1e-9)
    st = np.stack([L, R], 1) / peak * 0.9
    st = np.tanh(st * 1.15) / np.tanh(1.15)

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="pp-compose-")
    raw = os.path.join(tmp, "raw.wav")
    with wave.open(raw, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
    total_s = total_beats * tr.beat
    af = (f"highpass=f={post['highpass']},{post['comp']},loudnorm=I=-14:TP=-1.5:LRA=8,"
          f"afade=t=out:st={total_s:.3f}:d=1.5")
    codec = ["-c:a", "libmp3lame", "-b:a", "256k"] if out.endswith(".mp3") else []
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", af] + codec + [out],
                       capture_output=True, text=True)
    shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode:
        sys.exit("compose.py: ffmpeg failed:\n" + r.stderr[-2000:])
    print(f"compose.py: {out}  {mood}  {bpm:g} bpm  {total_beats} beats ({total_s:.1f}s)  seed {seed}")
    for s in secs:
        role = "break+riser" if s.get("riser") else ("drop" if s.get("impact") else "groove")
        print(f"  beats {s['start']:>3}-{s['end']:<3} {s['name']:<12} {role}")


if __name__ == "__main__":
    main()
