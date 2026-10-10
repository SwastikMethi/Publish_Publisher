#!/usr/bin/env python3
"""Compose an original music track that follows the edit plan's beat grid.

  compose.py plan.json [--mood NAME] [--seed N] [--out output/media/music.mp3]

Reads bpm and the video's timeline (render.timeline: the scenes in the order and for the beats
the theme's format stages them), and writes a track whose sections line up with the video: a filtered intro with a riser under the
hook, a drop on the first frame of the title, a full groove under the chapters, a break with a
riser under the stats card, a second drop on the chapter after it, and a tail that fades with
the end card. Every note is synthesised here, so the result is original and safe to publish;
nothing is sampled or downloaded. Runs in about a second.

Moods:
  energetic  120-130 bpm electro-pop: four-on-the-floor kick, claps, 16th hats, side-chained saw
             bass, supersaw stabs on the off-beats, a short lead hook. Default.
  calm       78-92 bpm lo-fi: felt-piano chords, soft sub bass, brushed drums, vinyl crackle.
  trap       140 bpm half-time trap: gliding 808s, hi-hat rolls, FM bell hook.
  indie      124 bpm acoustic indie: strummed guitar, stomps and claps, tambourine, glockenspiel,
             a page-flip on every cut.
  chiptune   144 bpm 8-bit: pulse-wave lead, fast arpeggios, triangle bass, noise drums.
  marimba    112 bpm launch-video pop: stomps and claps, marimba riff, plucked bass, whistle.

With no --mood and no music.mood, the plan's theme picks its paired track (THEME_MOOD).

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

import render      # the video's timeline, so the track's sections land on its cuts

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


# ---------- sections, from the same timeline render.py cuts the video to ----------
ROLES = {
    "intro": dict(drums=False, full=False, pad=True, riser=True),
    "drop": dict(drums=True, full=True, lead=False, impact=True),
    "groove": dict(drums=True, full=True, lead=True, impact=False),
    "return": dict(drums=True, full=True, lead=True, impact=True),
    "break": dict(drums=False, full=False, pad=True, riser=True),
    "outro": dict(drums=True, full=True, lead=False),
}


def sections_from_plan(plan):
    """Give every stretch of beats a musical role, in the order the theme's format stages it."""
    secs, b = [], 0
    for item in render.timeline(plan, render.theme_of(plan)[1]["format"]):
        for j, (name, beats, role) in enumerate(item["music"]):
            if beats > 0:          # cut: a new clip starts here, so a transition plays over it
                secs.append({"name": name, "start": b, "end": b + beats, "cut": j == 0, **ROLES[role]})
                b += beats
    return secs, b


def section_at(secs, beat):
    for s in secs:
        if s["start"] <= beat < s["end"]:
            return s
    return secs[-1]


# ---------- drums and fx shared by the newer moods (energetic and calm keep their own) ----------
def kick(rng, punch=150, body=48, decay=9, click=0.4):
    n = int(0.4 * SR)
    tt = np.arange(n) / SR
    k = np.sin(2 * np.pi * (punch * np.exp(-tt * 40) + body) * tt) * np.exp(-tt * decay)
    k += click * highpass(rng.normal(0, 1, n) * env_exp(n, 0.006), 2000)
    return np.tanh(k * 1.8) * 0.9


def clap(rng, tone=190):
    n = int(0.25 * SR)
    c = np.zeros(n)
    for off in (0, 0.012, 0.024):
        i = int(off * SR)
        c[i:] += rng.normal(0, 1, n - i) * env_exp(n - i, 0.045)
    return highpass(c, 900) + 0.5 * np.sin(2 * np.pi * tone * np.arange(n) / SR) * env_exp(n, 0.05)


def hat(rng, decay=0.012, cutoff=6000):
    n = int(max(0.05, decay * 6) * SR)
    return highpass(rng.normal(0, 1, n) * env_exp(n, decay), cutoff)


def glide(f0, f1, n, tau):
    """Phase of a tone gliding from f0 to f1 with time constant tau (seconds)."""
    tt = np.arange(n) / SR
    return np.cumsum(f1 + (f0 - f1) * np.exp(-tt / tau)) / SR


