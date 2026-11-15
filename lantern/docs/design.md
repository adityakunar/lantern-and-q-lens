# How Lantern is built

This page is for readers who want to change Lantern or copy part of it. It follows one run
from the sources to the saved note, then describes what Lantern stores and how to add a new
kind of source or a new place to deliver the note. Every file named here is under
[src/lantern/](../src/lantern/).

## One run, step by step

`lantern run ai-weekly` calls `run()` in [run.py](../src/lantern/run.py). It does five
things in order:

1. **Collect.** Each source in the interest file (`interests/ai.yaml`) is read by its source
   type: `feed` for RSS and Atom feeds, `page` for a web page that lists posts. A source that
   fails is recorded with its reason and the run carries on.
2. **Filter.** [select.py](../src/lantern/select.py) removes items with plain rules, in this
   order: outside the week, already shown in an earlier note, a duplicate of another item,
   sponsored. The rest are ranked by theme keywords and recency; at most 300 go on.
3. **Judge.** [judge.py](../src/lantern/judge.py) sends the items to the model ten at a
   time. The model gives each a score from 0 to 10 and a one-line reason, and says which
   traits from the taste file apply; Lantern adds their points to the score.
4. **Pick.** Code keeps the highest scores, up to the recipe's limits: 12 items in all, at
   most 3 from one source, nothing below 4.
5. **Write.** [write.py](../src/lantern/write.py) asks the model to write the note, then
   checks it: every picked link appears exactly once and no link is invented. It asks for one
   fix if needed. If the model is not reachable, or fails twice, Lantern writes a plainer
   note ranked by keywords and says so at the top.

The model is reached through one OpenAI-compatible endpoint in
[model.py](../src/lantern/model.py). Tests replace it with a fake, so no test needs a model
or the internet.

## What Lantern stores

Lantern keeps one SQLite file, the **library**, at
`~/Library/Application Support/Lantern/library.sqlite` unless `library:` in your settings
says otherwise. [library.py](../src/lantern/library.py) defines its tables:

| Table | One row per | What it holds |
|---|---|---|
| `items` | article ever seen | link, title, source, publication date, an excerpt, first and last seen |
| `runs` | run | the week covered, whether the model was used, which sources failed, seconds, model calls, tokens and cost |
| `decisions` | item in a run | the step that decided (`window`, `seen`, `duplicate`, `sponsored`, `rank`, `judge`, `budget` or the pick), the outcome, the score and the reason |
| `notes` | note written | the note's week, recipe, file path and run |
| `inclusions` | item in a note | its position and whether it was a story or a quick link |
| `stories` | story in a note | headline, themes, caveat and the "why you're seeing this" line |

The library is how Lantern knows what it already showed you, and how `lantern why <link>`
can say what happened to an article and why. A dry run works on a copy in memory and leaves
the file unchanged.

## The note

The note is a Markdown file in your Obsidian vault, at
`<vault>/Lantern/AI news/Lantern/<year>-W<week>.md`, where the week is the ISO week number
(the security recipe uses `Lantern/Security/Lantern/`). It starts with properties (YAML front
matter): reader properties such as `week`, `period` and `tags`, then `run_*` properties that
record how it was made, from `run_sources_failed` to `run_seconds`, `run_tokens_in` and
`run_cost_usd`. The body has a title, a 30-second summary, up to 6 stories with their links
and a caveat where needed, quick links, and a folded block of run details. A real one is in
[examples/2026-11-15/lantern.md](../../examples/2026-11-15/lantern.md).

## Adding a source type or a place to deliver the note

Lantern looks up source types and delivery targets by name, so the core never imports a
specific one:

- **Source types** live in [inputs/](../src/lantern/inputs/). Each module has a `type` name,
  a `validate(cfg)` that returns configuration errors, and a `collect(name, cfg, fetch)` that
  returns items. It never opens a network connection itself: `fetch` is passed in, which is
  how the tests feed it saved pages. A failed source raises `SourceError`.
- **Delivery targets** live in [outputs/](../src/lantern/outputs/). Each module has a `type`
  name, a `validate(cfg)` and a `deliver(note, cfg, settings)` that returns where the note
  went. Delivering the same week again replaces the note. Today there is one, `obsidian`.

Add the module to the dictionary in its package's `__init__.py`, and add it to the
parametrised tests in [tests/contract/](../tests/contract/), which check that every source
type and delivery target behaves the same way.

A **recipe** (`recipes/*.yaml`) is data, not code: which interest, how many days, how many
stories and quick links, the per-source cap, the minimum score and where the note goes. The
**lens** (`lenses/news.md`) holds the instructions the model gets for judging and writing.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Done, including a note written without the model or with failed sources |
| 1 | A settings, interest or recipe file is invalid; every problem is printed |
| 2 | The vault folder is missing or the library cannot be written |
| 3 | Another run is already using the library |
