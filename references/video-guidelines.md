# Demo video guidelines

Read this before recording. The video should feel like "here is what I built and how it works",
not "here is an agent clicking around a website".

## Explore first, record second

Never record the discovery session. Explore the app fully, then write a demo plan, then record
the plan once, cleanly. If the recording is messy, delete it and record again. Do not try to
edit or redact a bad take.

## The demo plan

Before pressing record, write down 4–6 steps in this shape:

```
1. Start on the strongest screen, content loaded.
2. Perform the core interaction.
3. Show what it produced.
4. Show one more feature that differentiates the project.
5. End on a clean, meaningful result screen. Hold for about two seconds.
```

Every step must be a specific action on a specific element, not "explore the settings".
The plan should line up with the post: what the post calls interesting is what the video shows.

## Length and pacing

- Target 15–45 seconds. Shorter is better. Go longer only when the product needs the context.
- Show the core value within the first 10 seconds.
- Pause about one second after each meaningful change so a viewer can read the result.
  Use `browser_wait_for` with a time or a text match, not a sleep in Bash.
- No dead time. If something takes more than three seconds to load, either prepare it before
  recording or cut the wait by starting the recording after the slow step.
- No scrolling unless the content below the fold is the point. Then scroll once, smoothly.
- No repeated actions. Clicking the same button twice reads as a bug.
- No back-and-forth navigation. Plan the route so each screen is visited once.

## Never show

Unless it is genuinely the product being demonstrated:

- the Claude Code terminal or any terminal
- Playwright inspector, debug UI, dev tools, console
- setup commands, install output, build logs
- login pages, credentials, API keys, tokens
- localhost URLs with unusual ports if a cleaner view is available (viewport capture hides the address bar; prefer that)
- internal or private URLs, hostnames, emails, account names
- notifications, OS popups, other windows
- error states, failed requests, loading failures

If any of these appear in the recording, re-record. Do not upload it.

## Recording with Playwright MCP

The Playwright MCP server exposes native recording when started with `--caps=devtools`.

```
browser_resize            1440 × 900 (or the same viewport used for screenshots)
<put the app in its clean start state, first frame ready>
browser_snapshot          once, to collect the element refs for every step of the plan
browser_start_video       filename: output/media/demo.webm, size: { width: 1440, height: 900 }
<execute the demo plan, step by step, back to back>
browser_stop_video
```

Notes:

- `browser_start_video` accepts a `filename`; relative paths resolve against the workspace
  root. Always pass it so the file lands in `output/media/`.
- Always pass `size`. Without it the recording is 800 × 600 no matter what the viewport is,
  and the page is scaled down.
- The recording runs on wall-clock time. Every second you spend reasoning between tool calls
  is dead time in the video. Decide every selector and ref from the snapshot before
  `browser_start_video`, then issue the plan's calls one after another with no re-snapshotting
  and no deliberation. A 6-step plan should be 6 to 12 tool calls total.
- If a click fails during recording, stop, delete the file, fix the selector, and record again.
  Do not retry inside the recording.
- Keep the app in its clean start state before starting, so the first frame is already good.
- `browser_start_recording` is a different tool that records actions as code, not pixels.
  Do not use it for the demo.
- Output is WebM. LinkedIn accepts it. Convert with the installed `ffmpeg` only if LinkedIn
  rejects the upload:
  `ffmpeg -i output/media/demo.webm -c:v libx264 -pix_fmt yuv420p output/media/demo.mp4`

## Annotations

Default to none. A polished product demo is a clean interface.

- `browser_video_show_actions` adds a callout and an animated pointer to each action. Use it
  with `cursor: "pointer"` only when the viewer would otherwise not see where the click
  happened, for example on a dense dashboard. Turn it off with `browser_video_hide_actions`
  before the final result screen so the ending is clean.
- `browser_video_chapter` shows a full-screen title card. Use at most two or three, only when the
  demo has distinct phases that a viewer needs named. Titles of four words or fewer, for example
  "Upload a repo", "Generated architecture", "Results". No descriptions unless essential.
- Do not add both callouts and chapters to a short demo. It starts to look like a test recording.

## Terminal and CLI products

When the project has no web UI, the terminal is the product. Record it with the macOS built-in
recorder from a second shell, not with Playwright:

```
screencapture -v -V 40 output/media/demo.mov     # records the screen for 40 seconds
```

Or use `screencapture -v -i -V 40` to select a region, so only the terminal window is captured.
Before recording: clear the terminal, enlarge the font, hide the dock, close notifications,
and make sure no other window shows private information. The same pacing and never-show rules
apply. Convert with `ffmpeg` to WebM or MP4 only if LinkedIn rejects the `.mov`.

## Review the recording

After stopping, watch the whole file, not a sample of it. Open it with `open output/media/demo.webm`
and watch it through, or if a player is not available, extract frames with the installed ffmpeg
(`ffmpeg -i output/media/demo.webm -vf fps=1 output/media/frames/%03d.png`) and Read each frame.

Check:

- Total length and pacing.
- The first frame is a clean screen, not a blank or half-loaded page.
- Every transition. Sensitive content most often appears for a moment between screens.
- Every input field. Values typed during the demo are on screen.
- Any toast, dialog, or error that appeared and vanished.
- The final frame holds long enough to read.

Delete the frames folder after review. Re-record if any check fails.

If the only problem is dead time at the very start or very end, one trim with the installed
ffmpeg is acceptable instead of a re-record:
`ffmpeg -y -ss 3 -i output/media/demo.webm -t 30 -c copy output/media/demo-trimmed.webm`
Then review the trimmed file the same way. Anything else, re-record.
