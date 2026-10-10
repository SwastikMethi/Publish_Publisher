# Demo video guidelines

Read this before recording. The finished video is a designed piece that has to hold a
stranger for forty seconds in a feed that autoplays muted: a hook line before anything else,
the title landing on the first beat of the music, four or five numbered chapters where the
footage sits in a card beside a large caption, a stats card with counting numbers, and an end
card that asks a question. Every cut lands on a beat, a progress bar runs along the bottom, and
an original track is composed to the same beat grid. Thirty-five to forty seconds. It should
feel like a launch video, not "here is an agent clicking around" and not a raw screen dump.

The work happens in four passes: record raw footage, write an edit plan, compose the music,
render. Nothing uploaded to LinkedIn is ever the raw recording.

## Pass 1: record raw footage

### Explore first, record second

Never record the discovery session. Explore the app fully, write the demo plan (stage 6),
then record it once, cleanly. If the take is messy, delete it and record again.

### The demo plan

4–5 steps in this shape, each a specific action on a specific element. Each step becomes a
chapter of the finished video with a one-word name, so think in verbs:

```
1. Start on the strongest screen, content loaded.
2. Perform the core interaction.
3. Show what it produced.
4. Show one more feature that differentiates the project.
5. End on a clean, meaningful result screen. Hold for about two seconds.
```

The plan lines up with the post: what the post calls interesting is what the video shows,
and the last step is the design detail or the refusal, which is where the video ends.

### Pacing while recording

- The hook and title take the first six seconds; the first chapter must show the core value
  by second ten, so the first recorded moment has to be the product doing its job.
- Pause about one second after each meaningful change. Use `browser_wait_for` with a time or
  a text match, not a sleep in Bash.
- No repeated actions, no back-and-forth navigation, no scrolling unless the content below
  the fold is the point.
- Slow steps (a build, a long fetch) are fine in the raw footage; the edit fast-forwards them.

### Never show

Unless it is genuinely the product being demonstrated:

- the Claude Code terminal or any terminal
- Playwright inspector, debug UI, dev tools, console
- setup commands, install output, build logs
- login pages, credentials, API keys, tokens
- internal or private URLs, hostnames, emails, account names, home-directory paths
- notifications, OS popups, other windows
- error states, failed requests, loading failures

For web apps this list is enforced by re-recording. For terminal and agent products the
terminal *is* the product and will print paths and names you cannot suppress; there the list
is enforced by the redaction pass in Pass 3. Either way, nothing on this list reaches LinkedIn.

### Web apps: record the browser with Playwright MCP

The Playwright MCP server records natively when started with `--caps=devtools`. Drive the demo
as one Playwright snippet passed inline to `browser_run_code_unsafe`, so pacing is controlled
by the snippet and not by tool round trips. The snippet is typed into the tool call, never
saved to the skill or the project.

```
browser_resize            1440 × 900
browser_snapshot          once, to learn roles, names, and text of every target element
<write the snippet from the plan>
browser_run_code_unsafe   DRY RUN, not recorded; fix any selector that fails
browser_navigate          back to the start URL, so the first frame is the clean start state
browser_wait_for          the start screen's real content, not its heading
browser_start_video       filename: output/media/raw-browser.webm, size: { width: 1440, height: 900 }
browser_run_code_unsafe   the same snippet, unchanged
browser_stop_video
```

The snippet is one async function of `page`. Use role and text locators, a pause of about
1000–1500 ms after each visible change, and a 2000 ms hold at the end. After any navigation or
fetch, wait for the content that proves it finished, not the page heading.

**Log the zoom targets while you record.** Before each click or fill, get the element's
bounding box and print it with a timestamp; the edit plan uses these as zoom regions:

```js
async (page) => {
  const t0 = Date.now();
  const mark = async (loc, label) => {
    const b = await loc.boundingBox();
    console.log(JSON.stringify({ t: (Date.now() - t0) / 1000, label, ...b }));
  };
  const city = page.getByRole('textbox', { name: /city/i });
  await mark(city, 'search');
  await city.fill('Berlin');
  await page.keyboard.press('Enter');
  await page.waitForSelector('text=Berlin, Germany');
  await page.waitForTimeout(1500);
  const card = page.getByText('Berlin, Germany').locator('..');
  await mark(card, 'result');
  await page.waitForTimeout(1500);
  await page.getByRole('link', { name: 'Forecast' }).click();
  await page.waitForTimeout(2000);
}
```

