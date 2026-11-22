# Demo video guidelines

Read this before stage 8. The finished video is an animation, not a recording. It has to hold
a stranger for forty seconds in a feed that autoplays muted: a hook line before anything else,
the title landing on the first beat of the music, four or five numbered chapters with the
product on the right and a large caption on the left, a stats card with counting numbers, and
an end card that asks a question. A progress bar runs along the bottom and an original track
is composed to the same beat grid.

The product appears as real stills: captures of its screens shown whole and unchanged, or the
real output of a real run shown as text. Rings point at things. Nothing is redrawn by hand,
nothing is recorded, and nothing is blurred.

One page draws all of it: `assets/animation/index.html`, the template. It reads
`output/media/plan.json` and is a pure function of time, so frame 300 looks the same every
time it is drawn. The same plan drives the music, so picture and track cannot drift apart.

Four passes: capture the stills, write the plan, build it and look at stills, then compose,
render, assemble and scan. Run every command from the repository root; if your shell starts
each command somewhere else, put `cd <repository root> &&` in front. `<skill dir>` is the
skill's own directory, the one this guide's `references/` folder is in.

## Pass 1: capture the stills

A still is the product in one state. Most chapters need two: before and after the thing the
chapter is about. List the states from the demo plan (stage 6) before capturing anything, and
save each to `output/media/flow/assets/NN-slug.png` (or `.txt`), a folder stage 2 made.

| The product is | Capture with | Notes |
|---|---|---|
| A web app | The capture snippet below, at 1200 × 750 | That size keeps the page's text readable in the video; the post's own screenshots stay 1440 × 900 |
| A phone app | The emulator's or simulator's own screenshot of the whole screen (`adb exec-out screencap -p > file.png`) | Never a person's real phone |
| A tool with no screen (command line, library, agent skill) | The real output of a real run, as text: `{ echo '$ <command>'; <command>; } > output/media/flow/assets/NN-slug.txt 2>&1` | Use relative paths in the command, so no home path is printed. Strip colour codes |

For a web app, pass this to `browser_run_code_unsafe` in the tab the app is open in. Keep
`still`, `box` and `text` as they are and put the demo plan's own steps after them:

```js
async (page) => {
  const dir = '<absolute path>/output/media/flow/assets/';
  const still = async name => {            // no caret and no focus ring in the picture
    await page.evaluate(() => document.activeElement && document.activeElement.blur());
    await page.screenshot({ path: dir + name, scale: 'css' });
  };
  const box = async locator => {           // where something is, in the capture's own pixels
    const b = await locator.boundingBox();
    return [b.x, b.y, b.width, b.height].map(Math.round);
  };
  const text = locator => locator.evaluate(e => {   // the words alone, not the block they sit in
    const r = document.createRange(); r.selectNodeContents(e);
    const b = r.getBoundingClientRect(); return [b.x, b.y, b.width, b.height].map(Math.round);
  });
  await page.setViewportSize({ width: 1200, height: 750 });
  await page.goto('http://127.0.0.1:5173/');            // the app's own URL
  await still('01-empty.png');
  await page.getByLabel('Bill amount').fill('84.50');
  await page.getByRole('button', { name: '20%' }).click();
  await still('02-split.png');
  return { amount: await text(page.locator('#each')), tips: await box(page.locator('.tips')) };
}
```

The boxes it returns are what the plan's rings and `focus` use: `box` for a control or a
card, `text` for a figure or a line of words, since a block is as wide as its column. For a
phone app, take the boxes from the `bounds` in a `uiautomator dump`, or read them off the
capture (the Read tool says by how much it scaled the picture down).

Rules for every still:

- It shows the product doing its job with content loaded: no spinner, error, cookie banner
  or tooltip, unless that is the feature. An empty or starting state is fine as the before
  of a pair, never as what a chapter ends on.
- It is used whole. Do not crop, retouch or composite a capture. To draw the eye, add a ring
  in the plan; to bring small text closer on a web capture, add a `focus` in the plan.
- A line of output is never edited. Whole lines may be deleted to shorten it; keep the
  untouched output beside it as `NN-slug.full.txt`.
- Nothing from the never-show list is in it: credentials, tokens, emails, account names,
  private URLs, home-directory paths, notifications, other windows, the agent's own terminal.
  A still that shows one is taken again with the cause removed. There is no blur step.
- Use made-up sample data that cannot be taken for the real thing (a `555` phone number, a
  name with no account behind it).
