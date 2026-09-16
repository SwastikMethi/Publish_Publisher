# Project Publisher

A Claude Code Skill that turns a finished software project into a ready-to-review LinkedIn
build-in-public post, with screenshots and a short demo video already loaded into the composer.

Built as Day 1 of a 30-day challenge: one project a day, each posted to LinkedIn. This is the
tool that publishes the other 29.

There is no application here. The skill is a set of instructions that Claude Code or Codex follows using
capabilities it already has: reading the repository, running Git and shell commands, driving a
browser through Playwright MCP, and writing. No Python, no backend, no custom automation.

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
Playwright explores it (not recorded)
      ↓
2–4 screenshots captured and inspected
      ↓
15–45 second demo video recorded and reviewed
      ↓
LinkedIn post written, every claim checked against the repo
      ↓
Security review of post, screenshots, and full video
      ↓
Screenshots or video chosen as the stronger medium
      ↓
LinkedIn composer opened, text inserted, media uploaded
      ↓
Stops. You review and press Post.
```

## Requirements

- Claude Code or Codex.
- Playwright MCP with the `devtools` capability enabled, which provides video recording.
  The installer registers it.
- A browser Playwright can launch (Chromium is downloaded on first use).
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
2. Registers a Playwright MCP server named `playwright` at user scope with video recording
   enabled and a fixed browser profile, so your LinkedIn login carries across projects.

If an agent already has a `playwright` server configured differently, the installer shows it
and asks before replacing it. Pass `--force` to replace without asking, or `--skip-mcp` to
link the skill and leave MCP alone. Running it again is safe; it changes nothing that is
already correct.

To do it by hand instead:

```bash
ln -s ~/Projects/Project_Publisher ~/.claude/skills/project-publisher
claude mcp add --scope user playwright -- npx @playwright/mcp@latest --caps=devtools --user-data-dir ~/.playwright-mcp/project-publisher --output-dir ~/.playwright-mcp/output
```

For Codex, replace the first line's target with `~/.codex/skills/project-publisher` and the
second with `codex mcp add playwright -- npx @playwright/mcp@latest ...` (same arguments).

Start a new session in the agent after installing.

Notes:

- If a project already has its own `playwright` MCP server configured at project scope, it
  shadows the user-scope one. If that project entry lacks `--caps=devtools`, video tools will be
  missing there. The skill detects this and tells you.
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
    ├── demo.webm           the demo video
    └── composer.png        the prepared LinkedIn composer, for the record
```

Both screenshots and video are always captured, even though only one is loaded into LinkedIn.

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
  private URLs, personal data, and internal names before LinkedIn is opened. If anything is
  uncertain, Claude stops and asks.
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
└── references/
    ├── linkedin-style.md          audience, post spine, first line, voice, checklist
    ├── screenshot-guidelines.md   what to capture and how to check it
    ├── video-guidelines.md        planning, recording, and reviewing the demo
    └── security-guidelines.md     what must never be posted
```

`SKILL.md` is deliberately short. The reference files hold the detail and are read only at the
stage that needs them.

## Terminal, CLI, and agent projects

When a project has no web UI, the terminal is the product. The skill opens a clean Terminal.app
window through AppleScript, gives it a plain prompt, and captures that window by id with the
macOS built-in `screencapture`. Short deterministic commands become screenshots. A long agent
run that you drive in that window is recorded whole and compressed into a timelapse with
`ffmpeg`. Playwright is still used for the LinkedIn step.

This needs Screen Recording permission for the app that runs Claude Code. The skill checks and
tells you which app to allow if the capture fails.

For agent products, meaning skills, Codex or Claude Code pipelines, and anything with an
installer that copies into a skills folder, the skill runs only the deterministic layer: help
text, validators, pure subcommands. It never runs the installer and never invokes the agent flow
itself, because that may open browsers as you or act on your accounts. If a live demo is worth
having, it hands you the command and records you running it.

Git worktrees are detected. The branch is named, uncommitted work counts as part of the
project, and the parent directory is never read.

## What the post looks like

Each post introduces the project to people who have never seen it: what got you into it, what
you built, what it does in plain words, and the one design detail that makes it interesting.
It is not a changelog. Nothing about "what I did today" or "what's not done" goes in, and no
code identifiers or architecture terms. See `references/linkedin-style.md` for the full
guide, including a worked bad-versus-good example.