def riser_impact(tr, rng, sec, b, t0, gain=0.2):
    """A beat of rising noise through riser sections; a boom on the first beat of a drop."""
    if sec.get("riser"):
        n = int(tr.beat * SR)
        prog = (b - sec["start"]) / max(1, sec["end"] - sec["start"])
        tr.at("fx", t0, highpass(rng.normal(0, 1, n), 800 + 6000 * prog) * (0.04 + gain * prog))
    if sec.get("impact") and b == sec["start"]:
        n = int(1.2 * SR)
        tt = np.arange(n) / SR
        s = (np.sin(2 * np.pi * (90 * np.exp(-tt * 6) + 38) * tt) * np.exp(-tt * 3)
             + highpass(rng.normal(0, 1, n), 1500) * np.exp(-tt * 5) * 0.4)
        tr.at("fx", t0, s * 0.8)


def pad_bar(tr, t0, chord, cutoff, gain, detune=(-10, 10)):
    """A four-beat detuned-saw chord with soft edges."""
    n = int(tr.beat * 4 * SR)
    tt = np.arange(n) / SR
    s = sum(saw(midi(nn), tt, detune) for nn in chord)
    s = lowpass(s, cutoff) * np.minimum(1, tt / 0.3) * np.minimum(1, (tr.beat * 4 - tt) / 0.3)
    tr.at("pad", t0, s * gain)


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


_PLUCKS = {}


