# LinkedIn writing style

Read this before drafting the post. The goal is a post that sounds like a
developer explaining something they actually built, to other developers.

## Voice

- Write like you are telling a colleague what you did today. First person, plain English.
- Short paragraphs: one to three sentences each. One blank line between them.
- Technical but accessible. Name the real tools and decisions. Do not explain what React is.
- Concrete beats abstract. "It groups similar stack traces and suggests a root cause" beats "it uses AI to improve debugging".
- Say what the project does not do yet, if that is honest and interesting.
- Do not force a lesson. If nothing was learned, do not invent one.
- Do not exaggerate the project's importance. A day's build is a day's build.

## Hard limits

- 900–1600 characters is the target. Quality over length; a tight 700 beats a padded 1600.
- At most 3 emojis, and zero is fine.
- 2–4 hashtags, at the end, lowercase or CamelCase, relevant to the actual stack or theme.
- No engagement bait: no "agree?", no "thoughts?", no "comment X to get the link", no "follow for more".
- No metrics, user counts, percentages, or benchmarks unless they exist in the repository or the user supplied them.
- Include the challenge day only if the user gave it. Never invent a day number.

## Banned openers and phrases

Never start with, or use anywhere:

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
```

Also avoid the AI tells: three-item lists of adjectives, "It's not X, it's Y" pivots, a
rhetorical question followed by its own answer, and paragraphs that all start the same way.

## The one required ingredient

Every post must contain at least one detail beyond "I built X using Y":

- a design decision and why
- a technical problem that showed up and how it was handled
- a tradeoff that was made on purpose
- an experiment and its result
- a workflow that turned out to be interesting
- something that did not work

Find it in the diff, the commits, or the code. If the repository truly has none, tell the user
before writing rather than padding.

## Angles

Pick the angle that fits this repository. Do not reuse last post's angle by default.

**Builder story.** "Day 4/30. Today I built a ..." Open with the day and the thing.
Best when the project is self-explanatory and the interesting part is the pace or the stack.

**Problem → solution.** Open with the annoyance. "Every time I ... I had to ..." Then the build.
Best when the project exists because of a real friction the reader will recognise.

**Experiment.** "I wanted to see if ... would work." Then what happened, including if it half-worked.
Best for spikes, prototypes, and things that surprised you.

**Technical discovery.** Open with the thing you learned, then how the project led you to it.
Best when a library, API, or tool behaved in an unexpected way.

**Engineering challenge.** Open on the hard part: a tricky bug, a race, an API limit, a data shape.
Best when the diff shows a real fight and a clean fix.

**Behind the scenes.** Open on a design choice, not the product. "I decided not to add a database."
Best when the product is modest but the reasoning is worth sharing.

## Default shape

Use this when no angle suggests a better order. Reorder freely.

```
Hook (one line, no preamble)

Why I built it / what I wanted to test

What it does (two or three sentences)

How it works (the stack, the flow, in plain words)

The interesting detail (see above)

What I learned or what is next

Day X/30 (only if given)

#tag1 #tag2 #tag3
```

## Good versus bad

Bad:

> Excited to share my latest project! 🚀 I built an AI-powered weather dashboard that
> leverages cutting-edge APIs to deliver seamless real-time insights. Game changer for
> anyone who checks the weather! #AI #Innovation #Tech #Weather #Coding #100DaysOfCode

Good:

> I rebuilt my weather dashboard's history view today, and the interesting part was not the UI.
>
> The free tier of the API I use only returns hourly data for the last 24 hours, so a
> seven-day chart meant caching each day's response in localStorage and stitching them
> together on load. It works, but the first week the chart is mostly empty. I decided
> that was fine for a personal tool.
>
> Day 7/30.
>
> #react #buildinpublic #webdev