Read the logged lines back with `browser_console_messages` and keep them for the plan. The
recording starts a few seconds before the snippet's first line runs, so the snippet must not
open with a wait; add the offset you observe to the logged times when you build the plan.

Notes: always pass `filename` and `size` to `browser_start_video` (without `size` it records
at 800 × 600). The dry run is mandatory. Nothing happens between `browser_start_video` and
`browser_run_code_unsafe` except the call itself. `browser_start_recording` records actions
as code, not pixels; do not use it.

### Terminal, CLI, and agent products: record the whole screen

When the project has no web UI, the terminal is the product. Playwright is not involved; use
the macOS built-ins. This needs Screen Recording permission for the app running Claude Code.
Check first, and if it fails, stop and tell the user which app to allow under System Settings
› Privacy & Security › Screen Recording:

```
screencapture -x /tmp/pp-check.png && rm /tmp/pp-check.png
```

**Record the entire main display, not a rectangle.** A rectangle cuts off whatever opens
next to it (a browser window, a dialog), and the edit needs the whole screen to zoom into.

```
osascript -e 'tell application "System Events" to set frontmost of process "Terminal" to true'
screencapture -x -v -V <seconds> output/media/raw-screen.mov
```

Before starting: hide the Dock, turn on Do Not Disturb, close every window that is not part
of the demo, and set a plain prompt so the shell does not print `user@hostname`:

```
osascript -e 'tell application "Terminal"
  set w to do script "cd <repo> && export PS1=\"$ \" && clear && <command>"
  delay 0.5
  set b to bounds of front window
  return (id of front window as text) & "|" & (item 1 of b) & "," & (item 2 of b) & "," & ((item 3 of b) - (item 1 of b)) & "," & ((item 4 of b) - (item 2 of b))
end tell'
```

