# Demo video guidelines

Read this before stage 8. The finished video is an animation, not a recording. It has to hold
a stranger for forty seconds in a feed that autoplays muted: a hook line before anything else,
the title landing on the first beat of the music, four or five numbered chapters with the
product on the right and a large caption on the left, a stats card with counting numbers, and
an end card that asks a question. A progress bar runs along the bottom and an original track
is composed to the same beat grid. Thirty-three to forty-two seconds.

The product appears as real stills: captures of its screens shown whole and unchanged, or the
real output of a real run shown as text. Rings point at things. Nothing is redrawn by hand,
nothing is recorded, and nothing is blurred.

One page draws all of it: `assets/animation/index.html`, the template. It reads
`output/media/plan.json` and is a pure function of time, so frame 300 looks the same every
time it is drawn. The same plan drives the music, so picture and track cannot drift apart.

Four passes: capture the stills, write the plan, build it and look at stills, then compose,
render, assemble and scan.

## Pass 1: capture the stills

A still is the product in one state. Most chapters need two: before and after the thing the
chapter is about. List the states from the demo plan (stage 6) before capturing anything, and
save each to `output/media/flow/assets/NN-slug.png` (or `.txt`).

| The product is | Capture with | Notes |
|---|---|---|
| A web app | Playwright: `browser_resize` to 1200 × 750, set up the state, `browser_take_screenshot` of the viewport | 1200 × 750 keeps the page's text readable in the video; the post's own screenshots stay 1440 × 900 |
| A phone app | The emulator's or simulator's own screenshot of the whole screen (`adb exec-out screencap -p > file.png`) | Never a person's real phone |
| A tool with no screen (command line, library, agent skill) | The real output of a real run, as text: `{ echo '$ <command>'; <command>; } > output/media/flow/assets/NN-slug.txt 2>&1` | Run it from the repository root with relative paths, so no home path is printed. Strip colour codes |

Rules for every still:

- It shows the product doing its job with content loaded: no spinner, empty state, error,
  cookie banner, tooltip or focus ring, unless that is the feature.
- It is used whole. Do not crop, retouch or composite a capture. To draw the eye, add a ring
  in the plan; to bring small text closer on a web capture, add a `focus` in the plan.
- A line of output is never edited. Whole lines may be deleted to shorten it; keep the
  untouched output beside it as `NN-slug.full.txt`.
- Nothing from the never-show list is in it: credentials, tokens, emails, account names,
  private URLs, home-directory paths, notifications, other windows, the agent's own terminal.
  A still that shows one is taken again with the cause removed. There is no blur step.
- Use made-up sample data that cannot be taken for the real thing (a `555` phone number, a
  name with no account behind it).

While the state is on screen, note where the things worth pointing at are, in the capture's
own pixels: for a web page, `await page.locator(...).boundingBox()` gives `x, y, width,
height` directly; for Android, the `bounds` in a `uiautomator dump`; otherwise read them off
the capture (the Read tool says by how much it scaled the picture down).

## Pass 2: write the plan

### The spine

The video has the same spine as the post. Every part is an entry in the plan, and every entry
states its length in beats:

```
hook     8 beats   the spark as one or two big lines, and what you built as a smaller line
title    6 beats   project name; the lines under it are the post's "you give it X, it gives you Y"
01..05   10-12     four or five chapters, one idea each: the demo plan's steps in order
stats    8 beats   real numbers from the run, the design detail as the highlighted one
end      8-10      Day N/30, the theme hashtag, and the post's closing question
```

Put the stats card after the third or fourth chapter, never last: the music breaks there and
drops again on the chapter that follows, so the strongest chapter goes after it. Total 76 to
84 beats. Fewer than four chapters means the demo plan was too thin.

### Chapters

Each chapter is one thing the product does. Its fields:

- `chapter`: one or two words, shown very large: Search, Score, Kind words.
- `group`: a short label over the number, shared by chapters that belong together.
- `head`: one sentence saying what the product does here. `sub`: one more, smaller.
- `chips`: the parts of the product at work in this chapter (a model, a tool, a file).
- `stage` and its stills: see below.

