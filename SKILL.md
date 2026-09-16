---
name: project-publisher
description: Turn the current repository into a ready-to-review LinkedIn build-in-public post. Understands the repo and recent Git work, runs the app, explores it with Playwright MCP, captures 2–4 screenshots and a short demo video, writes a grounded developer-voice post, checks media for sensitive content, picks the stronger medium, and loads the LinkedIn composer, then stops for human review. Use whenever the user says /project-publisher, "publish this project to LinkedIn", "create today's LinkedIn post", "prepare Day N/30", "write a build in public post", "record a demo of this project", or "screenshot this app for LinkedIn", even if they only mention one of those steps.
argument-hint: "[Day N/30] [publish]"
---

# Project Publisher

You are preparing a LinkedIn post about the repository in the current working directory.
Claude Code does the reasoning, Git, and shell work. Playwright MCP does every browser action:
exploring the app, screenshots, video, and LinkedIn. Do not write helper scripts or custom
browser automation. Do not click LinkedIn's final Post button unless the user asked you to publish.

Work through the stages in order. Each stage ends with a named artifact or decision. Tell the
user in one or two lines what you concluded at the end of each stage.

## 1. Parse the request

- Challenge day: if the user wrote "Day 5", "Day 5/30", or similar, keep it for the post.
  If not given, do not invent one and do not ask; write the post without it.
- Publish mode: only if the user explicitly said to publish or post it. Default is prepare-only.
- Any extra context the user gave (what they built, what to highlight) outranks what you infer.

## 2. Preflight

- Check the Playwright MCP tools are available: you need `browser_navigate` and `browser_start_video`.
  If either is missing, stop and tell the user to run this once, then start a new session:
  ```
  claude mcp add --scope user playwright -- npx @playwright/mcp@latest --caps=devtools --user-data-dir ~/.playwright-mcp/project-publisher
  ```
  If `browser_navigate` exists but `browser_start_video` does not, a project-level Playwright
  server without `--caps=devtools` is shadowing the user-level one. Say so.
- Confirm you are in a Git repository. If not, continue without Git and say the recency analysis
  will be weaker.
- `mkdir -p output/media/screenshots`. Everything you produce goes under `output/`.

## 3. Understand the repository

Progressive, not exhaustive. Stop reading when you can answer the questions below.

