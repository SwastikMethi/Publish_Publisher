# Security and privacy review

Read this before opening LinkedIn. Everything that will be posted is public and permanent.
Review the post text, every screenshot, and the whole video.

## The rule

If you are not sure something is safe to post publicly, do not proceed automatically.
Stop, describe the concern to the user with the file and location, and let them decide.

## What to look for

Secrets and credentials:

- API keys, in any format: `sk-...`, `AKIA...`, `ghp_...`, `xoxb-...`, long hex or base64 strings
  next to words like key, token, secret, password
- JWTs (three base64 segments separated by dots)
- Authorization headers, bearer tokens, session cookies
- Database connection strings, `postgres://`, `mongodb://`, `redis://` with credentials
- Passwords, even test passwords, and password fields with visible values
- Private keys, `.pem` content, SSH keys

Private infrastructure:

- Internal hostnames and company domains
- Private IP addresses, VPN addresses, staging or internal URLs
- Cloud account IDs, project IDs, bucket names
- Localhost URLs with a port are usually fine, but prefer viewport captures that hide the
  address bar entirely

People and data:

- Real email addresses, phone numbers, full names other than the user's own
- Customer, client, or employer data, including realistic-looking sample data copied from work
- Profile pictures and account names in app headers
- Calendar entries, chat messages, notifications
- Private project or codename references from an employer

Repository-derived information:

- Anything read from a file the user did not intend to publish, for example a private README
  section, an internal ticket number, a colleague's name in a commit message
- Claims about a company's systems or performance

## Where to look

Post text:

- Every proper noun. Is it a public product or an internal name?
- Every number. Is it grounded in the repository or user input?
- Every URL.

Screenshots:

- Open each one with the Read tool. Look at the header, footer, sidebar, and any table cells,
  not only the feature in focus.
- Check browser chrome if it was captured: tabs, bookmarks, extensions, the address bar.

Video, which is higher risk because content appears briefly:

- Watch the complete recording, every frame range, not the first and last few seconds.
- Transitions between screens, where a previous page's content lingers.
- Every visible URL during navigation.
- Notifications and OS popups that appeared during recording.
- Account or user information in headers on any screen.
- Input fields and what was typed into them.
- Temporary error messages, toasts, and console-style output.
- Loading states that briefly show raw JSON or request details.

Web-app footage that shows anything unsafe is re-recorded cleanly. Terminal footage is
different: the agent's own output prints home paths, usernames, and repo URLs that no prompt
setting can hide, so terminal scenes are always run through `scripts/redact.py`, and the
rendered video is OCR-scanned before it counts as reviewed (see `references/video-guidelines.md`,
Pass 3). The scan is the check, not a substitute for it: the video is clean when a scan of the
final file reports `0 boxes`, and not before.

## OCR scan

`scripts/redact.py` samples frames, runs tesseract, and matches every word against patterns
for home paths, tilde paths, email addresses, `github.com/` and `owner/repo.git` references,
token shapes (`sk-`, `ghp_`, `xoxb-`, `AKIA`, JWTs), IPv4 addresses, and the login name you
pass with `--user`. Use it on:

- every terminal scene's source window before rendering (produces the blur boxes)
- the rendered `demo.mp4`, at 5 fps, after rendering (must report `0 boxes`; patch and rescan
  until it does)
- every screenshot (a `.png` input is treated as a single frame; `--start`/`--end` are
  required by the parser but ignored):
  `python3 <skill dir>/scripts/redact.py --input output/media/screenshots/01-main.png --start 0 --end 1 --user $(whoami) --out /tmp/pp-shot.json`

A screenshot that produces a box is retaken with the offending content off screen. Blur is
for footage only; a blurred still looks like it is hiding something.

The scan misses things OCR cannot read (tiny text, text under a dialog, a profile picture)
and matches only the patterns listed. It is one layer. Eyes on every still and every contact
sheet remain the other.

## Never open

Do not read or display these to check them, and do not let them appear in media:

```
.env, .env.*, *.local
browser cookie stores and authentication storage
Playwright storage-state files: *auth*.yml, *auth*.json, storage-state*.json, state.json
~/.ssh, *.pem, *.key
credential files: ~/.aws/credentials, ~/.netrc, ~/.docker/config.json, keychains
personal documents: resumes, CVs, candidate profiles, cover letters, anything under Documents/
the parent directory of a Git worktree, and sibling folders of the repo
```

If the app needs a value from one of these to run, ask the user to start it themselves or to
confirm the value is already set. Do not cat the file to find out.

Terminal captures add two checks: no `user@hostname` in the prompt, and no absolute paths that
reveal the home directory or an employer's naming scheme. Set a plain prompt before capturing.

## Before LinkedIn

Confirm all of these in one short checklist in your response, with a yes or a specific concern
for each:

1. Post text reviewed: no secrets, no private names, every claim grounded.
2. Each screenshot reviewed by eye and OCR-scanned: 0 boxes each.
3. Final `demo.mp4` OCR-scanned at 5 fps: 0 boxes (quote the line), and every contact sheet
   of the final file read by eye.
4. Only the rendered `demo.mp4` will be uploaded; no raw recording leaves `output/media/`.
5. No file from the never-open list was read.
6. Nothing uncertain remains. If something does, it goes to the user before LinkedIn opens.
