# LinkedIn writing style

Read this before drafting the post, and run the checklist at the end before saving it.

Every post introduces a new project. The reader has never heard of it and will not see a
follow-up. So this is not a progress update, a changelog, or a PR description. It is a
person telling their network: here is something I got curious about, here is what I built
today because of it, here is what it does, and here is the bit that surprised me.

## Who is reading

The feed is mixed. Write for all three at once:

- A recruiter, PM, designer, or founder. They should understand what the project is and
  what it does without any technical background.
- An engineer on a different stack. They should follow every paragraph and pick up the one
  idea that made this project worth building.
- A peer on your stack. They should get one concrete detail they can steal or ask about.

Translate, do not dumb down. Describe what the code does, never how it is written.
"Type a city and it shows current weather and a forecast, no login" beats "the service layer
reshapes the response contract". No field names, function names, storage APIs, or query
strings. Name real tools and products (React, Open-Meteo, Google Opal) because readers
search for those; do not name internals.

## The shape

A post has a spine. Default order, reorder if the story wants it:

```
1. The spark: what you have been curious about or annoyed by lately (one or two lines)

2. What you set out to build, and the project's name if it has one

3. What it actually does, as input → output, in plain words
   ("dump in a rough idea and some notes, and it maps out the screens and the task list")

4. The moment: what surprised you, felt great, or turned out to be the hard part
   (this is where the one interesting detail from the brief goes)

5. What is rough, missing, or broken, said plainly

6. An invitation: a real question aimed at people who build similar things (optional; see
   below)

7. Day N/30 (only if given)

8. #tags
```

Paragraphs 1, 3, and 4 carry the post. If paragraph 4 has nothing in it, go back to the
brief and find the detail, or tell the user.

The day number goes at the end by default, on its own line just before the hashtags. The
alternative is a short line right after the spark, but do not do that every post; a
two-word paragraph in the same slot every day reads as a template.

The closing question must be one the user actually wants answered: a real error they are
stuck on, a real choice between tools, a real curiosity about how others do it. That
cannot be read from the repository. If the brief or the user's words do not supply a
genuine question, end on the honest-state paragraph (5) and skip the question. Never invent
an ask.

## The first line

LinkedIn shows roughly 140–210 characters before "...see more". The first line has to make
someone stop.

- Under 150 characters. Stands alone. A reader who stops there knows the topic.
- No preamble: no greeting, no "Day 2/30." as the opener, no project name first, no
  "Today I built".
- The best openers are personal and specific: what you have been into lately, what set you
  off, or the wow moment itself.
- Openers that fit a new-project post:
  - the rabbit hole: "so I've been diving deep into game UX lately, trying to understand..."
  - the spark: "saw Llama 4's 10M context window and it got me thinking..."
  - the itch: "I open three weather tabs every morning. today I replaced them."
  - the surprise: "I meant to build a small demo and ended up with a whole pipeline."
  - the belief: "giving an LLM an entire library is less useful than giving it Google."
- Rotate across posts. Two posts in a row with the same opener shape look templated.

## Voice

- First person, conversational, like a message to a group chat of people you respect.
  Contractions are fine. Lowercase sentence starts are fine if the user writes that way.
- Enthusiasm is allowed and welcome when it is specific: "honestly blew my mind because the
  blank-canvas paralysis was just gone in seconds" works because it says what was mind-
  blowing. "Excited to share" says nothing.
- Explain the why before the what. People care about a project once they know what you
  were chasing.
- Describe the thing by what happens when you use it, not by its architecture.
- Say what does not work yet. It is the most trusted sentence in the post and it invites
  replies.
- If there is a real question, ask it at the end, to the people who build similar things.
  Not "thoughts?". "Anyone else chaining AI workflows lately? Would love to see what
  you're building." If there is no real question, end on what is not done yet.
- Do not exaggerate. A day's build is a day's build. Say it is small if it is small.
- Do not force a lesson. If one showed up, one sentence. Otherwise skip it.

## Formatting for the feed

- Paragraphs of one to three sentences, at most about 300 characters. Blank line between.
- Six to nine paragraphs. 900–1500 characters total including hashtags.
- Plain text. LinkedIn renders no markdown: no headers, backticks, bold, or links in the
  body.
- A short arrow flow or a list is fine when it is the clearest way to show what the thing
  does: "User question → LLM → data router → the right file". At most four items, each
  under 60 characters.
- Zero to three emojis. Use them the way the user does, at the emotional beats (the wow
  moment, the ask), never as bullets and never in the first line.