- If a still shows the product getting something wrong (a total that does not add up), do
  not ring it and do not hide it. Tell the user in one line, as stage 6 says; whether to fix
  it before posting is theirs to decide.

## Pass 2: write the plan

### The spine

The video has the same spine as the post. Every part is an entry in the plan, and every entry
states its length in beats:

```
hook     8-10 beats  the spark as one or two big lines, and what you built as a smaller line
title    6-8         project name; the lines under it are the story's "you give it X, it gives you Y"
01..05   10-14 each  four or five chapters, one idea each: the demo plan's steps in order
stats    8-10        real numbers from the run, the design detail as the highlighted one
end      8-12        Day N/30, the series hashtag, and the closing question
```

With no spark from stage 1, the hook's lines are the problem the project solves, as stage 4
puts it. The sum (beats × 60 ÷ bpm) must come to between 34 and 42 seconds: 68 to 84 beats
at 120 bpm, 71 to 86 at 124 or 125, 80 to 98 at 140. Start near the lower ends at 120 to
125 bpm and near the upper ends at 140 with four chapters (the title takes 8 there; five chapters at
140 fit only at 10 or 11 beats each), then add or take beats in the chapters until the sum
lands.

Put the stats card after the third or fourth chapter, never last: the music breaks there and
drops again on the chapter that follows, so the strongest chapter goes after it. Fewer than
four chapters means the demo plan was too thin. A step that only sets the scene (the empty
page) is the before-still of the first chapter, not a chapter of its own.

The words come from stage 4's story lines, the same lines the post is written from at
stage 9, so video and post say the same thing in the same voice.

### Chapters

Each chapter is one thing the product does. Its fields:

- `type`: `chapter`. The stats card is the one entry whose `type` is `stats`.
- `chapter`: one or two words, shown very large: Search, Score, Kind words.
- `group`: a short label over the number, shared by chapters that belong together.
- `head`: one sentence of up to about 45 characters saying what the product does here.
  `sub`: one more sentence, smaller.
- `chips`: optional. The named parts of the product at work in this chapter (a model, a
  library, a file). Leave it out rather than repeat the chapter's name.
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

Every time is in beats from the start of the chapter: a shot's `at`, and a ring's `at` and
`until`. A ring is `{at, until, box}`, where `box` is `[x, y, width, height]` in the capture's
own pixels; leave `until` out and the ring stays while its shot does. Give each still two
beats or more before the next thing happens, keep each ring up for three beats or more, and
end each chapter on the result.

`focus` is a box of the same kind, on any `window` shot: the card then shows that part of
the capture instead of the whole. Give it the capture's own shape (for 1200 × 750, 1.6 times
as wide as it is tall), make it 800 wide or more, and keep it inside the capture. A box of
another shape shows what is beside it, a narrower one is enlarged past its real size and goes
soft, and one that runs past the edge shows a strip of bare card; the page warns of all
three.

### Stats card

Up to four figures from the actual run, each with a short label: what the product printed or
wrote, or what you measured in this run. Never estimates; say where each came from when you
show the plan. A whole number written in digits alone (1200, not 1,200) counts up, with or without a unit
after it (`"20 %"`); the unit is drawn small beside it. A figure with a decimal point is written as text and shown as it
is: `"33.80"`, `"1.7 GB"`. All the figures are drawn at one size, so one long figure makes
every figure smaller: prefer short ones. Make one of them the design detail whenever it is a
number ("0 auto-submitted", "0 bytes sent") and set `highlight` to its position, from 0.
`label` is the card's own heading, a few words. `note` is one sentence of the story; put `**`
around the part to stress.

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
2. Otherwise find the last two video posts: the records in `~/.project-publisher/posts/` whose
   `medium:` is `video`, the last two in file-name order (the names start with the date). The
   first word of each one's `theme:` line is its theme. Do not use either.
3. From what is left, drop the themes the captures would not stand out against: `daylight`
   when the product's own screens are light, the three dark themes when they are dark. A
   product with no screen drops nothing. If that drops everything, keep what step 2 left.