Captions carry the meaning; the stills are the evidence. Say what the product does, not what
is on the screen: "A phone number is hidden before it goes", not "The redaction card opens".
No identifiers, file names or architecture nouns. Every caption and every number is a claim:
stage 10 checks them with the post's.

### The three stages

| `stage` | For | Fields | What it shows |
|---|---|---|---|
| `phones` | Portrait stills of a phone app | `shots`, each `{slot, src, at, rings}` | Two phones side by side: slot `a` is there from the start, slot `b` slides in when its first shot is due. One slot alone sits in the middle |
| `window` | Landscape stills of a web or desktop app | `shots`, each `{src, at, focus, rings}` | One card. Shots cross-fade in order. The same `src` twice in a row is one picture with the view moving: give the second a `focus` and the card pushes in on that part |
| `terminal` | Real output as text | `src` (the `.txt`) or `lines`, and `mark` | A terminal panel. Lines appear in order, a `$ ` line is typed out, and the line numbers in `mark` (from 0) are highlighted |

`at` is when a shot appears, in beats from the start of its chapter. A ring is `{at, until,
box}`: `box` is `[x, y, width, height]` in the capture's own pixels, `until` may be left out
(the ring then stays while its shot does). `focus` is a box of the same kind. Give each still
two beats or more before the next thing happens, and end each chapter on the result.

### Stats card

Up to four figures from the actual run, each with a short label, taken from what the product
printed or wrote. Never estimates. A whole number counts up; a figure with a unit is written
as text (`"1.7 GB"`, `"20 %"`). Make one of them the design detail whenever it is a number
("0 auto-submitted", "0 bytes sent") and set `highlight` to its position, from 0. `note` is
one sentence from the post; put `**` around the part to stress.

### Theme

The layout never changes. A theme is its colours, its display typeface and its track, and
themes rotate so the posts do not look like one template.

| `theme` | Colours | Typeface | `music.mood` | `bpm` |
|---|---|---|---|---|
| `aurora` | near-black, violet to blue | SF Pro | `marimba` | 120 |
| `ember` | warm black, amber to rose | Avenir Next | `trap` | 140 |
| `lagoon` | teal-black, mint to sky blue | Futura | `energetic` | 125 |
| `daylight` | cool off-white, dark ink, cobalt to violet | Charter | `indie` | 124 |

Pick it like this:

1. If the user named a theme, use it.
2. Otherwise read the `theme:` line of the last two video posts in
   `~/.project-publisher/posts/` and take its first word. Do not use either of those.
3. From what is left, prefer the one the captures stand out against: `daylight` when the
   product's own screens are dark, a dark theme when they are light.

Write the theme, its `bpm` and its `music.mood` into the plan, and name the theme when you
show the plan to the user.

### The plan file

Write `output/media/plan.json`. A real one, shortened to one chapter:

