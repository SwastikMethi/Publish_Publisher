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

If anything unsafe appears anywhere in a video, do not upload it. Re-record the flow cleanly.
Do not attempt to blur, crop, or trim around the problem.

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
2. Each screenshot reviewed by eye.
3. Full video reviewed, including transitions.
4. No file from the never-open list was read.
5. Nothing uncertain remains. If something does, it goes to the user before LinkedIn opens.