def pluck(f, dur, bright=0.5, damp=0.996):
    """A plucked string (Karplus-Strong): a burst of noise circulating in a delay line one period
    long, averaged a little on every pass, so it rings and then mellows like a real string.
    Cached per pitch, so every note at a pitch is the same pluck at its own level."""
    key = (round(f, 3), dur, bright, damp)
    if key not in _PLUCKS:
        N, n = max(2, int(round(SR / f))), int(dur * SR)
        out = np.zeros(n + 2 * N)
        out[:N] = lowpass(np.random.default_rng(int(f * 1000)).uniform(-1, 1, N), 1500 + 7000 * bright)
        for k in range(1, n // N + 2):             # one period at a time: y[i] = (y[i-N] + y[i-N-1]) / 2
            blk = out[(k - 1) * N:k * N]
            before = out[(k - 1) * N - 1] if k > 1 else 0.0
            out[k * N:(k + 1) * N] = damp * 0.5 * (blk + np.concatenate(([before], blk[:-1])))
        _PLUCKS[key] = out[:n]
    return _PLUCKS[key]


def indie(tr, secs, total_beats, rng):
    """Acoustic indie pop: a strummed steel-string guitar (down, down-up, up-down-up), a plucked
    bass, foot stomps and hand claps, tambourine and shaker, a glockenspiel line, and a paper
    page-flip on every cut. Breaks are fingerpicked while the shaker builds. G Em C D."""
    B, E = tr.beat, tr.beat / 2                    # a beat and an eighth
    CH = [[43, 47, 50, 55, 59, 67], [40, 47, 52, 55, 59, 64], [48, 52, 55, 60, 64], [50, 57, 62, 66]]
    ROOT = [43, 40, 36, 38]
    STRUM = [(0, 1), (2, 1), (3, -1), (5, -1), (6, 1), (7, -1)]     # (eighth, down 1 / up -1)
    BASS = [(0, 0), (3, 0), (4, 7), (7, 0)]                          # (eighth, semitones)
    PICK = [0, 2, 3, 4, 5, 4, 3, 2]                                  # string per eighth
    GLOCK = [[79, None, 83, None, 86, None, 83, None, 81, None, 79, None, 76, None, None, None],
             [79, None, 83, None, 86, None, 88, None, 86, None, 83, None, 81, None, None, None]]

    def note(stem, t, f, length, gain, bright=0.5, damp=0.996):
        n = int(length * SR)
        s = pluck(f, length + 0.05, bright, damp)[:n]
        tr.at(stem, t, s * np.minimum(1, (n - np.arange(n)) / (0.03 * SR)) * gain)   # damped by the next stroke

    def stomp():
        n = int(0.3 * SR)
        tt = np.arange(n) / SR
        body = np.sin(2 * np.pi * glide(110, 55, n, 0.03)) * np.exp(-tt * 14)
        thud = lowpass(rng.normal(0, 1, n), 400) * np.exp(-tt * 25) * 3
        return np.tanh((body + thud) * 1.5) * 0.8

    def handclap():
        n = int(0.2 * SR)
        c = np.zeros(n)
        for _ in range(4):                         # a few people, never quite together
            i = int(rng.uniform(0, 0.018) * SR)
            c[i:] += rng.normal(0, 1, n - i) * env_exp(n - i, 0.012)
        return highpass(lowpass(c, 3200), 700) * 1.6

    def tamb(decay):
        n = int(0.15 * SR)
        tt = np.arange(n) / SR
        jingle = sum(np.sin(2 * np.pi * f * tt + rng.uniform(0, 6.28)) for f in (5200, 6800, 8100, 9600)) * 0.25
        return (highpass(rng.normal(0, 1, n), 5000) * 0.6 + jingle) * env_exp(n, decay)

    def page_turn():
        n = int(0.4 * SR)
        tt = np.arange(n) / SR
        s = highpass(lowpass(rng.normal(0, 1, n), 6000), 1500) * np.sin(np.pi * tt / 0.4) ** 2
        crinkle = highpass((rng.random(n) < 0.004) * rng.normal(0, 1, n), 3000) * np.exp(-tt * 6)
        return s * 0.5 + crinkle * 0.8

    for sec in secs:
        if sec.get("cut") and sec["start"] > 0:
            tr.at("swish", max(0.0, sec["start"] * B - 0.05), page_turn() * 0.5)
    for b in range(total_beats):
        t0, bar, pos = b * B, b // 4, b % 4
        sec = section_at(secs, b)
        full, drums = sec.get("full", True), sec.get("drums", True)
        chord, root = CH[bar % 4], ROOT[bar % 4]
        prog = (b - sec["start"]) / max(1, sec["end"] - sec["start"])
        if pos == 0 and full:
            for j, (e, d) in enumerate(STRUM):
                nxt = STRUM[j + 1][0] if j + 1 < len(STRUM) else 8
                strings, gap = (chord, 0.012) if d > 0 else (chord[::-1][:4], 0.008)
                for i, nn in enumerate(strings):
                    note("guitar", t0 + e * E + i * gap, midi(nn), (nxt - e) * E + 0.05,
                         (0.3 if d > 0 else 0.2) * rng.uniform(0.85, 1.1))
            for j, (e, up) in enumerate(BASS):
                nxt = BASS[j + 1][0] if j + 1 < len(BASS) else 8
                note("bass", t0 + e * E, midi(root + up), (nxt - e) * E, 0.3, bright=0.15, damp=0.995)
        elif pos == 0:
            for e, s in enumerate(PICK):
                note("guitar", t0 + e * E, midi(chord[min(s, len(chord) - 1)]), 3 * E, 0.32)
        if drums:
            if pos in (0, 2):
                tr.at("stomp", t0, stomp() * 0.6)
            if pos == 3 and bar % 2:
                tr.at("stomp", t0 + E, stomp() * 0.42)
            if pos in (1, 3):
                tr.at("clap", t0, handclap() * 0.19)
            for e in range(2):                     # tambourine eighths, the off-beat louder
                tr.at("tamb", t0 + e * E, tamb(0.07 if e else 0.04) * (0.16 if e else 0.1))
        else:                                      # intro and break: the shaker builds, claps join late
            for s16 in range(4):
                tr.at("shaker", t0 + s16 * B / 4, hat(rng, decay=0.02, cutoff=6000) * (0.05 + 0.2 * prog))
            if sec["end"] - b <= 2:
                tr.at("clap", t0, handclap() * 0.15)
                tr.at("clap", t0 + E, handclap() * 0.11)
        if sec.get("impact") and b == sec["start"]:   # the drop: everyone at once
            tr.at("tamb", t0, tamb(0.25) * 0.3)
        if full and sec.get("lead", True):
            for s16 in range(4):
                nn = GLOCK[(bar // 2) % 2][pos * 4 + s16]
                if nn is None:
                    continue
                n = int(0.9 * SR)
                tt = np.arange(n) / SR
                f = midi(nn)
                s = (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * 2.76 * f * tt) * np.exp(-tt * 8)
                     + 0.2 * np.sin(2 * np.pi * 5.4 * f * tt) * np.exp(-tt * 16)) * np.exp(-tt * 3.5)
                tr.at("glock", t0 + s16 * B / 4, s * np.minimum(1, tt / 0.001) * 0.07)
    mix = {"guitar": 1.0, "bass": 1.0, "stomp": 1.0, "clap": 0.9, "tamb": 0.8, "shaker": 0.8, "glock": 1.0,
           "swish": 1.0}
    wide = {"guitar": 0.35, "tamb": 0.2, "glock": 0.25, "shaker": 0.2}
    return mix, wide, dict(highpass=40, comp="aecho=0.8:0.6:35|70:0.18|0.1,"
                                             "acompressor=threshold=-14dB:ratio=2.5:attack=10:release=150:makeup=2")


def chiptune(tr, secs, total_beats, rng):
    """8-bit chiptune: a pulse-wave lead with vibrato, 32nd-note chord arpeggios, a triangle bass
    bouncing between octaves, and drums made of pitch-swept squares and noise. Dm Bb C A."""
    B, S = tr.beat, tr.beat / 4
    CH = [[62, 65, 69], [58, 62, 65], [60, 64, 67], [57, 61, 64]]                    # Dm Bb C A
    ROOT = [50, 46, 48, 45]
    LEAD = [[74, None, 77, None, 81, None, 79, 77, None, 76, None, 77, None, None, 74, None],
            [74, None, 77, None, 81, None, 84, None, 82, None, 81, None, 79, None, None, None]]

    def pulse(ph, duty):
        return np.where(ph % 1 < duty, 1.0, -1.0)

    def noise(n, tau):
        return np.sign(rng.normal(0, 1, n)) * env_exp(n, tau)

    for b in range(total_beats):
        t0, bar, pos = b * B, b // 4, b % 4
        sec = section_at(secs, b)
        full, drums = sec.get("full", True), sec.get("drums", True)
        chord, root = CH[bar % 4], ROOT[bar % 4]
        for s32 in range(8):                           # the arpeggio never stops; quieter in breaks
            n = int(S / 2 * SR)
            tt = np.arange(n) / SR
            f = midi(chord[(pos * 8 + s32) % 3] + 12)
            tr.at("arp", t0 + s32 * S / 2, pulse(tt * f, 0.125) * (0.05 if full else 0.035))
        if drums:
            if pos in (0, 2) or (pos == 3 and bar % 2):
                n = int(0.12 * SR)
                k = pulse(glide(180, 50, n, 0.03), 0.5) * env_exp(n, 0.05)
                tr.at("kick", t0 + (S * 2 if pos == 3 else 0), k * 0.5)
            if pos in (1, 3):
                tr.at("snare", t0, highpass(noise(int(0.12 * SR), 0.05), 1500) * 0.35)
            for e in range(2):
                tr.at("hats", t0 + e * B / 2, highpass(noise(int(0.03 * SR), 0.008), 6000) * (0.15 if e else 0.08))
        if full:
            for e in range(2):
                n = int(B / 2 * SR * 0.9)
                tt = np.arange(n) / SR
                f = midi(root + (12 if e else 0))
                tri = 2 * np.abs(2 * ((tt * f) % 1) - 1) - 1
                tr.at("bass", t0 + e * B / 2, tri * np.minimum(1, (n - np.arange(n)) / (0.005 * SR)) * 0.4)
            if sec.get("lead", True):
                for s16 in range(4):
                    nn = LEAD[(bar // 2) % 2][pos * 4 + s16]
                    if nn is None:
                        continue
                    n = int(B * 0.5 * SR)
                    tt = np.arange(n) / SR
                    ph = np.cumsum(midi(nn) * (1 + 0.01 * np.sin(2 * np.pi * 6 * tt) * np.minimum(1, tt / 0.15))) / SR
                    tr.at("lead", t0 + s16 * S, pulse(ph, 0.25) * np.minimum(1, (n - np.arange(n)) / (0.01 * SR)) * 0.09)
        riser_impact(tr, rng, sec, b, t0, gain=0.12)
    mix = {"arp": 1.0, "kick": 1.0, "snare": 0.9, "hats": 0.8, "bass": 1.0, "lead": 1.0, "fx": 1.0}
    wide = {"arp": 0.3, "lead": 0.15}
    # Raw pulse waves alias into a fizz on phone speakers; a gentle top cut keeps the 8-bit bite.
    return mix, wide, dict(highpass=40, comp="lowpass=f=9000,acompressor=threshold=-12dB:ratio=3:attack=5:release=100:makeup=2")


def trap(tr, secs, total_beats, rng):
    """Half-time trap: gliding 808s under a short kick, a clap on beat three, hi-hats that roll
    into every second bar, an FM bell hook over a dark pad. Fm Db Ab Eb."""
    B, S = tr.beat, tr.beat / 4
    CH = [[53, 56, 60], [49, 53, 56], [56, 60, 63], [51, 55, 58]]                    # Fm Db Ab Eb
    ROOT = [41, 37, 44, 39]
    HITS = [[(0, 0), (6, 0), (10, 0)], [(0, 0), (3, 0), (8, 0), (11, 0), (14, 12)]]  # 16th step, glide from (semitones)
    BELL = [[77, None, None, 80, None, None, 84, None, 82, None, 80, None, 77, None, 75, None],
            [77, None, None, 80, None, None, 84, None, 87, None, 84, None, 82, None, None, None]]
    for b in range(total_beats):
        t0, bar, pos = b * B, b // 4, b % 4
        sec = section_at(secs, b)
        full = sec.get("full", True)
        chord, root = CH[bar % 4], ROOT[bar % 4]
        if pos == 0:
            pad_bar(tr, t0, chord, 900, 0.06 if full else 0.1, (-8, 8))
        if full and pos == 0:
            hits = HITS[bar % 2]
            for j, (step, up) in enumerate(hits):
                nxt = hits[j + 1][0] if j + 1 < len(hits) else 16
                n = int(min((nxt - step) * S, 1.6 * B) * SR)
                tt = np.arange(n) / SR
                f = midi(root)
                ph = glide(f * 2 ** (up / 12), f, n, 0.09) if up else glide(f * 1.6, f, n, 0.04)
                s = np.sin(2 * np.pi * ph) * np.minimum(1, tt / 0.002) * np.exp(-tt * 1.4)
                s *= np.minimum(1, (n - np.arange(n)) / (0.01 * SR))     # no click where the next hit cuts it
                tr.at("808", t0 + step * S, np.tanh(s * 2.4) * 0.7)
                tr.at("kick", t0 + step * S, kick(rng, punch=220, body=60, decay=22, click=0.6) * 0.7)
        if sec.get("drums", True):
            if pos == 2:
                tr.at("clap", t0, clap(rng, tone=210) * 0.6)
            roll = pos == 3 and bar % 2 == 1
            steps = (6 if bar % 4 == 1 else 8) if roll else 2
            for k in range(steps):
                v = (0.06 + 0.1 * k / steps) if roll else (0.14 if k == 0 else 0.1)
                tr.at("hats", t0 + k * B / steps, hat(rng, decay=0.008, cutoff=7000) * v)
        for s16 in range(4):
            nn = BELL[(bar // 2) % 2][pos * 4 + s16]
            if nn is None:
                continue
            n = int(0.9 * SR)
            tt = np.arange(n) / SR
            f = midi(nn)
            s = np.sin(2 * np.pi * f * tt + 2.2 * np.exp(-tt * 7) * np.sin(2 * np.pi * 3.5 * f * tt))
            tr.at("bell", t0 + s16 * S, s * np.exp(-tt * 4.5) * np.minimum(1, tt / 0.002) * (0.12 if full else 0.08))
        riser_impact(tr, rng, sec, b, t0)
    mix = {"808": 1.0, "kick": 0.8, "clap": 0.9, "hats": 0.8, "bell": 1.0, "pad": 1.0, "fx": 1.0}
    wide = {"bell": 0.3, "pad": 0.3, "hats": 0.1}
    return mix, wide, dict(highpass=25, comp="acompressor=threshold=-12dB:ratio=3:attack=5:release=120:makeup=2")


def marimba(tr, secs, total_beats, rng):
    """Launch-video pop: a stomp on one and three, claps and snaps on two and four, a marimba
    riff over the chords, a plucked bass and a whistled hook. C G Am F."""
    B, S = tr.beat, tr.beat / 4
    CH = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]                    # C G Am F
    ROOT = [36, 43, 45, 41]
    RIFF = [0, 2, 1, 2, 0, 2, 1, 2]                # chord tone for each eighth, an octave up
    BLINE = [0, None, 0, 12, None, 0, 7, None]     # eighths over the root
    WHISTLE = [[79, None, None, 76, None, None, 74, None, 72, None, None, None, 74, None, 76, None],
               [79, None, None, 81, None, None, 79, None, 76, None, None, None, 74, None, None, None]]
    for b in range(total_beats):
        t0, bar, pos = b * B, b // 4, b % 4
        sec = section_at(secs, b)
        full, drums = sec.get("full", True), sec.get("drums", True)
        chord, root = CH[bar % 4], ROOT[bar % 4]
        if pos == 0:
            pad_bar(tr, t0, chord, 2000 if full else 1200, 0.03 if full else 0.07, (-6, 6))
        for e in range(2):                             # marimba: a sine and its bright 3.9x partial
            nn = chord[RIFF[pos * 2 + e]] + 12 + (12 if (bar % 2 and pos == 3 and e) else 0)
            n = int(0.4 * SR)
            tt = np.arange(n) / SR
            f = midi(nn)
            s = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * 3.9 * f * tt) * np.exp(-tt * 30)) * np.exp(-tt * 9)
            tr.at("marimba", t0 + e * B / 2, s * np.minimum(1, tt / 0.001) * (0.16 if full else 0.1))
        if drums:
            if pos in (0, 2):
                tr.at("kick", t0, kick(rng, punch=90, body=55, decay=9, click=0.5) * 0.9)
            if pos in (1, 3):
                tr.at("clap", t0, clap(rng, tone=230) * 0.6)
                n = int(0.04 * SR)
                tt = np.arange(n) / SR
                snap = highpass(rng.normal(0, 1, n), 2500) + np.sin(2 * np.pi * 1300 * tt)
                tr.at("snap", t0 + 0.012, snap * env_exp(n, 0.006) * 0.25)
            for s16 in range(4):
                tr.at("shaker", t0 + s16 * S, hat(rng, decay=0.012, cutoff=8000) * (0.06 if s16 % 2 else 0.035))
        if full:
            for e in range(2):
                up = BLINE[pos * 2 + e]
                if up is None:
                    continue
                n = int(B / 2 * SR * 0.9)
                tt = np.arange(n) / SR
                f = midi(root + up)
                s = (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(4 * np.pi * f * tt) * np.exp(-tt * 20)) * env_exp(n, 0.18)
                tr.at("bass", t0 + e * B / 2, np.tanh(s * np.minimum(1, tt / 0.003) * 1.5) * 0.5)
            if sec.get("lead", True):
                for s16 in range(4):
                    nn = WHISTLE[(bar // 2) % 2][pos * 4 + s16]
                    if nn is None:
                        continue
                    n = int(B * 0.9 * SR)
                    tt = np.arange(n) / SR
                    ph = np.cumsum(midi(nn) * (1 + 0.008 * np.sin(2 * np.pi * 5.5 * tt) * np.minimum(1, tt / 0.2))) / SR
                    s = np.sin(2 * np.pi * ph) + lowpass(rng.normal(0, 1, n), 3000) * 0.04
                    s *= np.minimum(1, tt / 0.02) * np.minimum(1, (n - np.arange(n)) / (0.05 * SR))
                    tr.at("lead", t0 + s16 * S, s * 0.07)
        riser_impact(tr, rng, sec, b, t0)
    mix = {"marimba": 1.0, "kick": 1.0, "clap": 0.85, "snap": 0.8, "shaker": 0.7, "bass": 1.0, "lead": 1.0,
           "pad": 1.0, "fx": 1.0}
    wide = {"marimba": 0.3, "pad": 0.3, "lead": 0.2, "shaker": 0.15}
    return mix, wide, dict(highpass=30, comp="acompressor=threshold=-12dB:ratio=3:attack=6:release=120:makeup=2")


MOODS = {"energetic": energetic, "calm": calm, "trap": trap, "indie": indie, "chiptune": chiptune,
         "marimba": marimba}
BPM = {"energetic": 125, "calm": 84, "trap": 140, "indie": 124, "chiptune": 144, "marimba": 112}
# Each video theme in render.py has the track it was designed with; used when the plan names a
# theme but no music.mood.
THEME_MOOD = {"midnight": "energetic", "volt": "trap", "paper": "indie", "console": "chiptune",
              "keynote": "marimba"}


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
    mood = args.mood or music.get("mood") or THEME_MOOD.get(render.theme_of(plan)[0], "energetic")
    if mood not in MOODS:
        sys.exit(f"compose.py: unknown mood {mood!r}; use one of {', '.join(MOODS)}")
    out = args.out or music.get("file") or "output/media/music.mp3"
    seed = args.seed if args.seed is not None else int(music.get("seed", 7))
    bpm = float(plan.get("bpm", BPM[mood]))
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