```json
{
  "output": "output/media/demo.mp4",
  "size": [1920, 1080], "fps": 30,
  "theme": "aurora", "bpm": 120,
  "brand": {"name": "Kids Chat", "day": "Day 23/30"},
  "badge": "Runs on the phone",
  "music": {"file": "output/media/music.mp3", "mood": "marimba", "seed": 23},
  "hook": {"lines": ["Kids can't avoid tech.", "Can it keep them safe?"],
           "sub": "I took the small on-device models from my keyboard\nand put them in a chat app for children.",
           "beats": 8},
  "title": {"text": "Kids Chat",
            "sub": ["A chat app demo for children, with 12 small AI models.",
                    "Every message is checked on the phone before it is sent."],
            "beats": 6},
  "scenes": [
    {"type": "chapter", "chapter": "Private", "group": "Before it is sent", "beats": 10,
     "head": "A phone number is hidden before it goes.",
     "sub": "The child sees the safer message first, and chooses.",
     "chips": ["Redact"], "stage": "phones",
     "shots": [
       {"slot": "a", "src": "assets/03-card.png", "at": 0,
        "rings": [{"at": 1.6, "until": 3.8, "box": [85, 1790, 1275, 200]},
                  {"at": 3.8, "until": 5.4, "box": [85, 2020, 1275, 190]}]},
       {"slot": "b", "src": "assets/04-sent.png", "at": 5.4,
        "rings": [{"at": 6.2, "box": [340, 2530, 940, 190]}]}
     ]},
    {"type": "stats", "label": "What stands between a child and send",
     "items": [[12, "small models, all of them on the phone"], [5, "checks, from unkind words to nudity"],
               [0, "bytes sent while the models work"], [1, "phone: a demo with two pretend users"]],
     "highlight": 2,
     "note": "One rule sits under all of it. **What cannot be checked is not sent.**",
     "beats": 8}
  ],
  "end": {"text": "Day 23/30", "sub": "#BuildInPublic",
          "question": "Would you want this for a child you know?", "accent": "a child you know?",
          "note": "Small models on the phone, no cloud AI.",
          "chips": ["Toxic", "Redact", "Moderator"], "beats": 10}
}
```

A `window` chapter and a `terminal` chapter, in the same place:

```json
{"type": "chapter", "chapter": "Split", "group": "The answer", "beats": 10,
 "head": "It shows what each person pays.", "sub": "And the same amount rounded up, for cash.",
 "chips": ["JavaScript"], "stage": "window",
 "shots": [
   {"src": "assets/02-split.png", "at": 0},
   {"src": "assets/02-split.png", "at": 3, "focus": [596, 125, 434, 275],
    "rings": [{"at": 5, "box": [640, 179, 342, 78]}]}
 ]},
{"type": "chapter", "chapter": "Check", "group": "From the command line", "beats": 12,
 "head": "One command checks a template before it ships.", "sub": "It names the line that is wrong.",
 "chips": ["Python"], "stage": "terminal", "src": "assets/05-check.txt", "mark": [3]}
```

The rest of the fields:

- `src` paths are relative to `output/media/flow/`. `output` and `music.file` are relative to
  the repository root, where the scripts are run from.
- `badge` is one chip shown in every chapter, for the thing true of all of them. Leave it out
  if there is none.
- `brand.day` and `end.text` are left out when no challenge day was given. `end.question` is
  the post's closing question and is left out when the user gave none; the end card then
  shows the project name. `end.accent` is the part of the question drawn in the accent
  colours; `title.accent` does the same for the name (by default its last word).
- `\n` in a `sub` breaks the line there.
- `music.seed` keeps the same track on a re-run. A licensed track in `assets/music/` can be
  used by pointing `music.file` at it; then the beats will not match it.

Show the plan to the user in a few lines: the theme, the hook, the chapter names with their
`head` lines, the four stats, the question.

## Pass 3: build it and look at stills

```
mkdir -p output/media/flow output/media/frames output/media/stills
cp <skill dir>/assets/animation/index.html output/media/flow/index.html
python3 -m http.server <port> --bind 127.0.0.1 --directory output/media     # in the background
```

Open the page in its own tab, at the video's size, and ask it whether everything fits. Pass
this to `browser_run_code_unsafe`; it also saves a still every two seconds:

```js
async (page) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto('http://127.0.0.1:<port>/flow/index.html?f=0');
  const info = await page.evaluate(() => window.ready);
  for (let n = 0, t = 1; t < info.seconds; n++, t += 2) {
    await page.evaluate(t => window.renderAt(t), t);
    await page.screenshot({ path: '<absolute path>/output/media/stills/s' + String(n).padStart(2, '0') + '.png', scale: 'css' });
  }
  return info;
}
```

`info.warnings` lists every text that does not fit its place. Shorten that text in the plan
and run it again until the list is empty. If the call fails, the page says why in red at its
top left (a missing capture, a plan that is not valid JSON).

Then tile the stills and Read every sheet:

```
ffmpeg -v error -y -i output/media/stills/s%02d.png -vf "scale=640:-1,tile=3x4" output/media/stills/sheet%d.png
```

