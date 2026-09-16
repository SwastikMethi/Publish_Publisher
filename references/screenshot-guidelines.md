# Screenshot guidelines

Read this before capturing screenshots. Screenshots are captured for every project, even when
the video is chosen for LinkedIn.

## How many and which

Capture 2–4. Each one should earn its place in the story the post tells:

1. The main experience. What the user sees first, with real content loaded.
2. The core feature in use. The thing the post is about.
3. The result or output. What the feature produced.
4. Optional: one more feature that differentiates the project, only if it looks different from 1–3.

Skip any shot that looks nearly identical to one already taken. Two screenshots that differ only
by a dropdown value are one screenshot.

Prefer feature-rich screens with real data over empty states, settings pages, and login forms.

## Viewport

- Call `browser_resize` to 1440 × 900 before the first capture unless the product is
  mobile-first, in which case use a phone viewport and say so.
- Capture the viewport, not the full page, unless a long page is the point.
- Use `browser_take_screenshot` with an explicit `filename` under `output/media/screenshots/`.

## Before each capture

Check via `browser_snapshot` or a quick look, then fix, then capture:

- Content has finished loading. No spinners, skeletons, or "Loading..." text.
- No cookie banners, toasts, tooltips, or modals covering content, unless the modal is the feature.
- No browser developer tools, Playwright overlays, or highlight outlines left on.
- No focused input with a blinking caret or focus ring drawing the eye, unless typing is the point.
- No empty or error states. If the app needs data to look good, create safe sample data first.
- No terminal windows, unless the terminal is the product. When it is, capture a fresh
  Terminal.app window by id with `screencapture -x -o -l<id>` and a plain `$ ` prompt, as
  described in `references/video-guidelines.md`. Good subjects: the `--help` output, a
  validator run against a shipped template, a tree of the skill files, one test run passing.
  No `user@hostname`, no absolute paths under the home directory.
- No secrets, tokens, emails, private URLs, internal hostnames, or personal data anywhere on screen.
  See `references/security-guidelines.md` for the full list.

## Naming

```
output/media/screenshots/01-main.png
output/media/screenshots/02-<feature>.png
output/media/screenshots/03-result.png
output/media/screenshots/04-<extra>.png
```

Use a short lowercase slug that says what the shot shows.

## After capture

Open every screenshot with the Read tool, all in one batch after the last capture rather than
one at a time between captures. Do not trust that the capture matched the snapshot. Check for:

- cut-off content at the edges
- a spinner or toast that appeared between snapshot and capture
- anything from the security list

Retake any that fail. Delete the rejects so the output folder holds only usable images.

## Story fit

Before moving on, write one line per screenshot saying which part of the post it supports.
If a screenshot supports nothing, drop it.
