# Demo video guidelines

Read this before recording. The finished video is an edited piece: a title card, four to six
short scenes that each zoom to the part of the screen that matters, a caption per scene,
music underneath, an end card. Twenty to forty seconds. It should feel like "here is what I
built and how it works", not "here is an agent clicking around" and not a raw screen dump.

The work happens in three passes: record raw footage, write an edit plan, render. Nothing
uploaded to LinkedIn is ever the raw recording.

## Pass 1: record raw footage

### Explore first, record second

Never record the discovery session. Explore the app fully, write the demo plan (stage 6),
then record it once, cleanly. If the take is messy, delete it and record again.

### The demo plan

4–6 steps in this shape, each a specific action on a specific element:

```
1. Start on the strongest screen, content loaded.
2. Perform the core interaction.
3. Show what it produced.
4. Show one more feature that differentiates the project.
5. End on a clean, meaningful result screen. Hold for about two seconds.
```

The plan lines up with the post: what the post calls interesting is what the video shows.

### Pacing while recording

- Show the core value within the first 10 seconds of the finished video.
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
plan, then look closer around each with a denser tile if needed. Pick 4–6 scenes. For each,
decide: source start and end, speed, zoom region, caption.

Rules of thumb:

- A web-app interaction plays at 1×. Zoom to the element that was clicked and its result.
- A terminal scene fast-forwards at 4–8×. Zoom to the terminal window bounds, or tighter to
  the text block that matters. A minute of the agent thinking becomes ten seconds.
- Each scene is 4–10 seconds of output. Total 20–40 seconds plus title and end cards.
- Captions are one short sentence in plain words, the same voice as the post. They are what
  the viewer reads; the screen is texture. ("It reads the repo and writes a brief.")
- Title card: project name and the post's one-line "what it does". End card: Day N/30 and the
  theme hashtag, or the project name again.

Write the plan to `output/media/plan.json`:

```json
{
  "output": "output/media/demo.mp4",
  "size": [1920, 1080],
  "fps": 30,
  "transition": 0.5,
  "title": {"text": "Project Publisher", "sub": "one command from a repo to a LinkedIn draft", "duration": 2.5},
  "end":   {"text": "Day 1/30", "sub": "#buildinpublic", "duration": 2.0},
  "music": {"file": "<skill dir>/assets/music/<track>", "volume_db": -20},
  "segments": [
    {"src": "output/media/raw-screen.mov", "start": 118, "end": 136, "speed": 4,
     "zoom": {"x": 40, "y": 30, "w": 1500, "h": 820, "ease": 1.2},
     "caption": "It reads the repo and writes a brief",
     "blur": "output/media/blur-118-136.json"},
    {"src": "output/media/raw-browser.webm", "start": 3.0, "end": 11.0, "speed": 1,
     "zoom": {"x": 120, "y": 180, "w": 900, "h": 520, "ease": 1.4},
     "caption": "Type a city and the forecast fills in"}
  ]
}
```

Zoom regions are in source pixels and are fitted to the output aspect around their centre;
`ease` is the seconds the zoom takes to settle. Speed above 1.5× shows a small "6x" badge.
Pick the music track from `assets/music/` in the skill directory; if the folder holds only
the README, leave `music` out and tell the user the video is silent.

## Pass 3: redact, render, verify

Three scripts calls, all deterministic, all in the skill's `scripts/` directory. They need
`ffmpeg`, `ffprobe`, and `tesseract` on PATH (`brew install ffmpeg tesseract`).

**Redact every terminal scene.** OCR the source window and produce blur boxes for anything
on the never-show list. Pass the user's login name so it is caught even when OCR misreads it:

```
python3 <skill dir>/scripts/redact.py --input output/media/raw-screen.mov \
        --start 118 --end 136 --user $(whoami) --out output/media/blur-118-136.json
```

It samples four frames per second, so a minute of source takes about a minute on a Mac.
Browser scenes normally need no redaction, but run it if the app shows accounts or data.

**Render.**

```
python3 <skill dir>/scripts/render.py output/media/plan.json
```

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
screen): cut that scene from the plan and re-render rather than blurring half the frame.

## Review the finished video

Tile it and Read every sheet:

```
ffmpeg -v error -y -i output/media/demo.mp4 -vf "fps=1/2,scale=480:-1,tile=3x3" output/media/frames/final%d.png
```

Check: the title card reads cleanly; every scene's zoom lands on the thing the caption
names; text is legible at phone size (if it is not, the zoom region is too large); no scene
is a blur field; transitions are clean; the last frame holds; the badge shows the speed on
fast-forwarded scenes; nothing from the never-show list is readable anywhere. Play the file
once for the music level: audible, never competing with the captions.

Delete `output/media/frames/` after review. Fix the plan and re-render rather than editing
the output; rendering takes under a minute.

The raw recordings (`raw-screen.mov`, `raw-browser.webm`) stay in `output/media/` for the
record but are never uploaded. LinkedIn gets `demo.mp4` only.
