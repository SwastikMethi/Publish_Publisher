# Project Publisher

A Claude Code Skill that turns a finished software project into a ready-to-review LinkedIn
build-in-public post, with screenshots and a designed 35–40 second animated demo video already loaded
into the composer.

Built as Day 1 of a 30-day challenge: one project a day, each posted to LinkedIn. This is the
tool that publishes the other 29.

There is no application here. The skill is a set of instructions that Claude Code or Codex
follows using capabilities it already has: reading the repository, running Git and shell
commands, driving a browser through Playwright MCP, and writing. The only code is one web page,
the animation template that draws the video, and three small deterministic scripts that compose
the music, join the frames into the video, and scan it for sensitive text by OCR. None of them
touches the network or anything outside the project's `output/` folder.

## Workflow

```
Build project
      ↓
Invoke Project Publisher from the project directory
      ↓
Claude reads the repo, README, and recent Git history
      ↓
Claude asks what got you into this today and whether to connect it to an earlier post
      ↓
Claude finds the one design detail that makes the project interesting
      ↓
Application runs locally
      ↓
Playwright explores it
      ↓
2–4 screenshots captured and inspected
      ↓
Stills captured: the product in each state worth showing (real output as text if it has no screen)
      ↓
Plan: hook, title, 4–5 chapters with their stills and captions, stats, end card, theme
      ↓
The animation template draws it; stills are checked; music is composed to the same beats
      ↓
Frames rendered, joined with the music, and the finished video OCR-scanned until clean
      ↓
LinkedIn post written, every claim checked against the repo
      ↓
Security review of post, screenshots, and the final video
      ↓
Screenshots or video chosen as the stronger medium
      ↓
LinkedIn composer opened, text inserted, media uploaded
      ↓
Stops. You review and press Post.
```

## Requirements

- macOS. The animation's themes use typefaces that ship with macOS (SF Pro, Avenir Next,
  Futura, Charter), and the installer assumes Homebrew.
- Claude Code or Codex.
- Playwright MCP. The installer registers it. No special capability is needed: the video's
  frames are drawn with its ordinary tools.
- A browser Playwright can launch (Chromium is downloaded on first use).
- `ffmpeg` and `tesseract`, for joining the video and the OCR scan: `brew install ffmpeg
  tesseract`. The installer checks and prints the line if either is missing. Python 3 as
  shipped with macOS is enough for `redact.py` and `assemble.py`; `compose.py`, which writes
  the music, needs `numpy` (`python3 -m pip install numpy`).
- Optional: background tracks you are licensed to use, dropped into `assets/music/`. They
  are only used when the composer cannot run or a plan points at one; normally every video
  gets its own original track. See `assets/music/README.md`.
- A LinkedIn account. You log in once in the Playwright browser window; the profile is kept
  between runs so you are not asked again.

## Install

Clone this repository and run the installer. It works for Claude Code and Codex:

```bash
git clone <this repo> ~/Projects/Project_Publisher
cd ~/Projects/Project_Publisher
./install.sh
```

With no flags it installs for every agent whose CLI is on your PATH. Use `--claude` or
`--codex` to pick one. For each agent it does two things:

1. Symlinks this repository into the agent's skills directory (`~/.claude/skills` or
   `~/.codex/skills`), so `git pull` updates the skill in place.
2. Registers a Playwright MCP server named `playwright` at user scope with a fixed browser
   profile, so your LinkedIn login carries across projects.

If an agent already has a `playwright` server configured differently, the installer shows it
and asks before replacing it. Pass `--force` to replace without asking, or `--skip-mcp` to
link the skill and leave MCP alone. Running it again is safe; it changes nothing that is
already correct.

To do it by hand instead:

```bash
ln -s ~/Projects/Project_Publisher ~/.claude/skills/project-publisher
claude mcp add --scope user playwright -- npx @playwright/mcp@latest --user-data-dir ~/.playwright-mcp/project-publisher --output-dir ~/.playwright-mcp/output
```

For Codex, replace the first line's target with `~/.codex/skills/project-publisher` and the
second with `codex mcp add playwright -- npx @playwright/mcp@latest ...` (same arguments).

Start a new session in the agent after installing.

Notes:

- If a project already has its own `playwright` MCP server configured at project scope, it
  shadows the user-scope one, and its browser profile will not hold your LinkedIn login.
- `--output-dir` keeps Playwright's own page snapshots out of your project. Screenshots and video still go to `output/` because the skill passes explicit filenames.
- A persistent browser profile can be used by one browser at a time. If Playwright fails to
  launch, close other Playwright MCP browsers first.

## Usage

From inside any project repository:

```
/project-publisher
/project-publisher Day 5/30
```

Or in plain words:

```
Publish this project to LinkedIn.
Create today's LinkedIn post for this project.
Prepare Day 5/30 for LinkedIn.
```

If you give a challenge day, it goes into the post. If you do not, no day is invented.

Add the word `publish` if you want Claude to press Post itself after its checks pass.
Without it, Claude always stops before posting.

The first time LinkedIn is opened, log in manually in the browser window that appears. Claude
never asks for or stores your password and does not attempt to get past CAPTCHA or 2FA.

## Output

Everything lands in `output/` inside the project you ran it from:

```
output/
├── post.md                 the LinkedIn text
└── media/
    ├── screenshots/
    │   ├── 01-main.png
    │   ├── 02-feature.png
    │   └── 03-result.png
    ├── flow/
    │   ├── index.html      a copy of the animation template
    │   └── assets/         the stills: captures of the product, or its real output as text
    ├── plan.json           the plan: theme, hook, title, chapters, stats, end card
    ├── music.mp3           the original track composed for this plan
    ├── leftover.json       what the OCR scan of the finished video found (empty when clean)
    ├── demo.mp4            the finished video; the only one that is ever uploaded
    └── composer.png        the prepared LinkedIn composer, for the record
```

