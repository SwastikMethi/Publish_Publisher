#!/usr/bin/env bash
# Installs the Project Publisher skill for Claude Code and/or Codex, and registers
# the Playwright MCP server each of them needs for screenshots, video, and LinkedIn.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
skill_name="project-publisher"

profile_dir="$HOME/.playwright-mcp/project-publisher"
output_dir="$HOME/.playwright-mcp/output"
playwright_cmd=(npx @playwright/mcp@latest --caps=devtools --user-data-dir "$profile_dir" --output-dir "$output_dir")

targets=()
skip_mcp=false
force=false

usage() {
  cat <<'EOF'
Usage: ./install.sh [--claude] [--codex] [--skip-mcp] [--force]

Symlinks this repository into the skills directory of each selected agent and
registers a user-scoped Playwright MCP server with video recording enabled.
With no target flag, installs for every agent whose CLI is on PATH.

Options:
  --claude     Install for Claude Code (~/.claude/skills)
  --codex      Install for Codex ($CODEX_HOME/skills or ~/.codex/skills)
  --skip-mcp   Symlink the skill only; leave MCP configuration untouched
  --force      Replace an existing "playwright" MCP server entry without asking
  -h, --help   Show this help
EOF
}

while (($#)); do
  case "$1" in
    --claude) targets+=(claude); shift ;;
    --codex) targets+=(codex); shift ;;
    --skip-mcp) skip_mcp=true; shift ;;
    --force) force=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -f "$script_dir/SKILL.md" ]] || { echo "No SKILL.md next to this script; run it from the repository." >&2; exit 1; }

if ((${#targets[@]} == 0)); then
  command -v claude >/dev/null && targets+=(claude)
  command -v codex >/dev/null && targets+=(codex)
  ((${#targets[@]} > 0)) || { echo "Neither claude nor codex is on PATH. Pass --claude or --codex explicitly." >&2; exit 1; }
fi

# link_skill DEST_DIR: symlink the repo as DEST_DIR/project-publisher, or leave a
# correct existing link alone.
link_skill() {
  local dest="$1" link="$1/$skill_name"
  mkdir -p "$dest"
  if [[ -L "$link" && "$(readlink "$link")" == "$script_dir" ]]; then
    echo "  skill: already linked at $link"
  elif [[ -e "$link" ]]; then
    echo "  skill: $link exists and is not a link to this repository." >&2
    echo "         Move or remove it, then run the installer again." >&2
    return 1
  else
    ln -s "$script_dir" "$link"
    echo "  skill: linked $link"
  fi
}

# confirm_replace AGENT CURRENT: ask before replacing a differing playwright entry.
confirm_replace() {
  local agent="$1" current="$2"
  echo "  mcp:   $agent already has a playwright server:" >&2
  echo "         $current" >&2
  if [[ "$force" == true ]]; then
    echo "         replacing (--force)" >&2
    return 0
  fi
  if [[ ! -t 0 ]]; then
    echo "         Not a terminal, so not replacing. Re-run with --force to replace, or --skip-mcp to leave it." >&2
    return 1
  fi
  read -r -p "         Replace it with the Project Publisher configuration? [y/N] " answer
  [[ "$answer" =~ ^[Yy]$ ]]
}

install_claude() {
  echo "Claude Code"
  link_skill "$HOME/.claude/skills"
  [[ "$skip_mcp" == true ]] && return 0
  command -v claude >/dev/null || { echo "  mcp:   claude CLI not found; skipping MCP registration" >&2; return 0; }

  local existing
  if existing="$(claude mcp get playwright 2>/dev/null)"; then
    if grep -q -- '--caps=devtools' <<<"$existing" && grep -q -- "$profile_dir" <<<"$existing"; then
      echo "  mcp:   playwright already registered with video enabled"
      return 0
    fi
    confirm_replace "Claude Code" "$(grep -E '^\s*(Args|Command):' <<<"$existing" | tr -s ' ' | tr '\n' ' ')" || return 0
    claude mcp remove playwright --scope user >/dev/null 2>&1 || claude mcp remove playwright >/dev/null 2>&1 || true
  fi
  claude mcp add --scope user playwright -- "${playwright_cmd[@]}" >/dev/null
  echo "  mcp:   registered playwright (user scope, --caps=devtools)"
}

install_codex() {
  echo "Codex"
  link_skill "${CODEX_HOME:-$HOME/.codex}/skills"
  [[ "$skip_mcp" == true ]] && return 0
  command -v codex >/dev/null || { echo "  mcp:   codex CLI not found; skipping MCP registration" >&2; return 0; }

  local existing
  if existing="$(codex mcp get playwright 2>/dev/null)"; then
    if grep -q -- '--caps=devtools' <<<"$existing" && grep -q -- "$profile_dir" <<<"$existing"; then
      echo "  mcp:   playwright already registered with video enabled"
      return 0
    fi
    confirm_replace "Codex" "$(grep -iE 'args|command' <<<"$existing" | tr -s ' ' | tr '\n' ' ')" || return 0
    codex mcp remove playwright >/dev/null 2>&1 || true
  fi
  codex mcp add playwright -- "${playwright_cmd[@]}" >/dev/null
  echo "  mcp:   registered playwright (--caps=devtools)"
}

# check_media_tools: the video edit needs ffmpeg with drawtext, ffprobe, and tesseract.
# Homebrew's plain ffmpeg formula is built without drawtext; ffmpeg-full has it but is
# keg-only, so it must be put on PATH by hand.
check_media_tools() {
  echo "Media tools"
  local missing=()
  local full=/opt/homebrew/opt/ffmpeg-full/bin
  command -v tesseract >/dev/null || missing+=(tesseract)
  # Buffer the filter list first: with pipefail on, grep -q closing the pipe early would
  # make ffmpeg exit 141 and fail the whole check even when drawtext is present.
  has_drawtext() { local f; f=$("$1" -hide_banner -filters 2>/dev/null || true); grep -qE '^ *[A-Z.]+ +drawtext ' <<<"$f"; }
  if command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null && has_drawtext ffmpeg; then
    echo "  ffmpeg: ok (drawtext present)"
  elif [[ -x "$full/ffmpeg" ]] && has_drawtext "$full/ffmpeg"; then
    echo "  ffmpeg: ffmpeg-full is installed but not first on PATH. Add this to your shell profile:" >&2
    echo "          export PATH=$full:\$PATH" >&2
  else
    missing+=(ffmpeg-full)
  fi
  if ((${#missing[@]} > 0)); then
    echo "  missing: ${missing[*]}. Install with:" >&2
    echo "          brew install ${missing[*]}" >&2
    [[ " ${missing[*]} " == *" ffmpeg-full "* ]] && echo "          export PATH=$full:\$PATH" >&2
    echo "  Without these the skill still runs, but posts get screenshots only, no video." >&2
  else
    echo "  tesseract: ok"
  fi
}

mkdir -p "$profile_dir" "$output_dir" "$HOME/.project-publisher/posts"

check_media_tools

for target in "${targets[@]}"; do
  case "$target" in
    claude) install_claude ;;
    codex) install_codex ;;
  esac
done

cat <<EOF

Done. Start a new session in each agent so the skill and MCP server load.
Post records will be kept in ~/.project-publisher/posts/.
The first LinkedIn visit asks you to log in once in the Playwright browser window.
EOF