4. If more than one is still left, take the first in the table among those never used in the
   log; failing that, the one used longest ago.

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
        "rings": [{"at": 1.6, "until": 5.4, "box": [85, 1790, 1275, 200]}]},
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
          "note": "Small models on the phone, no cloud AI.", "beats": 10}
}
```

A `window` chapter and a `terminal` chapter, in the same place:

```json
{"type": "chapter", "chapter": "Split", "group": "The answer", "beats": 12,
 "head": "It shows what each person pays.", "sub": "And the same amount rounded up, for cash.",
 "stage": "window",
 "shots": [
   {"src": "assets/02-split.png", "at": 0},
   {"src": "assets/02-split.png", "at": 3, "focus": [400, 125, 800, 500],
    "rings": [{"at": 6, "box": [648, 215, 179, 93]}]}
 ]},
{"type": "chapter", "chapter": "Check", "group": "From the command line", "beats": 12,
 "head": "One command checks a template.", "sub": "It names the line that is wrong.",
 "chips": ["Python"], "stage": "terminal", "src": "assets/05-check.txt", "mark": [3]}
```

The rest of the fields:

- `src` paths are relative to `output/media/flow/`. `output` and `music.file` are relative to
  the repository root.
- `size` is always `[1920, 1080]` and `fps` 30: the page draws at that size whatever the plan
  says, and `assemble.py` checks the frames against the plan.
- `brand.name` is shown small at the top of every chapter and on the end card. `badge` is
  one more chip shown in every chapter, for the thing true of all of them; leave it out if
  there is none.
- The title card shows the day tag, the hashtag and the chapter names by itself.
- `brand.day` and `end.text` are left out when no challenge day was given. `end.sub` is the
  series hashtag, the one every post of the challenge carries (`#BuildInPublic`); leave it
  out if there is none. `end.question` is the closing question and is left out when the user gave
  none; the end card then shows the project name large. `end.accent` is the part of the
  question drawn in the accent colours; `title.accent` does the same for the name (by
  default its last word). `end.note` is one line under the question. `end.chips` is an
  optional short row under that (the product's parts, say); most plans leave it out.
- `\n` breaks the line in the hook's `sub` and the end card's `note`. A title's `sub` is a
  list, one line per entry; a chapter's `sub` wraps on its own.
- `music.seed` is any whole number and keeps the same track on a re-run: use the day number,
  or 1. A licensed track from `<skill dir>/assets/music/` can be used by pointing `music.file`
  at it with an absolute path (the skill's folder, not the repository's); then the beats will
  not match it.

Show the plan to the user in a few lines: the theme, the hook, the chapter names with their
`head` lines, the stats and where each came from, the question.

## Pass 3: build it and look at stills

```
mkdir -p output/media/flow/assets output/media/frames output/media/stills
cp <skill dir>/assets/animation/index.html output/media/flow/index.html
python3 -m http.server 8765 --bind 127.0.0.1 --directory "$PWD/output/media"     # in the background
```

Use another port if 8765 is taken, and change it in the two snippets and the kill command
below too. Open a new tab for the animation with `browser_tabs` (action `new`); it becomes the
current tab, so the two snippets below run in it and the app's own tab is left alone.

Before each run of the next snippet, `rm -f output/media/stills/s*.png`, so no still of an
earlier plan is tiled with the new ones. Then pass this to `browser_run_code_unsafe`. It asks
the page whether everything fits, and saves a still at each moment the page says is worth one: the first frame, every still once it has
settled, every ring while it is up, and the end of every scene.

```js
async (page) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto('http://127.0.0.1:8765/flow/index.html?f=0&v=' + Date.now());
  const info = await page.evaluate(() => window.ready);
  for (let n = 0; n < info.moments.length; n++) {
    await page.evaluate(t => window.renderAt(t), info.moments[n]);
    await page.screenshot({ path: '<absolute path>/output/media/stills/s' + String(n).padStart(2, '0') + '.png', scale: 'css' });
  }
  return info;
}
```

`info.warnings` lists every text that does not fit its place and every `focus` of the wrong
shape, size or place, each with what to change. Change the plan and run the snippet again until the
list is empty. If the call fails, the page says why in red at its top left (a missing
capture, a plan that is not valid JSON).

Then tile the stills and Read every sheet:

```
rm -rf output/media/stills/sheets && mkdir output/media/stills/sheets
ffmpeg -v error -y -i output/media/stills/s%02d.png -vf "scale=640:-1,tile=3x4" output/media/stills/sheets/sheet%d.png
```

Check, in this order:

- The first still shows the hook's first line. A feed uses the first frame as the thumbnail.
- Each chapter's stills show the thing its caption names, and each ring sits on the thing it
  is meant to point at. A ring that is off is a wrong `box`; measure again.
- Text inside a capture that the caption depends on can be read on the sheet. If it cannot,
  add a `focus` (window) or retake the capture closer.
- No `head` leaves one short word alone on its last line; reword it if it does.
- The stats match the run, and the highlighted one is the design detail.
- The end card shows the day, the hashtag and the question.
- Nothing from the never-show list is in any still.

Change the plan, never the page: the copy in `output/media/flow/` stays identical to the
template. If a product needs something the plan cannot say, tell the user what is missing
(that is a change to the skill, not to this video) and make the video with what the plan can
say, or choose screenshots at stage 12.

## Pass 4: compose, render, assemble, scan

The scripts are in the skill's `scripts/` directory. They need `ffmpeg`, `ffprobe`,
`tesseract`, and Python 3 with `numpy` (the music only).

**Compose the music.** The track follows the plan's beats: a riser under the hook, a drop on
the title's first frame, the groove under the chapters, a break under the stats card, a second
drop on the chapter after it, a tail that fades with the end card. Every note is synthesised,
so it is original and safe to post.

```
python3 <skill dir>/scripts/compose.py output/media/plan.json
```

It writes `music.file` and prints the section map. Skip this step when `music.file` points at
a licensed track: compose.py writes to `music.file`. If `numpy` is missing it says so; then do
what stage 2 decided: point `music.file` at a licensed track in `<skill dir>/assets/music/` by
its absolute path, or go on without music, and say in the review which happened. Never ship
a silent video without telling the user.

**Render the frames.** After any change to the plan or a capture, empty `output/media/frames/`
and start again from frame 0. Pass this to `browser_run_code_unsafe` in the animation's tab as
it is, with `let from = 0;`; it draws frames for forty seconds and returns where it stopped.
Call it again with that 0 changed to the `next` it returned, until `done` is true. About ten frames a second: three or four calls for
a forty-second video.

```js
async (page) => {
  let from = 0;
  await page.setViewportSize({ width: 1920, height: 1080 });
  if (from === 0) await page.goto('http://127.0.0.1:8765/flow/index.html?f=0&v=' + Date.now());
  const info = await page.evaluate(() => window.ready);
  if (info.warnings.length) return info;
  const started = Date.now();
  while (from < info.frames && Date.now() - started < 40000) {
    await page.evaluate(f => window.renderFrame(f), from);
    await page.screenshot({ path: '<absolute path>/output/media/frames/f' + String(from).padStart(5, '0') + '.png', scale: 'css' });
    from++;
  }
  return { next: from, of: info.frames, seconds: info.seconds, done: from >= info.frames };
}
```

**Assemble.**

```
python3 <skill dir>/scripts/assemble.py output/media/plan.json
```

It checks that every frame is there and is the plan's size, then writes `output/media/demo.mp4`
with the music cut to length and faded out. If it refuses, it says which frame or which part
of the plan is wrong; fix that and run it again. Do not join the frames by hand.

**Scan the finished file.** The file is what ships, so scan it, not the stills. `<seconds>`
is the length the page and `assemble.py` reported:

```
python3 <skill dir>/scripts/redact.py --input output/media/demo.mp4 --start 0 --end <seconds> \
        --fps 5 --user $(whoami) --out output/media/leftover.json
```

Only a scan that reports `0 boxes` clears the video for stage 11. A hit means a still shows
something from the never-show list. Find it (the scan gives the time and the place), then
retake that capture, delete that line of output, or change the sample data; run the stills
snippet again (Pass 3), then render, assemble and scan again. If the only hits are the product's own made-up sample data and the chapter
is about that data (an invented address being masked), name each hit to the user and go on
only with their yes.

**Review.** Tile the finished file, a frame a second, and Read every sheet against the
Pass 3 list:

```
rm -rf output/media/stills/final && mkdir output/media/stills/final
ffmpeg -v error -y -i output/media/demo.mp4 -vf "fps=1,scale=640:-1,tile=3x4" output/media/stills/final/sheet%d.png
```

For a product with no screen, copy now the stills that become its screenshots to
`output/media/screenshots/`: a terminal chapter's still is the one taken at its end, its only
moment (the screenshot guide says what makes a good one). Then stop the local server
(`lsof -ti tcp:8765 | xargs kill`; the harness may report that background task as failed,
which is the kill), close the animation's tab (`browser_tabs`, action `close`), and delete
`output/media/frames/` and `output/media/stills/`. The plan, the captures, the page,
`music.mp3` and `leftover.json` stay in `output/media/` for the record. LinkedIn gets
`demo.mp4` only.
