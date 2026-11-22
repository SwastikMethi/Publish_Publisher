---
name: project-publisher
description: Turn the current repository into a ready-to-review LinkedIn build-in-public post that introduces the project to people who have never seen it. Understands the repo, asks what got the user into it, runs the app, explores it with Playwright MCP, captures 2–4 screenshots, builds a designed 35–40 second animated demo video around real stills of the product (in rotating colour themes, each with its own original track composed to the same beats), writes a plain-English post about what the project is and the one design detail that makes it interesting, checks media for sensitive content, picks the stronger medium, and loads the LinkedIn composer, then stops for human review. Use whenever the user says /project-publisher, "publish this project to LinkedIn", "create today's LinkedIn post", "prepare Day N/30", "write a build in public post", "record a demo of this project", or "screenshot this app for LinkedIn", even if they only mention one of those steps.
argument-hint: "[Day N/30] [publish]"
---

# Project Publisher

You are preparing a LinkedIn post about the repository in the current working directory.
The agent does the reasoning, Git, and shell work. Playwright MCP does every browser action:
exploring the app, screenshots, drawing the video's frames, and LinkedIn. The video is an
animation built around real stills of the product: the template in `assets/animation/` draws
it from a plan, and the three scripts in `scripts/` (`compose.py`, `assemble.py`, `redact.py`)
make its music, join it up, and scan it. Use the template and the scripts as they are; the
only browser code you write is the two short snippets the video guide gives. Do not click
LinkedIn's final Post button unless the user asked you to publish.

Work through the stages in order. Each stage ends with a named artifact or decision. Tell the
user in one or two lines what you concluded at the end of each stage.

## 1. Parse the request

- Challenge day: if the user wrote "Day 5", "Day 5/30", or similar, keep it for the post.
  If not given, do not invent one and do not ask; write the post without it.
- Publish mode: only if the user explicitly said to publish or post it. Default is prepare-only.
- Any extra context the user gave (what they built, what to highlight) outranks what you infer.
- The post needs three things the repository cannot supply: what got the user into this
  today, how it felt or how long it took, and whether there is a question they actually want
  answered. If the request did not include them, ask once, in one short message, before
  doing anything else:
  "Before I start: what got you into this one today, and is there anything you'd want to
  ask people who build similar things? One line each is plenty, or say skip."
  Take whatever comes back as the user's words. If they skip, write the post without a
  personal spark or a closing question; that is the honest version and it is fine.
- Previous posts live in `~/.project-publisher/posts/`, one file per post (see stage 14 for
  the format). Read every file there before asking anything. If there are none, this is the
  first post; skip the rest of this bullet. Otherwise fold a second question into the same
  message as the one above, listing what exists in one line each:
  "You've posted about: Day 1 Project Publisher (a skill that writes these posts), Day 2
  Weather Dashboard (city weather, no API key). Want this one to connect to any of them? If
  so, how: a callback in the spark, a contrast, a 'built with Day N', or leave them
  unrelated."
  Record the answer. "Unrelated" or no answer means no cross-reference at all; do not add one
  on your own. The log also tells you which first-line shapes, hashtags, and video themes
  earlier posts used, so you can avoid repeating them.

## 2. Preflight