Both screenshots and video are always made, even though only one is loaded into LinkedIn.
The stills and the plan stay in `output/media/` for the record and never leave it.

Add `output/` to the project's `.gitignore` if you do not want media committed.

A record of every post is also kept outside the project, in
`~/.project-publisher/posts/YYYY-MM-DD-<project>.md`: the post text plus what it was about,
the opener shape, the hashtags, and which earlier projects it referenced. At the start of each
run the skill reads these and asks whether today's post should connect to any of them and how.
The default is no connection; every post has to stand alone for a reader who never saw the
others.

## Safety

- Prepare-only by default. The final Post button is never clicked unless you ask.
- Every factual claim in the post is checked against the README, code, config, Git history, or
  your own words. Metrics, user counts, and benchmarks are not invented, and neither is your
  motivation: if you skip the "what got you into this" question, the post opens on what the
  project does rather than on a made-up story.
- The post, every screenshot, and the complete video are reviewed for secrets, credentials,
  private URLs, personal data, and internal names before LinkedIn is opened. The finished
  video is additionally OCR-scanned for home paths, usernames, repo URLs, emails, and token
  shapes, and must come back clean before it counts as reviewed. Nothing is blurred: a still
  that shows any of them is taken again. If anything is uncertain, Claude stops and asks.
- `.env` files, cookies, key material, and credential stores are never read.
- Playwright only interacts with safe controls while exploring. Nothing labelled delete,
  purchase, pay, logout, or pointing at production is clicked.

## Layout

```
project-publisher/
├── SKILL.md                       the orchestration instructions Claude follows
├── README.md
├── install.sh                     symlinks the skill and registers Playwright MCP for Claude Code and Codex
├── agents/
│   └── openai.yaml                metadata so OpenAI-style agents can also discover the skill
├── assets/
│   ├── animation/index.html       the animation template: draws the whole video from plan.json
│   └── music/                     optional licensed tracks (gitignored; README explains)
├── scripts/
│   ├── compose.py                 compose an original track to plan.json's beats
│   ├── assemble.py                join the rendered frames and the music into the finished video
│   ├── redact.py                  OCR a video or a still and report sensitive text
│   └── test_assemble.py           checks for assemble.py
└── references/
    ├── linkedin-style.md          audience, post spine, first line, voice, checklist
    ├── screenshot-guidelines.md   what to capture and how to check it
    ├── video-guidelines.md        stills, plan, themes, building, rendering, scan, review
    └── security-guidelines.md     what must never be posted, and the OCR scan
```

`SKILL.md` is deliberately short. The reference files hold the detail and are read only at the
stage that needs them. The scripts are plain Python 3 with no dependencies beyond `ffmpeg`
and `tesseract` on PATH, except the composer, which needs `numpy`. The template is one HTML
file with no dependencies at all.

## The video

Nothing is recorded. The video is an animation built around real stills of the product:
captures of its screens shown whole and unchanged, with rings pointing at things. The skill
captures the product in each state worth showing, usually a before and an after, then writes
a plan with the same spine as the post: the spark as a hook, the title on the first drop of
the music, four or five chapters with the product on the right and a caption that carries the
meaning on the left, four real numbers from the run with the design detail highlighted, and
the post's closing question. A progress bar runs along the bottom.

One page, `assets/animation/index.html`, draws all of it from that plan. It is a pure function
of time, so Playwright can draw it frame by frame and every frame comes out the same each
time. The layout never changes. The theme does, and themes rotate so no two posts in a row
look or sound alike:

| Theme | Colours | Typeface | Track |
|---|---|---|---|
| `aurora` | near-black, violet to blue | SF Pro | marimba pop, 120 bpm |
| `ember` | warm black, amber to rose | Avenir Next | half-time trap, 140 bpm |
| `lagoon` | teal-black, mint to sky blue | Futura | electro-pop, 125 bpm |
| `daylight` | cool off-white, cobalt to violet | Charter | acoustic indie, 124 bpm |

Every length in the plan is a count of beats, so picture and music share one grid.
`scripts/compose.py` synthesises an original track that follows the plan: a riser under the
hook, a drop on the title, a break under the stats card, a second drop on the chapter after
it, a fade with the end card. Nothing is sampled or downloaded, so there is nothing for
LinkedIn to flag. `scripts/assemble.py` joins the frames and the track into `demo.mp4`, and
refuses to if a frame is missing. Fixes go into the plan or a still, never into the output.

## Terminal, CLI, and agent projects

When a project has no screen of its own, its stills are the real output of real runs, saved
as text. A chapter then shows a terminal-style panel in which those lines appear in order,
with the ones that matter highlighted. A line is never edited; whole lines may be left out.
No screen recording is made and no Screen Recording permission is needed.

For agent products, meaning skills, Codex or Claude Code pipelines, and anything with an
installer that copies into a skills folder, the skill runs only the deterministic layer: help
text, validators, pure subcommands. It never runs the installer and never invokes the agent flow
itself, because that may open browsers as you or act on your accounts. If the output of a real
run is worth showing, it hands you the command to run with its output saved to a file.

Git worktrees are detected. The branch is named, uncommitted work counts as part of the
project, and the parent directory is never read.

## What the post looks like

Each post introduces the project to people who have never seen it: what got you into it, what
you built, what it does in plain words, and the one design detail that makes it interesting.
It is not a changelog. Nothing about "what I did today" or "what's not done" goes in, and no
code identifiers or architecture terms. See `references/linkedin-style.md` for the full
guide, including a worked bad-versus-good example.
