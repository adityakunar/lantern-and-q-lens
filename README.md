# Lantern and Q Lens: one weekly AI news digest, built two ways

Should this job be a workflow or an agent?

More AI news is published each week than one person can read. The two programs in this
repository do the same job: once a week each one reads about 60 blogs, lab sites and
newsletters, picks the dozen or so items most worth one reader's time, and writes a short
digest with a link and a reason for each. They were built in two very different ways, so
that the results can be compared.

- **[Lantern](lantern/) is a workflow.** It is an ordinary Python program that always runs
  the same four steps: collect, filter, score, write. An AI model is called only to score
  each item and to write the text. Code decides everything else. It runs on your own computer.
- **[Q Lens](q-lens/) is an agent.** An AI model is given the list of sources, a description
  of the reader and a spending limit, and then decides for itself how to do the job: which
  articles to open and read in full, what to search the web for, and which items belong
  together. It runs in the cloud as a Claude Managed Agent, Anthropic's hosted service for
  running agents on a schedule.

"Workflow or agent?" is one of the first questions in any project that uses AI models, and
most comparisons are made on toy tasks. This repository answers it for one real task that
repeats every week, with the cost, the time and the results written down.

What you take away:

- **One idea:** a workflow is cheap and predictable; an agent reads more and finds
  different things, and here it cost 5 to 9 times as much.
- **Two small programs to read:** [lantern/](lantern/) (about 2,100 lines of Python with
  tests) and [q-lens/](q-lens/) (a few pages of instructions and one helper script).
- **One free check:** `uv run pytest` in `lantern/`, with no internet and no AI model.
- **One record:** [benchmark/](benchmark/), the cost, time and contents of each week's two
  notes.

This page is for developers deciding between a workflow and an agent, for people starting
with Claude Managed Agents (Q Lens is a complete working example), and for anyone who wants
their own weekly digest from their own list of sources.

Where to look:

