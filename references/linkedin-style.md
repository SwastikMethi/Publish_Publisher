# LinkedIn writing style

Read this before drafting the post, and run the checklist at the end before saving it.

Every post introduces a new project. The reader has never heard of it and will not see a
follow-up. So this is not a progress update, a changelog, a PR description, or a status
report. It is a person telling their network: here is something I got curious about, here is
what I built because of it, here is what it does, and here is the bit that surprised me.

## The whole project is the news

The repository is one day's work, so everything in it is today's work. Never narrate the
commits ("today I split the skill into five", "today I added search history", "the latest
commit moved..."). Describe the project as it stands, as a finished thing someone could try.

Use Git and the diff to find the interesting detail: the decision, the constraint, the
surprise. Then tell that detail as part of the project's design, not as a task you did.
"Every score has to be one of five fixed values, anything else is rejected" is a design
choice. "Today I moved the scoring into Python" is a diary entry.

Do not inventory what is unfinished. No "what's not done:" paragraph, no "on tomorrow's
list", no test counts, no roadmap. If the user is actually stuck and wants help, one clause
inside the closing question is the most it gets ("I'm hitting an error on the upload step,
if anyone has seen it").

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
strings. Name real tools and products (React, Open-Meteo, Codex, Google Opal) because
readers search for those; do not name internals.

## The shape

A post has a spine. Default order, reorder if the story wants it:

```
1. The spark: what you have been curious about or annoyed by lately (one or two lines)

2. What you built, and the project's name if it has one

3. What it does, as input → output, in plain words
   ("dump in a rough idea and some notes, and it maps out the screens and the task list")

4. The moment: the design choice, constraint, or surprise that makes this project
   interesting (this is where the detail from the brief goes)

5. An invitation: a real question aimed at people who build similar things (optional)

6. Day N/30 (only if given)

7. The repository link, on its own line: "Code: https://github.com/<owner>/<repo>"
   (only if the repo has a public remote; read it with `git remote get-url origin`)

8. #tags
```

Paragraphs 1, 3, and 4 carry the post. If paragraph 4 has nothing in it, go back to the
brief and find the detail, or tell the user.

The day number goes at the end by default, on its own line just before the hashtags. The
alternative is a short line right after the spark, but do not do that every post; a
two-word paragraph in the same slot every day reads as a template.

The closing question must be one the user actually wants answered: a real error they are
stuck on, a real choice between tools, a real curiosity about how others do it. That cannot
be read from the repository. If the brief or the user's words do not supply a genuine
question, end on the moment (paragraph 4) and skip the question. Never invent an ask.

## The first line

LinkedIn shows roughly 140–210 characters before "...see more". The first line has to make
someone stop.

- Under 150 characters. Stands alone. A reader who stops there knows the topic.
- No preamble: no greeting, no "Day 2/30." as the opener, no project name first, no
  "Today I built".
- The best openers are personal and specific: what you have been into lately, what set you
  off, or the wow moment itself.
- Openers that fit a new-project post:
  - the rabbit hole: "So I've been diving deep into game UX lately, trying to understand..."
  - the spark: "Saw Llama 4's 10M context window and it got me thinking..."
  - the itch: "Applying for jobs recently, the most hectic part wasn't the interviews. It
    was the repetition."
  - the surprise: "I meant to build a small demo and ended up with a whole pipeline."
  - the belief: "Giving an LLM an entire library is less useful than giving it Google."
- Rotate across posts. Two posts in a row with the same opener shape look templated. The
  post log in `~/.project-publisher/posts/` records each post's shape; check it.

## Connecting to earlier posts

The user is asked at the start whether this post should connect to an earlier one. If they
said no, or said nothing, there is no connection. Do not add "like yesterday", "Day 3 of
this series", or "as I mentioned" on your own; a stranger did not read the earlier post.

If they said yes, they also said how. Keep it to one sentence, in the slot they chose:

- a callback in the spark: "After building a weather dashboard that needed no API key, I
  wanted to see how far 'no backend' could go."
- a contrast: "Yesterday's project was all UI. This one has none."
- built with: "The demo video in this post was recorded by the skill I built on Day 1."

Name the earlier project by what it is, not by its day number alone. "Day 2" means nothing
to a stranger; "the weather dashboard" does.

## The post and the media

The post goes out with an edited video or two to four screenshots. They are read together,
so they share a voice but never describe each other.

- The post does not narrate its attachments. No "see the video below", "screenshots
  attached", "the recording is my terminal while it worked", "watch it search a city". The
  media is right there; the reader can see what it is.
- The post does not depend on the media either. Someone reading with autoplay off, or in a
  notification preview, gets the whole story from the text.
- The video's title card takes its sub-line from the post's "what it does" sentence, and its
  scene captions are written in the same voice as the post: one short plain sentence each,
  present tense, no identifiers. If a caption would not fit in the post, it does not fit on
  the video. Write the post first; the captions come from it.
- Do not write the post around what was easiest to record. If the interesting detail did not
  make it into the footage, it still leads the post; the video shows the product, the post
  carries the idea.

## Voice

- First person, conversational, like a message to a group chat of people you respect.
  Contractions are fine. Casual lives in word choice and rhythm, not in grammar.
- Standard capitalization and punctuation. Every sentence starts with a capital letter and
  ends with a full stop or question mark. Proper nouns capitalized (LinkedIn, Naukri, Excel,
  Python). No run-on sentences joined by commas. This is a professional network and the
  reader will judge the writing before the project.
- Enthusiasm is welcome when it is specific: "honestly blew my mind because the blank-canvas
  paralysis was just gone in seconds" works because it says what was mind-blowing.
  "Excited to share" says nothing.
- Explain the why before the what. People care about a project once they know what you
  were chasing.
- Describe the thing by what happens when you use it, not by its architecture.
- If there is a real question, ask it at the end, to the people who build similar things.
  Not "thoughts?". "Anyone else chaining AI workflows lately? Would love to see what
  you're building."
- Do not exaggerate. A day's build is a day's build. Say it is small if it is small.
- Do not force a lesson. If one showed up, one sentence. Otherwise skip it.

## Formatting for the feed

- Paragraphs of one to three sentences, at most about 300 characters. Blank line between.
- Five to nine paragraphs. 800–1400 characters total including hashtags.
- Plain text. LinkedIn renders no markdown: no headers, backticks, bold, or links in the
  body.
- A short arrow flow or a list is fine when it is the clearest way to show what the thing
  does: "User question → LLM → data router → the right file". At most four items, each
  under 60 characters.
- Zero to three emojis. Use them at the emotional beats (the wow moment, the ask), never as
  bullets and never in the first line.
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
Today I split / added / moved / refactored / fixed
What's not done
See the video / screenshots below
The recording is / the demo shows / attached
On tomorrow's list
Only X for now
The service layer / the adapter / the component
```

Engagement bait: no "agree?", no bare "thoughts?", no "comment X to get the link", no "follow
for more". A specific question to builders is not bait.

AI tells: three adjectives in a row, "It's not X, it's Y", a rhetorical question you then
answer, every paragraph starting the same way, a tidy moral the day did not earn.

Facts: no metrics, user counts, percentages, benchmarks, or test counts unless the user asked
for them. Include the challenge day only if the user gave it. Never invent a day number.

Personal framing is a fact too. Habits ("I open three tabs every morning"), motivations
("I've been diving into game UX lately"), time spent, feelings ("blew my mind"), and
questions the user wants answered come from the user, not the code. The repository can tell
you what the project does and what was hard about it; it cannot tell you why this person
built it or how it felt. If the brief has no spark from the user, ask for one in stage 1
before writing. If the user gives none, open on what the project does instead of inventing
a life.

## The one required ingredient

The moment (paragraph 4 in the spine) needs at least one thing beyond "I built X using Y":

- a design decision and why
- a constraint you put on the system on purpose
- something that surprised you
- a technical problem that showed up and how it was handled
- a tradeoff made on purpose
- an experiment and its result

Find it in the diff, the commits, or the code. Tell it as a property of the project, not as
a task. If the repository truly has none, tell the user before writing rather than padding.

## Good versus bad

Bad, and why:

> applying for jobs recently, the most hectic part wasn't the interviews. it was the
> repetition.
>
> so I'm building AI Job Orient: a set of skills for the Codex coding agent that runs that
> loop for me, while I keep the submit button.
>
> today I split the one big skill into five (a coordinator plus search, match, tailor,
> apply) and moved every decision I don't trust an LLM with into plain Python.
>
> what's not done: only the scoring and tracking layer has tests (20, all green). the
> browser side is still written instructions the agent follows, not code I can test. Codex
> only for now.
>
> Day 2/30.

The spark and the project description are good. Everything else is wrong for the format:
no sentence starts with a capital letter; paragraph three narrates today's commits instead
of describing the project; paragraph four is a status inventory with a test count nobody
asked for; and "Codex only for now" is a roadmap note. A stranger reading this gets a
diary, not a project.

Good, same project, same facts:

> Applying for jobs recently, the most hectic part wasn't the interviews. It was the
> repetition.
>
> Same search on LinkedIn, same search on Naukri, then re-tuning my resume by hand for every
> single posting.
>
> So I built AI Job Orient: a set of skills for the Codex coding agent that runs that loop
> for me, while I keep the submit button.
>
> You give it your master resume and a short profile. It searches LinkedIn and Naukri, scores
> each posting against what's actually in your resume, tailors a copy for the ones worth
> applying to, and logs everything in an Excel tracker. It submits one application at a time,
> only after I approve that one.
>
> Most of the thinking went into what the agent is not allowed to do. It can't invent a
> score: every part must be 0, 0.25, 0.5, 0.75 or 1, and anything else is rejected.
>
> It can't mark a job "Applied" without the confirmation text it saw on screen. And
> yesterday's approval can't submit today's application. Every one of those rules lives in
> plain Python, not in a prompt.
>
> If you've built something that searches jobs or tailors resumes for you, how did you
> approach it? Feel free to argue with my design in the comments 👀
>
> Day 2/30.
>
> #buildinpublic #codex #python #jobsearch #aiagents

A stranger knows what the project is by paragraph three. The five-skill split and the
Python move are still in there, but as a property of the design ("every one of those rules
lives in plain Python"), not as something done today. Nothing about what is unfinished.
Proper sentences throughout.

Where each part came from: the loop the tool runs, the fixed score values, the confirmation
text rule, and the approval rule are all in the code. The opening frustration, the two job
sites the user actually used, and the closing question are the user's, supplied in stage 1.
Without them, the honest version opens on paragraph three and ends on the moment. That is a
weaker post, and it is still the correct one to write.

## Checklist before saving

Run every line. Fix and re-run until all pass.

1. Stranger test: would someone who has never heard of this project know what it is and
   what it does by the second or third paragraph?
2. First line: under 150 characters, stands alone, no day number, greeting, or project name
   first. The day number, if given, is at the end (or, occasionally, a short line after the
   spark), never a stub paragraph in the same slot every post.
3. Grammar: every sentence starts with a capital letter and ends with punctuation. Proper
   nouns capitalized. No comma splices. Read it once as an editor, not as the author.
4. Why before what: does the post say what you were curious about or annoyed by before it
   describes the build?
5. Input → output: is there one plain-words sentence of "you give it X, it gives you Y"?
6. The moment: is there a paragraph about a design choice, constraint, or surprise, told as
   a property of the project rather than a task you did today?
7. No diary: search for "today I", "what's not done", "for now", "next", "tomorrow", test
   counts, and any sentence that describes a commit rather than the project. Remove them.
8. Identifiers: zero field names, function names, storage APIs, query strings, or
   architecture nouns (adapter, service layer, hook, component, coordinator).
9. Ending: either a question the user actually wants answered, or the moment. Then day
   number (if given), then the repository link (if the remote is public, as
   "Code: <url>" on its own line, converted from an SSH remote to https), then hashtags.
   Not the stack, not a moral, not an invented ask, not a status line. Never link a private
   or work repository; if the remote is not on github.com, gitlab.com, or another public
   host, leave the link out and say so.
10. Formatting: paragraphs under about 300 characters, 800–1400 total, 0–3 emojis, 3–6
    hashtags, no markdown, nothing from the banned list.
11. Facts: every claim traces to a file, commit, or the user's words. That includes the
    spark, any time spent, any feeling, and the closing question. Day number only if given.
12. Media: no sentence points at the video or screenshots ("see below", "the recording",
    "attached"). The post reads whole with the media hidden.
13. The file `output/post.md` contains only the post text. No notes, no commentary, no
    instructions to the user, nothing after the hashtags.
