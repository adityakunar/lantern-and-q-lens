# Lantern and Q Lens: one weekly AI news digest, built two ways

More AI news is published each week than one person can read. The two programs in this
repository do the same job: every Monday each one reads about 60 blogs, lab sites and
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

"Should this be a workflow or an agent?" is one of the first questions in any project that
uses AI models, and most comparisons are made on toy tasks. This repository answers it for one
real task that repeats every week, with the cost, the time and the results written down.

## What the comparison shows so far

Both programs wrote the digest on Monday 2 November and Monday 9 November 2026, each time
covering the 7 days before. They read nearly the same sources and used the same description
of the reader.

| | Lantern (workflow) | Q Lens (agent) |
|---|---:|---:|
| Cost of one digest | $0.29 to $0.32 | $2.35 to $2.56 |
| Time to produce it | about 3 minutes | about 4.5 to 5 minutes |
| Text the model had to read (9 Nov) | about 62,000 tokens | about 3 million tokens |
| Items in the digest (9 Nov) | 12 | 14 |
| Items that appeared in both digests (9 Nov) | 3 | 3 |

A token is the unit AI models are billed in, roughly three quarters of a word. Costs are
what the model provider charges at its published prices.

What stands out:

1. **The agent costs about 8 times more.** It reads whole articles, where the workflow reads
   only a title and the first 500 characters of each. Part of the gap is also the model: Q
   Lens ran on Claude Opus 5.5 and Lantern on Claude Sonnet 5.5, a smaller and cheaper
   model.
2. **The two digests are mostly different.** Only 3 items were in both. Each program found
   things the other missed, which is a bigger difference than the cost.
3. **The workflow missed the week's big announcements.** On 9 November it left out four
   major items, three of them new model releases. The cause is how it picks. It scores each
   item from 0 to 10 using only the title and opening lines, so many items get the top score.
   The digest has only 12 places. The week before, 21 items scored 10, so a major model
   release that scored 8 had no chance. The agent opens an article when it is unsure and makes sure no
   single topic fills the digest, so it kept the big releases.
4. **The agent missed practical engineering articles.** Lantern gives extra points to
   articles that are useful for what the reader is building, and picked a hands-on article
   about memory for AI agents that Q Lens passed over.

Two weeks are an early signal, not a verdict. The details for each week are in
[benchmark/](benchmark/).

## Who this is for

- **Developers deciding between a workflow and an agent.** Both sides are small enough to
  read in an evening: about 2,100 lines of Python with tests on one side, and a few pages of
  instructions with one helper script on the other.
- **People starting with Claude Managed Agents.** Q Lens is a complete working example: the
  agent, its instructions, a weekly schedule with a spending limit, memory that lasts from
  one week to the next, and a sandbox that can reach only a fixed list of websites.
- **People who want their own weekly digest.** Both programs run on your own list of sources
  and your own description of what you care about.

## Words used in this repository

| Word | Meaning here |
|---|---|
| **note** | The weekly digest. Both programs write it as a Markdown file |
| **source** | A website the programs read each week: a blog feed or a page that lists posts |
| **item** | One article, post or release announcement from a source |
| **judge** | To have the model give an item a score from 0 to 10 for this reader |
| **pick** | An item that made it into the note |
| **story** and **quick link** | The two sections of the note: a story gets a paragraph, a quick link gets one line |
| **taste file** | `lantern/taste.yaml`: what the reader is working on, and a list of traits that add or remove points, such as "written by the people who did the work" (+1) or "mainly sells a product" (-3) |
| **primary source** | The original announcement or paper, as opposed to an article about it |
| **vault** | A folder of Markdown notes used with the note-taking app Obsidian. Both programs save the note there |

## Known limits of this version

This is version 1 of both programs, published unchanged so the numbers above can be
reproduced. A redesign is planned, and it will address these:

- Lantern caps scores at 10, so many items tie at the top and the places in the note are
  filled arbitrarily among them.
- Lantern has no rule that keeps a major release from a leading AI lab in the note.
- Lantern treats two versions of the same software release as two separate items.
- Lantern does not remember earlier weeks, so it cannot say "this continues last week's
  story". Q Lens can.
- Q Lens has no automated tests. Its only checks are that its list of allowed websites and
  its shared files are up to date.
- Both assume a Mac: for running on a schedule and for storing the API key in the macOS
  Keychain, the system's password store.

## What is in each folder

```
lantern/     the workflow: code, tests, the list of sources, settings and the written design
q-lens/      the agent: its instructions, schedule, sandbox settings and memory
benchmark/   cost, time and overlap for each week the two were compared
```

The taste file is shared by both programs. The one published here is a made-up example.
Replace it with your own, and `q-lens/sync-shared.sh` copies it to the agent.

## Try it

Lantern needs a Mac and [uv](https://docs.astral.sh/uv/), a tool that installs Python and
the project's dependencies:

```sh
cd lantern
uv sync
uv run pytest
cp lantern.example.yaml ~/.config/lantern.yaml
uv run lantern check ai
uv run lantern run ai-weekly --dry-run
```

`uv run pytest` runs the tests, which need no internet and no AI model. The last two
commands try every source once and then show what a note would contain without writing it.
Writing a real note needs an AI model, either one running on your Mac or a hosted one. See
[lantern/README.md](lantern/README.md).

Q Lens needs an Anthropic account with access to Managed Agents and Anthropic's `ant`
command-line tool. Setting it up creates resources in your account that cost money when
they run; each run is limited to $5. See [q-lens/README.md](q-lens/README.md).

## Security

API keys stay in the macOS Keychain and never in files. The agent's sandbox can reach only a
fixed list of websites. Details, and how to report a problem, are in [SECURITY.md](SECURITY.md).

## Licence

MIT. See [LICENSE](LICENSE).