The returned bounds are the zoom target for terminal scenes. If a browser window is part of
the demo, get its bounds the same way through System Events and use them for browser scenes.
Bounds are in screen points; the recording is in pixels. On a Retina display multiply by 2
(check: `ffprobe` width divided by the display's point width).

**Short deterministic commands** (help text, a validator, a scoring command) are screenshots,
not video.

**A long agent run the user drives.** Give the user the exact command, ask them to run it in
the demo window, and record the whole run with `-V` set generously. The edit picks moments
from it; do not compress the whole run into a timelapse.

**Never run an agent product's own flow yourself** to make a video.

Close the demo window afterwards with `tell application "Terminal" to close window id <id>`.

## Pass 2: write the edit plan

Review the raw footage first. Tile it into contact sheets and Read them:

```
mkdir -p output/media/frames
ffmpeg -v error -y -i output/media/raw-screen.mov -vf "fps=1/5,scale=480:-1,tile=4x3" output/media/frames/raw%d.png
```

For a 20-minute recording that is 20 sheets; skim them for the moments that match the demo
plan, then look closer around each with a denser tile if needed. Then open one full-resolution
frame from each candidate moment (`ffmpeg -ss <t> -i raw.mov -frames:v 1 frame.png`) and Read
it: crop regions are chosen from real pixels, never guessed.

### The spine

The video has the same spine as the post, in this order. Every part is a plan entry. The
beat counts below are the cards format's (`volt`); the other themes stage the same entries in
their own format and length (see Theme below):

```
hook     6 beats   the spark as one or two big lines, the "what I built" as a smaller sub-line
title    6 beats   project name; sub-line is the post's "you give it X, it gives you Y"
01..05   10-12     four or five chapters, one verb each: the demo plan's steps in order
stats    8 beats   real numbers from the run, the design detail as the highlighted one
end      8 beats   Day N/30, the theme hashtag, and the post's closing question
```

Put the stats card after the third or fourth chapter, never last: the music breaks there and
drops again on the chapter that follows, so the strongest chapter (usually the result) goes
after it. Total 76-84 beats; at the theme's bpm that is 33-42 seconds. Fewer than four
chapters means the demo plan was too thin; go back to the footage.

### Beats, not seconds

The bpm comes from the theme (see Theme below). Every scene's length is a beat count;
footage scenes run about 4.3-6 s across the themes' tempos. The speed of a footage
scene is not chosen, it is derived: the source window divided by the scene length. So pick
windows that give 4-8x for terminal work and about 1x for browser interaction, and adjust the
window, not the speed. A window shorter than the scene plays at 1x and holds its last frame.

### Chapters

Each chapter is one verb of the product: Search, Capture, Score, Tailor, Approve. Reads,
Starts, Clicks, Writes, Loads. The chapter word is drawn in small caps under a big number, so
keep it to one word.

Captions are three or four short lines, 18 characters or fewer each, in the post's voice, and
they carry the meaning; the footage is texture. Say what the product does, not what is on the
screen: "Scores each job / against what the / resume actually / proves", not "Analysis JSON
written". No identifiers, no file names, no architecture nouns. The last chapter's caption is
the design detail or the refusal: the thing the post is about.

Two layouts, used by the cards format only:

- `side` (default): a 1180x780 card on the right, caption on the left. For any region that
  is roughly 3:2 or taller: a browser page, a JSON block, a column of terminal output.
- `wide`: a 1680x720 card across the top, one or two caption lines under it, the second in
  the accent colour. For terminal output that spans the whole screen width, like a final
  summary. Use it once, for the last chapter, if at all.

### Crop regions

The crop is in source pixels and is fitted to the card's aspect around its centre, so give
the region you want to see and let the fit widen it. Choose it from the full-resolution frame
so that every one of these is outside the region:

- the terminal window's title bar (it prints `user — app — command`)
- the browser's tab strip, address bar, and any warning banner under it
- the agent's own footer: status line, "Tip:" lines, token counts
- the macOS menu bar and Dock
- any redaction blur that would cover more than a corner of the card

Then check the text that remains is legible when the card is 1180 px wide: for a 3456-wide
Retina recording that means a region no wider than about 1900 px for terminal text and about
1500 px for a browser page. If the important text is smaller than that, the region is too
large; cut it in half and pick the half the caption is about.

A region that cannot be made clean this way (a wall of paths, a blurred command line) is not
a chapter. Pick another moment.

### Stats card

Four numbers from the actual run, each with a two- or three-word label, taken from the
tracker, the summary the agent printed, the output folder. Never estimates. Make the fourth
the design detail whenever one is a number ("0 auto-submitted", "1 file changed", "0
retries") and set `highlight` to its index so it draws in the accent colour. The optional
`note` under the numbers is one sentence from the post.

### Theme

A theme is a whole format, not a skin: how the plan's content is staged, in what order, with
which transitions and pacing, in which look, over which track. Every track is energetic. The
same video on every post reads as a template in the feed, so themes rotate.

| `theme` | format | look and cuts | `music.mood` | `bpm` |
|---|---|---|---|---|
| `volt` | cards: hook card, title, numbered chapters with the footage in a card beside a big caption, stats, end card | black and electric lime, centred Impact capitals that snap in, hard cuts with a white flash | `trap`, half-time | 140 |
| `paper` | magazine: a cover (hook as the standfirst, title as the headline), one page per chapter with the footage as a photo on alternating sides, an "at a glance" box, the question as a pull-quote | cream paper, heavy black type and serif body, red accent, pages push in from the right with a page-flip sound | `indie` (strummed acoustic guitar, stomps, claps, glockenspiel) | 124 |
| `console` | terminal session: the hook typed at a prompt, the name boxed, each chapter as a checklist of steps beside a window of footage with the caption typed as a comment, the stats typed as a readout, the question as a `[y/n]` prompt | green phosphor on black, scanlines, Menlo, pixelated cuts | `chiptune` | 144 |
| `keynote` | launch keynote: the hook centred a line per beat, "Introducing" and the name, then per chapter the verb alone and huge followed by the footage on a laptop with a slow push-in, the numbers in a grid, the question | light studio grey, Avenir, a blue accent, crossfades | `marimba` pop | 112 |

`midnight` (the original navy cards look, `energetic`, 125 bpm) still renders old plans and any
plan without a theme, but it is out of the rotation.

Pick it like this:

1. If the user named a theme, use it.
2. Otherwise read `theme:` from the last two video posts in `~/.project-publisher/posts/`; a
   record without the line was `midnight`. Do not use either of those.
3. From what is left, pick the one that fits the project: `console` for developer, terminal,
   and agent tools; `keynote` for products with a polished UI; `paper` for writing, reading,
   and everyday tools; `volt` for bold automation and anything fast.

Write `"theme"`, its `bpm`, and its `music.mood` into the plan, and name the theme in the plan
summary you show the user. The content is the same for every theme (hook, title, chapters
with footage windows and captions, stats, end question), so the plan does not change shape
with the theme. What changes:

- Only `volt` (the cards format) reads `beats` and `layout` from the plan. The other formats
  own their pacing: paper 12-beat pages, console 14-beat chapters, keynote a 2-beat verb plus
  a 10-beat laptop shot per chapter. Pick footage windows for about those lengths.
- Captions are re-wrapped by the format, so write them as one short sentence in three or four
  lines; they become body copy in `paper`, a typed comment in `console`, and one centred line
  in `keynote`.
- The keynote push-in zooms inside the crop region, never outside it, so the crop rules below
  still decide what can be seen.

The plan may still override single colours: `"theme": {"name": "paper", "accent": "0x0057FF"}`.

The track is composed to the plan in Pass 3, so the plan only names the mood and, optionally,
a `seed` so a re-render keeps the same track. A licensed track in `assets/music/` can be used
instead by pointing `music.file` at it; then the beat grid will not match it. The `calm` lo-fi
mood still exists for a user who asks for it, but no theme uses it.

### The plan file

Write `output/media/plan.json`:

```json
{
  "output": "output/media/demo.mp4",
  "size": [1920, 1080], "fps": 30,
  "theme": "volt", "bpm": 140,
  "brand": {"name": "AI Job Orient", "day": "Day 2/30"},
  "music": {"file": "output/media/music.mp3", "mood": "trap"},
  "hook":  {"lines": ["Applying to jobs", "is a full-time job."],
            "sub": "So I built one that does it. And asks before every submit.", "beats": 6},
  "title": {"text": "AI Job Orient",
            "sub": ["Finds the jobs, scores them, tailors your resume,",
                    "and waits for your yes before anything is submitted."], "beats": 6},
  "scenes": [
    {"type": "footage", "layout": "side", "chapter": "Search",
     "src": "output/media/raw-screen.mov", "start": 118.0, "end": 141.0,
     "crop": {"x": 1480, "y": 300, "w": 1900, "h": 1260},
     "caption": ["Searches LinkedIn", "and Naukri, logs", "every posting"],
     "beats": 10, "blur": "output/media/blur-118-141.json"},
    {"type": "footage", "layout": "side", "chapter": "Score", "...": "..."},
    {"type": "stats", "label": "This run, start to finish",
     "items": [[4, "postings found"], [3, "shortlisted"], [1, "below threshold"], [0, "auto-submitted"]],
     "highlight": 3, "note": "Every 'Awaiting approval' status still needs a human yes.", "beats": 8},
    {"type": "footage", "layout": "wide", "chapter": "Approve",
     "src": "output/media/raw-screen.mov", "start": 466.0, "end": 490.0,
     "crop": {"x": 0, "y": 60, "w": 3456, "h": 1480},
     "caption": ["Three tailored packages wait for approval.", "Nothing goes out without my yes."],
     "beats": 10, "blur": "output/media/blur-466-490.json"}
  ],
  "end": {"text": "Day 2/30", "sub": "#buildinpublic",
          "question": "Would you let it press Apply for you?", "beats": 8}
}
```

`brand.day` and `end.text` are omitted when no challenge day was given; the end card then
repeats the project name. `end.question` is the post's closing question, and is left out
when the user did not supply one. `font` overrides the theme's headline typeface. Show the
plan to the user in a few lines: the theme, the hook, the chapter words with their captions,
the four stats, the question.

## Pass 3: compose, redact, render, verify

Four script calls, all deterministic, all in the skill's `scripts/` directory. They need
`ffmpeg` with the `drawtext` filter, `ffprobe`, `tesseract`, and Python 3 with `numpy` (the
music only). On Homebrew: `brew install ffmpeg-full tesseract`, then
`export PATH=/opt/homebrew/opt/ffmpeg-full/bin:$PATH`, and `python3 -m pip install numpy`.
The plain `ffmpeg` formula lacks `drawtext` and every render fails at the hook card.

**Compose the music.** The track follows the plan's beat grid: a filtered intro and riser
under the hook, a drop on the title's first frame, the groove under the chapters, a break with
a riser under the stats card, a second drop on the chapter after it, a tail that fades with
the end card. Everything is synthesised, so it is original and safe to post.

```
python3 <skill dir>/scripts/compose.py output/media/plan.json
```

It writes `music.file` (default `output/media/music.mp3`) and prints the section map. If
`numpy` is missing it says so; then either install it or point `music.file` at a licensed
track from `assets/music/`, and say in the review which one happened. Never render silent
without telling the user.

**Redact every terminal scene.** OCR the source window and produce blur boxes for anything
on the never-show list. Pass the user's login name so it is caught even when OCR misreads it:

```
python3 <skill dir>/scripts/redact.py --input output/media/raw-screen.mov \
        --start 118 --end 141 --user $(whoami) --out output/media/blur-118-141.json
```

It samples four frames per second, so a minute of source takes about a minute on a Mac.
Browser scenes normally need no redaction, but run it if the app shows accounts or data.

**Render.**

```
python3 <skill dir>/scripts/render.py output/media/plan.json
```

It prints one line per scene with its derived speed and blur count, then the total. A total
outside 30-45 s gets a note; fix the beats in the plan.

**Verify the output by OCR, then patch.** The rendered file is what ships, so scan it, not
the sources. Anything found is blurred in place and the scan is repeated until it is clean:

```
python3 <skill dir>/scripts/redact.py --input output/media/demo.mp4 --start 0 --end <duration> \
        --fps 5 --ocr-scale 0.6 --user $(whoami) --out output/media/leftover.json
python3 <skill dir>/scripts/render.py --patch output/media/demo.mp4 output/media/leftover.json output/media/demo-clean.mp4
mv output/media/demo-clean.mp4 output/media/demo.mp4
```

Repeat the scan. Only a scan that reports `0 boxes` clears the video for stage 11. If two
patch rounds do not get there, something in a scene is wrong (a wall of paths, a credentials
screen): change that chapter's crop or moment in the plan and re-render rather than blurring
half the card.

## Review the finished video

Tile it and Read every sheet:

```
ffmpeg -v error -y -i output/media/demo.mp4 -vf "fps=1/2,scale=480:-1,tile=3x3" output/media/frames/final%d.png
```

Check, in this order:

- The theme is not one used by either of the last two video posts.
- The hook reads in one glance and the title lands on the drop (frame at the title's first
  beat shows the name already large, the accent bar sweeping).
- Every chapter's card shows the thing its caption names, and the text inside the card is
  legible on the 480-px tile; if it is not, the crop is too large.
- Nothing inside any card is from the never-show list: no title bar, no address bar, no
  footer, no username, no blur covering more than a corner.
- The stats card's numbers match the run; the highlighted one is the design detail.
- The end card shows the day, the hashtag, and the question.
- The progress bar is visible along the bottom and (cards format) the small brand footer only during the
  chapters.
- The speed badge shows on fast-forwarded chapters and not on 1x ones.

Play the file once: the drop lands on the title, the break lands on the stats card, the
music is the only audio and sits at a normal level (it is normalised to -14 LUFS). Delete
`output/media/frames/` after review. Fix the plan and re-render rather than editing the
output; a render takes about a minute.

The raw recordings (`raw-screen.mov`, `raw-browser.webm`) and `music.mp3` stay in
`output/media/` for the record but are never uploaded. LinkedIn gets `demo.mp4` only.
