# Project Publisher

A Claude Code Skill that turns a finished software project into a ready-to-review LinkedIn
build-in-public post, with screenshots and a short demo video already loaded into the composer.

Built as Day 1 of a 30-day challenge: one project a day, each posted to LinkedIn. This is the
tool that publishes the other 29.

There is no application here. The skill is a set of instructions that Claude Code follows using
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
Claude picks the story angle and the one interesting detail
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

- Claude Code.
- Playwright MCP with the `devtools` capability enabled, which provides video recording.
- A browser Playwright can launch (Chromium is downloaded on first use).
- A LinkedIn account. You log in once in the Playwright browser window; the profile is kept
  between runs so you are not asked again.

## Install

Clone this repository and symlink it into your personal skills directory:

```bash
git clone <this repo> ~/Projects/Project_Publisher
ln -s ~/Projects/Project_Publisher ~/.claude/skills/project-publisher
```

Register Playwright MCP once, at user scope, with video enabled and a fixed browser profile so
your LinkedIn login carries across projects:

```bash
claude mcp add --scope user playwright -- npx @playwright/mcp@latest --caps=devtools --user-data-dir ~/.playwright-mcp/project-publisher --output-dir ~/.playwright-mcp/output
```

Start a new Claude Code session after both steps.

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

## Safety

- Prepare-only by default. The final Post button is never clicked unless you ask.
- Every factual claim in the post is checked against the README, code, config, or Git history.
  Metrics, user counts, and benchmarks are not invented.
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
├── agents/
│   └── openai.yaml                metadata so OpenAI-style agents can also discover the skill
└── references/
    ├── linkedin-style.md          voice, limits, banned phrases, story angles
    ├── screenshot-guidelines.md   what to capture and how to check it
    ├── video-guidelines.md        planning, recording, and reviewing the demo
    └── security-guidelines.md     what must never be posted
```

`SKILL.md` is deliberately short. The reference files hold the detail and are read only at the
stage that needs them.

## Terminal and CLI projects

When a project has no web UI, the terminal is the product. The skill records it with the macOS
built-in `screencapture -v` instead of Playwright, applies the same pacing and privacy rules, and
still uses Playwright for the LinkedIn step.