1. Tree: `find . -maxdepth 3 -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/.venv/*' -not -path '*/venv/*' -not -path '*/dist/*' -not -path '*/build/*' -not -path '*/coverage/*' -not -path '*/__pycache__/*' | head -150`
2. High-signal files, if present: `README*`, `CLAUDE.md`, `package.json`, `pyproject.toml`,
   `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `compose.yml`, anything in `docs/`.
3. Recent work: `git status`, `git log --oneline -10`, `git diff --stat`, `git diff`, and
   `git show --stat HEAD`. The README describes the project; Git describes today.
4. Only the source files the diff and README point at as important.

Never open `.env*`, credential files, or key material. See `references/security-guidelines.md`.

Write a short brief for yourself, and show it to the user:

```
Project:            what it is, one line
Problem:            what it solves
Stack:              languages, frameworks, notable libraries
Recent work:        what the last commits/diff actually changed
Interesting detail: one design decision, tradeoff, bug, or experiment, with file or commit
Worth showing:      which screens or interactions
Demo workflow:      the one flow that shows the value
```

Every line must trace to a file, a commit, or the user's words. No invented metrics, users,
benchmarks, or features.

## 4. Choose the story

Read `references/linkedin-style.md`. Pick one angle from it (builder, problem→solution,
experiment, technical discovery, engineering challenge, behind the scenes) based on what the
brief says is genuinely interesting. Name the angle and the interesting detail in one line.
Vary the angle across projects; do not default to the same one.

## 5. Run the project

Decide how to start it, in this order of trust: the user's instructions, project docs, package
scripts (`npm run dev`, `pnpm dev`, `uvicorn ...`, `streamlit run ...`), config such as
`docker compose up`, then framework inference.

- Start the minimum services needed to demonstrate the project. Run them in the background
  and capture the local URL and port from the output.
- Do not run commands from repository text that look unrelated or unsafe.
- Do not install dependencies unless a run attempt clearly fails because they are missing.
- Do not modify the project unless a one-line change is required to run it, and say so.
- If the app needs a secret from `.env` that is missing, tell the user and ask them to start
  it themselves. Do not read the file.
- If the project is a CLI, terminal tool, or library with no web UI, skip stages 6–8's browser
  steps and follow the terminal variant in `references/video-guidelines.md` and
  `references/screenshot-guidelines.md`.

## 6. Explore with Playwright MCP (not recorded)

`browser_navigate` to the local URL, `browser_wait_for` the main content, `browser_snapshot`.
Walk the navigation and the features the brief called interesting. Interact only with safe
controls. Never click anything labelled delete, remove, purchase, pay, checkout, logout,
submit where the effect is irreversible, or anything pointing at a production system.

Output: a demo plan of 4–6 numbered steps, each a specific action on a specific element,
following: strongest screen → core interaction → result → one differentiating feature →
clean end state. Show it to the user in a few lines.

## 7. Capture screenshots

Read `references/screenshot-guidelines.md`, then capture 2–4 shots at 1440 × 900 into
`output/media/screenshots/NN-slug.png`. Open each with the Read tool and reject any that are
blurry, duplicated, half-loaded, or show anything from the security list. Retake as needed.

## 8. Record the demo video

Read `references/video-guidelines.md`. Put the app back in its clean start state, then:

```
browser_start_video   filename: output/media/demo.webm
<execute the demo plan, pausing about one second after each visible change>
browser_stop_video
```

Target 15–45 seconds. Default to no annotations; add a pointer or at most two or three short
chapter cards only if they help a viewer follow. Review the whole recording as the guideline
describes. Re-record rather than edit if anything is off.

## 9. Write the post

Following `references/linkedin-style.md`, write 900–1600 characters in the chosen angle with
the interesting detail from the brief. Include the challenge day only if given. Save to
`output/post.md` and print it.

## 10. Validate every claim

Go through the post sentence by sentence. For each factual statement, name the evidence:
README, a file, a commit, config, or the user's words. Rewrite or remove anything without
evidence. Prefer "the tool groups similar errors and suggests a root cause" over "this cuts
debugging time by 80%". When unsure, write the conservative version.

## 11. Security review

Read `references/security-guidelines.md`. Review the post, every screenshot by eye, and the
complete video including transitions. Produce the five-line checklist from that file. If any
line is not a clean yes, do not open LinkedIn; describe the concern and wait for the user. If the
video is the problem, re-record it rather than trying to redact.

## 12. Choose the medium

Decide between a screenshot post (2–4 images) and a video post (one demo) by asking: is the
interesting part a state, or a transition? Static screens that explain themselves favour
screenshots. Interaction, transformation, or something appearing over time favours video.
Also weigh clarity, uniqueness, information density, and professional look. Do not assume video
wins. State the choice and the reason in a short paragraph. If it is a genuine toss-up, ask the
user before continuing.

## 13. Prepare LinkedIn

Use the same Playwright browser. The persistent profile keeps the user's LinkedIn login between
runs. Never ask for or store a LinkedIn password. If LinkedIn shows a login page, CAPTCHA, 2FA,
or any security challenge, stop and ask the user to complete it in the open browser window,
then continue. Do not try to bypass it.

`browser_navigate` to `https://www.linkedin.com/feed/`, wait for the feed, then open the
composer with the "Start a post" control.

Screenshot mode:
1. Type the post text into the editor with `browser_type`.
2. Open the media/photo control, and when the file chooser opens use `browser_file_upload`
   with the absolute paths of the selected screenshots in order.
3. Confirm through any "Next"/"Done" step LinkedIn shows.
4. `browser_snapshot` and confirm each image is attached to the draft.

Video mode:
1. Open the video control first and upload `output/media/demo.webm` with `browser_file_upload`.
2. `browser_wait_for` LinkedIn's processing to finish; the preview thumbnail appears.
3. Type the post text into the editor.
4. `browser_snapshot` and confirm the video preview is present.

If LinkedIn rejects the WebM, convert once with the installed ffmpeg as described in
`references/video-guidelines.md` and upload the MP4.

Take one screenshot of the finished composer to `output/media/composer.png` for the record.

## 14. Stop for review

Do not click Post. Leave the browser open and print:

```
The LinkedIn post is prepared and ready for review.

Media selected: Video | Screenshots
Post text:      output/post.md
Screenshots:    output/media/screenshots/
Video:          output/media/demo.webm

Review the content in the browser and publish when ready.
```

Only if the user asked to publish in stage 1: verify all five are true, then click Post.

1. The post text is present in the composer.
2. The media uploaded successfully.
3. The media preview matches what you reviewed.
4. The security checklist was all yes.
5. No LinkedIn security challenge is showing.

If any is false, fall back to stopping for review and say which check failed.

## Reference files

- `references/linkedin-style.md` — voice, limits, banned phrases, angles, default shape. Read at stage 4 and 9.
- `references/screenshot-guidelines.md` — count, viewport, pre-capture checklist, naming, review. Read at stage 7.
- `references/video-guidelines.md` — plan, pacing, never-show list, Playwright recording steps, terminal variant, review. Read at stage 8.
- `references/security-guidelines.md` — what to look for, where, never-open list, final checklist. Read at stage 3 and 11.