- 3–6 hashtags on the last line, CamelCase or lowercase, matching the tools and the theme.
  Always include the theme tag the user uses (for example #buildinpublic) and the main
  product names.
- No "Stack:" line. Mention a tool inline where it matters to the story; leave the rest to
  hashtags.

## Banned

Anywhere in the post:

```
Thrilled to announce
Excited to share
I'm delighted to
Happy to share
Game changer
Revolutionary
Groundbreaking
Cutting-edge
Unlock
Supercharge
Leverage (as a verb)
Seamless / seamlessly
In today's fast-paced world
Let that sink in
Stack:
The latest commit
This PR
The service layer / the adapter / the component
```

Engagement bait: no "agree?", no bare "thoughts?", no "comment X to get the link", no "follow
for more". A specific question to builders is not bait.

AI tells: three adjectives in a row, "It's not X, it's Y", a rhetorical question you then
answer, every paragraph starting the same way, a tidy moral the day did not earn.

Facts: no metrics, user counts, percentages, or benchmarks unless they exist in the repository
or the user supplied them. Include the challenge day only if the user gave it. Never invent
a day number.

Personal framing is a fact too. Habits ("I open three tabs every morning"), motivations
("I've been diving into game UX lately"), time spent ("took an afternoon"), feelings
("blew my mind"), and questions the user wants answered come from the user, not the code.
The repository can tell you what the project does and what was hard about it; it cannot
tell you why this person built it or how it felt. If the brief has no spark from the user,
ask for one in stage 1 before writing. If the user gives none, open on what the project does
instead of inventing a life.

## The one required ingredient

The moment (paragraph 4 in the spine) needs at least one thing beyond "I built X using Y":

- something that surprised you
- a design decision and why
- a technical problem that showed up and how it was handled
- a tradeoff made on purpose
- an experiment and its result
- something that did not work

Find it in the diff, the commits, or the code. If the repository truly has none, tell the user
before writing rather than padding.

## Good versus bad

Bad, and why:

> Day 2/30. My weather dashboard talks to Open-Meteo, but its components still think they are
> talking to OpenWeather.
>
> The pages were written against OpenWeather's response shape: main.temp, weather[0].icon,
> sys.country. The service layer now geocodes the city name, calls Open-Meteo (no API key
> needed), and reshapes each response into that older contract before the UI sees it.
>
> The latest commit added search history. A small hook keeps the last 20 searches in
> sessionStorage, moves a repeated city back to the top, and pushes a ?city= entry onto the
> browser history for every search.
>
> Stack: React, React Router, Axios, Vite, plain CSS with variables.

This reads as an update to people already following the project. Nobody outside the repo
learns what the app is or why it exists. The day number eats the hook. Eight code
identifiers. It ends on the stack. No question, no invitation.

Good, same project:

> I open three weather tabs every morning. today I finally replaced them with my own
> dashboard.
>
> it's a small React app: type a city, get the current conditions and a forecast, with icons
> that actually match the sky outside. no login, no backend, no API key. everything lives in
> your browser.
>
> the fun part was the data. I started on OpenWeather, then switched to Open-Meteo because it
> needs no key. instead of rewriting every screen for the new format, I put one translation
> layer in between and the rest of the app never noticed the provider changed. that swap took
> an afternoon instead of a week and honestly felt great 🙌
>
> what's not done: pressure and visibility are placeholders for now (every city says 1013 hPa
> 😅) and the back button is half wired. both on tomorrow's list.
>
> if you've built on Open-Meteo or have a favourite free weather API, I'd love to hear what
> you went with 👀
>
> Day 2/30.
>
> #react #buildinpublic #webdev #openmeteo

Same facts from the repository. A stranger knows what the app is by paragraph two. The
interesting detail (the provider swap) is told as a moment, not an architecture note. It
admits what is broken and ends by asking people in.

Where each part came from, because this matters: the app's behaviour, the provider swap,
the placeholders, and the half-wired back button are all in the code and commits. The
opening habit ("three weather tabs every morning"), the timeline ("an afternoon instead of
a week"), the feeling, and the closing question are the user's, supplied in stage 1. Without
them, the honest version of this post opens on paragraph two and ends on "both on
tomorrow's list." That is a weaker post, and it is still the correct one to write.

## Checklist before saving

Run every line. Fix and re-run until all pass.

1. Stranger test: would someone who has never heard of this project know what it is and
   what it does by the second or third paragraph?
2. First line: under 150 characters, stands alone, no day number, greeting, or project name
   first. The day number, if given, is at the end (or, occasionally, a short line after the
   spark), never a stub paragraph in the same slot every post.
3. Why before what: does the post say what you were curious about or annoyed by before it
   describes the build?
4. Input → output: is there one plain-words sentence of "you give it X, it gives you Y"?
5. The moment: is there a paragraph about what surprised you or was hard, told as a story
   rather than a spec?
6. Identifiers: zero field names, function names, storage APIs, query strings, or
   architecture nouns (adapter, service layer, hook, component).
7. Honest state: does it say what is missing or broken?
8. Ending: either a question the user actually wants answered, or the honest-state
   paragraph. Then day number (if given), then hashtags. Not the stack, not a moral, not an
   invented ask.
9. Formatting: paragraphs under about 300 characters, 900–1500 total, 0–3 emojis, 3–6
   hashtags, no markdown, nothing from the banned list.
10. Facts: every claim traces to a file, commit, or the user's words. That includes the
    spark, any time spent, any feeling, and the closing question. Day number only if given.
11. The file `output/post.md` contains only the post text. No notes, no commentary, no
    instructions to the user, nothing after the hashtags.