| I want to | Look at |
|---|---|
| see what the two notes look like | [examples/2026-11-15/](examples/2026-11-15/): one week's notes from both programs |
| compare cost, time and contents | [What three weeks show](#what-three-weeks-show), then [benchmark/](benchmark/) |
| run Lantern, for free at first | [Try it](#try-it), then [lantern/README.md](lantern/README.md) |
| run Q Lens in my Anthropic account | [q-lens/README.md](q-lens/README.md) |
| know where the output goes | [Where the output goes](#where-the-output-goes) |
| read the design | [lantern/docs/design.md](lantern/docs/design.md) and Q Lens's [weekly instructions](q-lens/skills/curate-weekly/SKILL.md) |

| Word | Meaning here |
|---|---|
| **workflow** | A program whose steps are fixed in code; the model fills in parts of them |
| **agent** | A program where the model decides the steps itself, within limits it is given |
| **note** | The weekly digest. Both programs write it as a Markdown file |
| **source** | A website the programs read each week: a blog feed or a page that lists posts |
| **item** | One article, post or release announcement from a source |
| **judge** | To have the model give an item a score from 0 to 10 for this reader |
| **pick** | An item that made it into the note |
| **story** and **quick link** | The two sections of the note: a story gets a paragraph, a quick link gets one line |
| **token** | The unit AI models are billed in, roughly three quarters of a word |
| **taste file** | `lantern/taste.yaml`: what the reader is working on, and a list of traits that add or remove points, such as "written by the people who did the work" (+1) or "mainly sells a product" (-3) |
| **primary source** | The original announcement or paper, as opposed to an article about it |
| **vault** | The folder the notes are saved to: any folder, or a vault of the note-taking app Obsidian |

API keys stay in the macOS Keychain, the system's password store, and never in files. The
agent's sandbox can reach only a fixed list of websites. [SECURITY.md](SECURITY.md) gives the
details and how to report a problem.

## What three weeks show

Both programs wrote the note for the 7 days up to 2 November, 9 November and 15 November
2026. Each week both read nearly the same sources and used the same taste file. The third run was the
live test of this published repository, started from a fresh copy with the example taste
file shipped here, and with an empty memory for Q Lens.

| | Lantern (workflow) | Q Lens (agent) |
|---|---:|---:|
| Cost of one note | $0.29 to $0.40 | $2.11 to $2.56 |
| Time to produce it | about 3 to 4 minutes | about 4 to 5 minutes |
| Text the model read | 62,000 to 73,000 tokens | 2.0 to 3.0 million tokens |
| Items in the note (9 and 15 Nov) | 12 | 14 |

Costs are what the model provider charges at its published prices.

1. **The agent costs 5 to 9 times as much.** It reads whole articles, where the workflow
   reads only a title and the first 500 characters of each. Part of the gap is also the
   model: Q Lens ran on Claude Opus 5.5 and Lantern on Claude Sonnet 5.5, a smaller and
   cheaper model.
2. **The two notes overlap only in part.** 2, 3 and 6 items were in both notes. Each program
   found things the other missed, which is a bigger difference than the cost.
3. **The workflow missed big announcements every week.** It left out Google DeepMind's
   Gemini 4 Carbon in the first week, three new models in the second, and Gemini 4
   Hydrogen, Claude Fable 5.2 and Inkling 2 Small in the third. The agent included the
   models of the second and third weeks. The cause is clearest in the first week: Lantern
   scores each item from 0 to 10 using only the title and opening lines, so many items get
   the top score, and the note has only 12 places. 21 items scored 10, so Gemini 4 Carbon,
   which scored 8, had no chance. The agent opens an
   article when it is unsure and makes sure no single topic fills the note.
4. **The agent missed practical engineering articles.** Lantern gives extra points to
   articles that are useful for what the reader is building. It picked hands-on articles,
   such as one on memory for AI agents and one on agents stuck in endless retries, that Q
   Lens passed over.
5. **Both carry on when a source breaks.** In the third week both found the same dead feed
   and listed it in the note. Q Lens also searched the broken sites directly and suggested
   fixes for a person to approve.

Three weeks are an early signal, not a verdict. The details for each week are in
[benchmark/](benchmark/).

## Try it

Lantern is made for a Mac and needs [uv](https://docs.astral.sh/uv/), a tool that installs
Python and the project's dependencies. Everything in this first block is free: no model is
called.

```bash
git clone https://github.com/adityakunar/lantern-and-q-lens.git
cd lantern-and-q-lens/lantern
uv sync --locked
uv run pytest                                       # the tests: no internet, no model
cp lantern.example.yaml lantern.yaml                # settings that keep everything in output/
mkdir -p output/notes
uv run lantern check ai                             # check the settings, try every source once
uv run lantern run ai-weekly --dry-run --no-model   # print a note ranked by keywords, save nothing
uv run lantern run ai-weekly --no-model             # save that note to output/notes/
```

The next two call the model, and each costs about as much as one note:

```bash
uv run lantern run ai-weekly --dry-run   # the full note, printed and not saved
uv run lantern run ai-weekly             # the full note, saved
```

A dry run skips only the saving: the model still judges every item and writes the note. In
the live test it took about 225 seconds and cost about $0.40 with Claude Sonnet 5.5. The
model can be a hosted one or one running on your Mac, which costs nothing per run.
[lantern/README.md](lantern/README.md) shows how to set either up.

Q Lens needs an Anthropic account with access to Managed Agents and Anthropic's `ant`
command-line tool. Setting it up creates resources in your account that cost money when
they run; each run is limited to $5. See [q-lens/README.md](q-lens/README.md).

## Where the output goes

Both programs write the note as a Markdown file on your computer. Nothing either program
produces is committed to this repository.

- **Lantern**, with the example settings, writes everything into `lantern/output/`, which git
  ignores: each week's note under `output/notes/Lantern/AI news/Lantern/`, and its library,
  a SQLite file with every item, every decision and its reason, and every run. Point the
  settings at your Obsidian vault and the notes go there instead.
- **Q Lens** saves the note in its cloud run, and keeps a few memory files in your Anthropic
  account between runs. `q-lens/fetch-latest-note.sh <folder>` downloads the note to
  `<folder>/Lantern/AI news/Agent/` and adds the run's cost and time to it.
- Fetch Q Lens's note into `lantern/output/notes` and `uv run lantern benchmark` puts the two
  side by side in one table.

Each note starts with a block of properties that records its own run: sources, items, time,
tokens and cost. The details, with file trees, are in
[lantern/README.md](lantern/README.md#where-the-output-goes) and
[q-lens/README.md](q-lens/README.md#where-the-output-goes).
[examples/](examples/) holds copies of one week's notes, and
[benchmark/README.md](benchmark/README.md) is a summary written by hand.

## Small enough to follow

```text
lantern/     the workflow: code, tests, the list of sources, settings and its design
q-lens/      the agent: its instructions, schedule, sandbox settings and memory
benchmark/   cost, time and contents of each week's two notes, written up by hand
examples/    the notes both programs wrote on 15 November 2026
```

Start with [lantern/src/lantern/run.py](lantern/src/lantern/run.py): the steps of one run
in one function. On the agent side, start with the
[instructions it follows each week](q-lens/skills/curate-weekly/SKILL.md).

The taste file is shared by both programs. The one published here is a made-up example.
Replace it with your own, and `q-lens/sync-shared.sh` copies it to the agent.

## What this version does not claim

This is version 1 of both programs, published unchanged so the numbers above can be
reproduced. The limits below are known and kept on purpose, so that the comparison measures
the programs as they ran:

- Lantern caps scores at 10, so many items tie at the top and the places in the note are
  filled arbitrarily among them.
- Lantern has no rule that keeps a major release from a leading AI lab in the note.
- Lantern treats two versions of the same software release as two separate items.
- Lantern does not remember earlier weeks, so it cannot say "this continues last week's
  story". Q Lens can.
- Q Lens has no automated tests. Its only checks are that its list of allowed websites and
  its shared files are up to date.
- Both assume a Mac: for running on a schedule and for storing the API key in the macOS
  Keychain.
- The comparison does not separate the two designs from the two models. Q Lens used a larger
  model than Lantern, so not all of the cost gap comes from being an agent.

## What comes next

A redesign of both programs is planned, and it will address the limits above. Until then,
each new week that both programs run adds a section to [benchmark/](benchmark/).

[MIT licence](LICENSE).
