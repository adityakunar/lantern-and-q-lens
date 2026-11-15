# Lantern

Lantern reads about 60 AI blogs, lab sites and newsletters once a week and writes you a short
note: the dozen items most worth your time, each with a link and a reason. It is a
**workflow**: an ordinary Python program that always runs the same steps, and asks an AI
model only to score items and to write the text.

This is version 1, kept unchanged so the published results can be repeated. It is one half of
a comparison: the same note is also written by an agent, [Q Lens](../q-lens/). The results
and the known limits are in the [top-level README](../README.md).

Where to look:

| I want to | Look at |
|---|---|
| try it without a model, for free | [Quick start](#quick-start-free-no-model) below |
| see a note it wrote | [examples/2026-11-15/lantern.md](../examples/2026-11-15/lantern.md) |
| know where its files go | [Where the output goes](#where-the-output-goes) |
| change the sources or the reader profile | [Change what you get](#change-what-you-get) |
| read how it is built | [docs/design.md](docs/design.md) |

| Word | Meaning here |
|---|---|
| **note** | The weekly digest, a Markdown file |
| **source** | A website Lantern reads: a blog feed or a page that lists posts |
| **interest** | A list of sources and themes, such as `interests/ai.yaml` |
| **recipe** | How one note is made from an interest: how many days, how many items, where it goes (`recipes/ai-weekly.yaml`) |
| **judge** | To have the model give an item a score from 0 to 10 for this reader |
| **library** | Lantern's memory: one SQLite database file with every item, decision and run |
| **vault** | The folder notes are written to. It can be any folder, or a vault of the note-taking app Obsidian |

## How it works

```text
sources ──collect──▶ library ──filter──▶ judge ──▶ write ──▶ note
 (feeds, pages)     (SQLite)  (rules)    (model)   (model)
```

1. **Collect** every source in the interest (`interests/ai.yaml`: 53 feeds and 11 pages
   without a feed). A source that fails is listed in the note and the run carries on.
2. **Filter** with plain rules: the week's window, nothing you were already shown, duplicates,
   sponsored posts. The rest is ordered by theme keywords and recency (at most 300 go on).
3. **Judge**: the model scores each item from 0 to 10 for you, with a one-line reason.
4. **Write**: the model writes the note (a 30-second summary, up to 6 stories, quick links).
   Lantern checks that every link appears exactly once and nothing is invented, and asks for
   one fix if needed. Without a model, you get a plainer note ranked by keywords, marked as
   such.

Every decision is stored with its reason, so you can ask about any link later with
`uv run lantern why <link>`.

## Quick start: free, no model

You need [uv](https://docs.astral.sh/uv/), a tool that installs Python and the project's
dependencies. Lantern is made for a Mac (the schedule and the key storage use macOS). Run
everything from this `lantern/` folder:

```bash
uv sync --locked
uv run pytest                          # the tests: no internet, no model
cp lantern.example.yaml lantern.yaml   # your settings; git ignores this file
mkdir -p output/notes                  # notes and the library go here
uv run lantern check ai                # check the settings and try every source once
uv run lantern run ai-weekly --dry-run --no-model   # print a keyword-ranked note, save nothing
uv run lantern run ai-weekly --no-model             # save it, and record it in the library
```

None of these call a model or cost money. `check` and `run` read the sources over the
internet, which takes about half a minute. Then:

```bash
uv run lantern why <a link from the note>   # what happened to that link, and why
uv run lantern benchmark                    # a table of every note's cost and time
```

## A real note, with a model

The model is any server that speaks the OpenAI chat API. The example settings point at one
running on your Mac, such as [rapid-mlx](https://github.com/raullenchai/Rapid-MLX) on port
9000, which costs nothing per run. A hosted model works too: `lantern.example.yaml` has ready
blocks for NVIDIA NIM and for Claude. Lantern reads a hosted model's key from the macOS
Keychain, the system's password store, so it never sits in a file. Store it once (the
command asks for the key):

```bash
security add-generic-password -s anthropic -a "$USER" -w
```

then set `keychain_service: anthropic` in the model block. For Claude also set
`temperature: null`, since newer Claude models reject a low temperature. If you set
`api_key_env`, that environment variable is used instead whenever it is set.

```bash
uv run lantern run ai-weekly --dry-run   # the full note, printed and not saved
uv run lantern run ai-weekly             # the full note, saved
```

**A dry run costs as much as a real run.** `--dry-run` does everything a real run does,
including asking the model to judge every item and write the note; it only skips saving. In
the live test on 15 November 2026 it took about 225 seconds and about $0.40 with Claude
Sonnet 5.5. Only the commands in the quick start are free.

Each note records what its run took (`run_seconds`, `run_model_calls`, `run_tokens_in`,
`run_tokens_out`, `run_cost_usd`, at list price; 0 for a model on your Mac). Prices for
Claude Opus 5.5 and Sonnet 5.5 are built in; for another hosted model add
`price_per_mtok: {input: <$>, output: <$>}` under `model:`.

| Command | What it does |
| --- | --- |
| `lantern run <recipe> [--until YYYY-MM-DD] [--dry-run] [--no-model]` | Write the note. `--dry-run` prints it instead of saving it (a model is still called); `--no-model` writes a keyword-ranked note without one. |
| `lantern why <url>` | Show every decision about a link. |
| `lantern check [<interest>]` | Check the settings; with an interest, try each source once. |
| `lantern status` | How the weekly schedule and the last runs went. |
| `lantern benchmark` | Rewrite `Lantern/Benchmark.md` in the vault: cost, time and tokens of every note, Lantern's and Q Lens's. |

Settings are read from `LANTERN_SETTINGS` if set, else `lantern.yaml` in the current folder,
else `~/.config/lantern.yaml`. Exit codes: 0 done, 1 settings problem, 2 vault or library
problem, 3 another run is going.

## Where the output goes

With the example settings, everything stays in one folder inside this checkout, which git
ignores:

```text
lantern/output/
├── library.sqlite                 the library: items, decisions with reasons, runs, notes
├── library.sqlite.lock            stops two runs from using the library at once
└── notes/                         the vault
    └── Lantern/
        ├── AI news/Lantern/
        │   └── 2026-W46.md        one note per week, named by its ISO week number
        └── Benchmark.md           written by `lantern benchmark`
```

- `run` writes the note and adds the run, its items and every decision to the library. A
  second run in the same week replaces that week's note. A dry run writes nothing, not even the library.
- The note starts with properties (YAML front matter): reader properties such as `week` and
  `tags`, then `run_*` properties that record the run: sources checked and failed, items
  seen, judged and picked, seconds, model calls, tokens and cost.
- `why` and `status` only read. `benchmark` rebuilds `Benchmark.md` from the `run_*`
  properties of every note under `Lantern/`, including Q Lens's notes if you fetch them into
  the same folder (see [q-lens/README.md](../q-lens/README.md)). A note written without a
  model shows `?` for cost and tokens there, because no model was called.
- The library's tables are described in [docs/design.md](docs/design.md#what-lantern-stores).

**If you use Obsidian, or run Lantern on a schedule.** Set `vault:` to your Obsidian vault and
the notes appear there instead, in the same `Lantern/` folders. Without a `library:` line, the
library goes to `~/Library/Application Support/Lantern/library.sqlite`. The weekly schedule
below adds two files: a health record at
`~/Library/Application Support/Lantern/schedule.json` (read by `lantern status`) and a log at
`~/Library/Logs/Lantern/weekly.log`.

Nothing Lantern writes is committed to this repository. The notes in
[examples/](../examples/) are copies, and [benchmark/README.md](../benchmark/README.md) is
written by hand.

## Run it every week

A launchd job, macOS's way to start programs on a schedule, writes the AI and security notes
on Mondays at 07:00. Install it once:

```bash
scripts/install-schedule.sh          # --remove uninstalls
uv run lantern status                # how the schedule and the last runs went
```

- **Catches up.** If the Mac slept through Monday 07:00, launchd runs it on wake. It also starts
  hourly and at login, and `scripts/weekly.sh` exits at once unless the week still has no note,
  so a missed or failed run is retried (up to 6 times a week).
- **Never overwrites with an empty note.** If `api.anthropic.com` can't be reached, it records
  `offline` and tries again within the hour instead of running.
- **Settings and key.** It uses `~/.config/lantern-claude.yaml` (set `LANTERN_SETTINGS` to
  change it), and the model key comes from your login Keychain.
- **Run now** with `scripts/weekly.sh --force`. `sudo pmset repeat wake M 06:55:00` wakes a
  sleeping Mac for it.
- **`Operation not permitted` in the log** means macOS privacy blocked the job from this
  folder (`~/Downloads` and iCloud Drive are protected). Give `/bin/bash` Full Disk Access in
  System Settings → Privacy & Security, or move the checkout out of `~/Downloads`.

## Change what you get

- **Sources and themes:** `interests/ai.yaml` and `interests/security.yaml`. A `feed` needs a
  `url`; a `page` reads post links from a listing page with a `link_pattern` (and optionally a
  `date_pattern`). A full-content feed over 2 MB can set `max_mb`. Adding a source is one
  entry under `sources:`; then run `uv run lantern check ai` to try it.
- **How much:** `recipes/ai-weekly.yaml` and `recipes/security-weekly.yaml` (number of items,
  stories, quick links, per-source cap, minimum score).
- **A new interest:** add `interests/<id>.yaml` and `recipes/<id>-weekly.yaml` (copy the
  security pair), then add it to `recipes` in `scripts/weekly.sh`.
- **Voice:** `lenses/news.md`, the instructions the model gets for judging and writing.
- **The reader:** `taste.yaml` says what the reader is building (an item that would change one
  of those projects earns the `own_stack` trait) and lists traits with points. The model says
  which traits apply; Lantern adds the points to its 0 to 10 score. The file here is a made-up
  example; replace it with your own. Q Lens copies it with `./sync-shared.sh`.

## Develop

```bash
uv run ruff check
uv run pytest      # offline: every test uses saved pages and a fake model
```

How the code is organised, what the library stores and how to add a source type are in
[docs/design.md](docs/design.md).