Check, in this order:

- The first still shows the hook's first line. A feed uses the first frame as the thumbnail.
- Each chapter's still shows the thing its caption names, and each ring sits on the thing it
  is meant to point at. A ring that is off is a wrong `box`; measure again.
- Text inside a capture that the caption depends on can be read on the sheet. If it cannot,
  add a `focus` (window) or retake the capture closer.
- The stats match the run, and the highlighted one is the design detail.
- The end card shows the day, the hashtag and the question.
- Nothing from the never-show list is in any still.

Change the plan, never the page: the copy in `output/media/flow/` stays identical to the
template. If a product needs something the plan cannot say, tell the user what is missing
(that is a change to the skill, not to this video) and make the video with what the plan can
say, or choose screenshots at stage 12.

## Pass 4: compose, render, assemble, scan

The scripts are in the skill's `scripts/` directory and are run from the repository root.
They need `ffmpeg`, `ffprobe`, `tesseract`, and Python 3 with `numpy` (the music only).

**Compose the music.** The track follows the plan's beats: a riser under the hook, a drop on
the title's first frame, the groove under the chapters, a break under the stats card, a second
drop on the chapter after it, a tail that fades with the end card. Every note is synthesised,
so it is original and safe to post.

```
python3 <skill dir>/scripts/compose.py output/media/plan.json
```

It writes `music.file` and prints the section map. If `numpy` is missing it says so; then
install it, or point `music.file` at a licensed track in `assets/music/`, and say in the
review which happened. Never ship a silent video without telling the user.

**Render the frames.** After any change to the plan or a capture, start again from frame 0.
Pass this to `browser_run_code_unsafe` with `from` set to 0; it draws frames for forty seconds
and returns where it stopped. Call it again with `from` set to the `next` it returned, until
`done` is true. About ten frames a second: three or four calls for a forty-second video.

```js
async (page) => {
  let from = 0;
  await page.setViewportSize({ width: 1920, height: 1080 });
  if (from === 0) await page.goto('http://127.0.0.1:<port>/flow/index.html?f=0');
  const info = await page.evaluate(() => window.ready);
  if (info.warnings.length) return info;
  const started = Date.now();
  while (from < info.frames && Date.now() - started < 40000) {
    await page.evaluate(f => window.renderFrame(f), from);
    await page.screenshot({ path: '<absolute path>/output/media/frames/f' + String(from).padStart(5, '0') + '.png', scale: 'css' });
    from++;
  }
  return { next: from, of: info.frames, done: from >= info.frames };
}
```

**Assemble.**

```
python3 <skill dir>/scripts/assemble.py output/media/plan.json
```

It checks that every frame is there and is the plan's size, then writes `output/media/demo.mp4`
with the music cut to length and faded out. If it refuses, it says which frame or which part
of the plan is wrong; fix that and run it again. Do not join the frames by hand.

**Scan the finished file.** The file is what ships, so scan it, not the stills:

```
python3 <skill dir>/scripts/redact.py --input output/media/demo.mp4 --start 0 --end <seconds> \
        --fps 5 --user $(whoami) --out output/media/leftover.json
```

Only a scan that reports `0 boxes` clears the video for stage 11. A hit means a still shows
something from the never-show list. Find it (the scan gives the time and the place), then
retake that capture, delete that line of output, or change the sample data; render, assemble
and scan again. If the only hits are the product's own made-up sample data and the chapter
is about that data (an invented address being masked), name each hit to the user and go on
only with their yes.

**Review.** Tile the finished file and Read every sheet against the Pass 3 list:

```
ffmpeg -v error -y -i output/media/demo.mp4 -vf "fps=1/2,scale=640:-1,tile=3x4" output/media/stills/final%d.png
```

Then stop the local server, close the animation's tab, and delete `output/media/frames/` and
`output/media/stills/`. The plan, the captures, the page and `music.mp3` stay in
`output/media/` for the record. LinkedIn gets `demo.mp4` only.