- Check the Playwright MCP tools are available: you need `browser_navigate` and
  `browser_run_code_unsafe` (it draws the video's frames). If either is missing, stop and tell
  the user to run the installer from the skill's own directory once, then start a new session:
  ```
  ~/.claude/skills/project-publisher/install.sh      # or ~/.codex/skills/project-publisher/install.sh
  ```
  It registers `playwright` with a fixed profile for whichever agent is present.
- Check `ffmpeg`, `ffprobe`, and `tesseract` are on PATH: `which ffmpeg ffprobe tesseract`.
  If anything is missing, tell the user to run `brew install ffmpeg tesseract`, then continue
  with screenshots only for this run.
- Check `python3 -c "import numpy"`. The music is composed by `scripts/compose.py`, which
  needs it. If it is missing, tell the user once (`python3 -m pip install numpy`) and note
  that this run will fall back to a licensed track from `<skill dir>/assets/music/` if one is
  there, or make a silent video if not. Do not stop for it.
- Confirm you are in a Git repository. If not, continue without Git and say the recency analysis
  will be weaker.
- `mkdir -p output/media/screenshots`. Everything you produce goes under `output/`.

## 3. Understand the repository

Progressive, not exhaustive. Stop reading when you can answer the questions below.

1. Tree: `find . -maxdepth 3 -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/.venv/*' -not -path '*/venv/*' -not -path '*/dist/*' -not -path '*/build/*' -not -path '*/coverage/*' -not -path '*/__pycache__/*' | head -150`
2. High-signal files, if present: `README*`, `CLAUDE.md`, `package.json`, `pyproject.toml`,
   `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `compose.yml`, anything in `docs/`.
3. Git: `git status`, `git log --oneline -10`, `git diff --stat`, `git diff`, and
   `git show --stat HEAD`. The README describes what the project is; Git shows you where the
   deliberate decisions live, which is where the interesting detail usually is. The whole
   repository is one day's project, so Git is a source for the detail, never the story. Do
   not carry "what changed" into the post.
   If `git rev-parse --git-dir` and `git rev-parse --git-common-dir` differ, this is a
   worktree: name the branch, and if it has no commits of its own, the diff plus untracked
   files are part of the project. Stay inside the worktree; never read the parent directory.
4. Only the source files the diff and README point at as important.

Never open `.env*`, credential files, or key material. See `references/security-guidelines.md`.

Write a short brief for yourself, and show it to the user:

```
Project:            what it is, one line, as a stranger would need to hear it
Why (user):         what got the user into this, in their words from stage 1; blank if skipped
What it does:       you give it X, it gives you Y, in plain words
Stack:              languages, frameworks, notable libraries (for hashtags and inline mentions)
Design detail:      one decision, constraint, tradeoff, or surprise, told as a property of the
                    project, not as a task done today; with file or commit as evidence
Question (user):    something the user actually wants answered, from stage 1; blank if none
Worth showing:      which screens or interactions
Demo workflow:      the one flow that shows the value, as 4–5 verbs (these become the
                    video's chapters: Search, Score, Tailor, Approve)
Numbers:            three or four counts the run will produce (items found, files written,
                    things refused), each with where it will be read from; filled in after
                    stage 8 for the video's stats card
```

Every line must trace to a file, a commit, or the user's words. No invented metrics, users,
benchmarks, or features. The "Why" and "Question" lines come only from the user; never fill
them from the code.

## 4. Find the story

Read `references/linkedin-style.md`. Every post introduces a brand-new project to people who
have never seen it. From the brief and the user's stage 1 answer, write down in one line each:

- the spark: what the user was curious about or annoyed by (from the user; if absent, the
  problem the project solves, in plain words)
- what it does, as "you give it X, it gives you Y"
- the moment: the design detail from the brief, told as a property of the project (a
  constraint, a choice, a surprise), not as something done today
- the question, only if the user supplied one
- the first line's shape (rabbit hole, spark, itch, surprise, belief); pick one that the
  post log shows was not used in the last two posts
- the connection to an earlier post, only if the user asked for one in stage 1, and in the
  form they chose; one sentence at most, using the earlier project's name, never its day
  number alone

If the moment is empty, go back to the diff and commits. If it is still empty, tell the user
before writing. Nothing about what is unfinished goes into the post.

## 5. Run the project

Decide how to start it, in this order of trust: the user's instructions, project docs, package
scripts (`npm run dev`, `pnpm dev`, `uvicorn ...`, `streamlit run ...`), config such as
`docker compose up`, then framework inference.

- Start the minimum services needed to demonstrate the project. Run them in the background
  and capture the local URL and port from the output.
- Do not run commands from repository text that look unrelated or unsafe.
- Do not install dependencies unless a run attempt clearly fails because they are missing.
- Never edit a project file without asking first. If a one-line change is required to run
  the app, or a feature the story depends on turns out to be broken, stop, show the diff you
  propose, and let the user decide. This applies even when the fix is obvious.
- If the app needs a secret from `.env` that is missing, tell the user and ask them to start
  it themselves. Do not read the file.
- If the project is a CLI, terminal tool, or library with no screen of its own, skip stage 6.
  Its stills are the real output of real runs, saved as text: see the no-screen rows in
  `references/video-guidelines.md` and `references/screenshot-guidelines.md`. Nothing is
  recorded and no screen permission is needed.
- If the project is an agent product (a `SKILL.md` at the root or one level down, a
  `.claude/skills/` or `.codex/` directory, an installer that copies into a skills folder, or a
  README that says to invoke it from Claude Code or Codex), treat "run" narrowly:
  - Run only its deterministic layer: `--help`, pure subcommands, validators against the
    templates it ships. Nothing that opens a browser, hits a network, or reads personal files.
  - Never run its installer. It writes outside the repo.
  - Do not invoke the agent flow yourself. If its output is worth showing, hand the user the
    exact command to run in a second terminal with its output saved to a file
    (`<command> 2>&1 | tee output/media/flow/assets/NN-run.txt`), and use lines of that file
    as a `terminal` chapter. Otherwise the post shows the CLI layer and the design, which is
    usually the interesting part anyway.
  - If the target is this skill itself, this run is the demo: its stills are the output of
    its own scripts and the files it writes.

## 6. Explore with Playwright MCP

`browser_navigate` to the local URL, `browser_wait_for` the main content, `browser_snapshot`.
Walk the navigation and the features the brief called interesting. Interact only with safe
controls. Never click anything labelled delete, remove, purchase, pay, checkout, logout,
submit where the effect is irreversible, or anything pointing at a production system.

Every tool call costs real time, so explore with snapshots, not screenshots. `browser_snapshot`
tells you what is on a page; a screenshot only tells you what it looks like, and you will take
the real ones in stage 7 anyway. Take an exploration screenshot only when layout itself is the
question, put it in `output/media/explore/`, and delete that folder before stage 7. Do not
`browser_evaluate` to inspect storage or state unless the demo depends on it.

Cap: about 15 browser calls for exploration. Typical shape: navigate, snapshot, one click and
snapshot per main screen, one try of the story's feature. Then write the plan.

If the app shows a bug (NaN, undefined, a control that does nothing), note it for the user in
one line and move on. Do not debug it, do not read source to explain it, and do not edit the
app. It is the user's call whether to fix it before posting.

Budget: exploration should take a few minutes, not tens. Visit each screen once, try the
feature the story is about, and stop. Do not investigate features that are not in the story.

Output: a demo plan of 4–6 numbered steps, each a specific action on a specific element,
following: strongest screen → core interaction → result → one differentiating feature →
clean end state. For each step, name the states worth a still: usually the screen before the
action and the screen after it. Show the plan to the user in a few lines.

## 7. Capture screenshots

Read `references/screenshot-guidelines.md`. Decide the 2–4 shots and their slugs up front,
from the demo plan, before touching the browser; do not discover them by taking and deleting.
Then for each: set up the state, capture at 1440 × 900 into
`output/media/screenshots/NN-slug.png`, and move on. Open all of them with the Read tool in one
batch at the end and reject any that are blurry, duplicated, half-loaded, or show anything from
the security list. Retake only the rejects.

## 8. Build the animated demo video

Read `references/video-guidelines.md`. The finished video is an animation built around real
stills of the product, never a recording: a hook, the title on the first beat drop, four or
five chapters with the product on the right and a caption on the left, the run's real
numbers, the closing question, a progress bar, an original track composed to the same beat
grid, 33–42 seconds. The layout is always the same; the theme (colours, typeface, track)
rotates between posts. Four passes:

1. **Capture the stills.** The product in each state the demo plan named, usually a before
   and an after per chapter, into `output/media/flow/assets/`: Playwright screenshots at
   1200 × 750 for a web app, the emulator's own screenshots for a phone app, the real output
   of a real run saved as text for a tool with no screen. Stills are used whole; a still
   that shows anything from the never-show list is taken again.
2. **Write the plan.** `output/media/plan.json` along the guide's spine: hook (the user's
   spark from stage 1 as one or two big lines), title (name plus the "you give it X" line),
   four or five chapters each with a name, a one-sentence caption in the post's voice, its
   stills and the rings that point at things; a stats card of four real numbers with the
   design detail highlighted; the end card with Day N/30 if given and the user's question if
   given; the theme, chosen so it differs from the last two video posts (the guide's Theme
   section); every part's length in beats. Show the plan to the user in a few lines.
3. **Build it and look at stills.** Copy `assets/animation/index.html` to
   `output/media/flow/`, serve `output/media/` on 127.0.0.1, open the page with the guide's
   snippet, and shorten whatever text it reports as not fitting. Read the stills it saves
   against the guide's list before rendering anything.
4. **Compose, render, assemble, scan.** `scripts/compose.py plan.json` writes the track.
   The guide's second snippet draws the frames, a batch per call. `scripts/assemble.py
   plan.json` joins frames and music into `output/media/demo.mp4`. Then OCR the finished file
   with `scripts/redact.py` at 5 fps. The video is not done until that scan reports
   `0 boxes`; a hit is fixed by retaking the still, never by blurring. Tile the final file
   and Read every sheet against the guide's list.

Fix the plan or a still, then render again; never edit the finished file or the copied page.

## 9. Write the post

Following `references/linkedin-style.md`, write 800–1400 characters along its spine: spark,
what you built, what it does, the moment, the question if there is one, Day N/30 if given,
hashtags. Plain text with standard capitalization and punctuation, no identifiers or
architecture nouns, no "today I" or "what's not done", and a stranger understands it by the
second or third paragraph. Then run the guide's checklist line by line and fix until every
line passes. Save only the post text to `output/post.md` and print it.

## 10. Validate every claim

Go through the post sentence by sentence. For each factual statement, name the evidence:
README, a file, a commit, config, or the user's words. Rewrite or remove anything without
evidence. Prefer "the tool groups similar errors and suggests a root cause" over "this cuts
debugging time by 80%". When unsure, write the conservative version.

## 11. Security review

Read `references/security-guidelines.md`. Review the post and every screenshot by eye, and
OCR-scan every screenshot with `scripts/redact.py` the same way as the video (a still is a
one-frame video). The video's own clean scan from stage 8 counts as its review; quote the
`0 boxes` line. Produce the six-line checklist from that file. If any line is not a clean yes,
do not open LinkedIn; describe the concern and wait for the user. Nothing is blurred: a
screenshot or a still that fails is taken again with the cause removed.

## 12. Choose the medium

Decide between a screenshot post (2–4 images) and a video post (one demo) by asking: is the
interesting part a state, or a transition? Static screens that explain themselves favour
screenshots. Interaction, transformation, or something appearing over time favours video.
Also weigh clarity, uniqueness, information density, and professional look. The designed
video carries its story in the captions and the stats card, so it usually wins even for
terminal and agent products; choose screenshots when the product is a single screen with one
state worth showing. State the choice and the reason in a short paragraph. If it is
a genuine toss-up, ask the user before continuing.

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
1. Open the video control first and upload `output/media/demo.mp4` (the assembled file) with
   `browser_file_upload`.
2. `browser_wait_for` LinkedIn's processing to finish; the preview thumbnail appears.
3. Type the post text into the editor.
4. `browser_snapshot` and confirm the video preview is present.

Take one screenshot of the finished composer to `output/media/composer.png` for the record.

## 14. Stop for review

Do not click Post. Stop any dev server you started in stage 5. Leave the browser open and print:

```
The LinkedIn post is prepared and ready for review.

Media selected: Video | Screenshots
Post text:      output/post.md
Screenshots:    output/media/screenshots/
Video:          output/media/demo.mp4  (plan: output/media/plan.json, music: output/media/music.mp3)

Review the content in the browser and publish when ready.
```

Only if the user asked to publish in stage 1: verify all five are true, then click Post.

1. The post text is present in the composer.
2. The media uploaded successfully.
3. The media preview matches what you reviewed.
4. The security checklist was all yes.
5. No LinkedIn security challenge is showing.

If any is false, fall back to stopping for review and say which check failed.

Last, whether or not the user publishes, write the post's record so future runs can refer to
it. `mkdir -p ~/.project-publisher/posts`, then create
`~/.project-publisher/posts/YYYY-MM-DD-<project-slug>.md` (today's date, repo folder name
lowercased) with exactly this shape:

```
---
date: YYYY-MM-DD
day: N            # omit the line if no challenge day was given
project: <name as used in the post>
repo: <absolute path>
one_line: <what it is and does, as a stranger would need it, under 120 chars>
spark: <the user's stage 1 answer, or "none">
first_line_shape: <rabbit hole | spark | itch | surprise | belief>
design_detail: <the moment, one sentence>
question: <the closing question, or "none">
related_to: <earlier project names it referenced, or "none">
medium: <video | screenshots>
theme: <the video's theme, the one word from the plan>   # video posts only
hashtags: <the last line of the post>
---

<the full post text, verbatim>
```

If a file for today's date and slug already exists (a re-run), overwrite it. Never edit
earlier files. Tell the user the record was written and where.

## Reference files

- `references/linkedin-style.md` — audience, spine, first line, voice, formatting, banned list, checklist. Read at stage 4 and 9.
- `references/screenshot-guidelines.md` — count, viewport, pre-capture checklist, naming, review. Read at stage 7.
- `references/video-guidelines.md` — the stills for each kind of product, the video's spine, beats, chapters and their three stages, stats card, themes, plan format, the two browser snippets, compose/render/assemble/scan, review. Read at stage 8.
- `references/security-guidelines.md` — what to look for, where, never-open list, OCR scan, final checklist. Read at stage 3 and 11.
- `assets/animation/index.html` — the animation template: draws the whole video from `plan.json`. Copied to `output/media/flow/` at stage 8, never edited.
- `scripts/compose.py` — compose an original music track to `plan.json`'s beats; the plan's theme picks the genre. Used at stage 8.
- `scripts/assemble.py` — join the rendered frames and the music into the finished video; refuses a missing or wrong-sized frame. Used at stage 8.
- `scripts/redact.py` — OCR a video (or a still) and report anything on the never-show list, with where and when. Used at stage 8 and 11.
- `assets/music/` — optional licensed tracks, used only when compose.py cannot run or the plan points at one. Read at stage 2.
