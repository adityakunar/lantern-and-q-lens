# Implementation Plan: Weekly AI Note in Obsidian

**Branch**: `claude/project-thread-6432ls` (feature `001-weekly-ai-note`) | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-weekly-ai-note/spec.md`

## Summary

Build Lantern's stage-1 core: a small Python command-line tool that collects the AI interest's
sources (feeds and scraped pages), stores every item and decision in one SQLite library,
filters deterministically (window, seen, duplicate, sponsored), ranks cheaply, asks the local
model to judge and write, and writes one Markdown note per ISO week into the Obsidian vault.
A GitHub Actions workflow runs it weekly, and on demand, on a self-hosted runner on Q's Mac.
The code is organised around the constitution's three slots: Inputs (`feed`, `page`), Recipes
(`ai-weekly`, lens `news`) and Outputs (`obsidian`), around a core that later stages extend
without reshaping. A selected set of proven helpers is ported from `reference/pre-reset`
([research.md](research.md#r10-what-is-ported-from-reference-pre-reset)).

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: `feedparser` (RSS/Atom parsing; tolerant of malformed feeds),
`PyYAML` (configuration). Everything else uses the standard library: `urllib.request` for
HTTP and the model endpoint, `urllib.robotparser`, `sqlite3`, `fcntl`, `html.parser`.
Dev only: `pytest`, `ruff`.

**Storage**: One SQLite file (the library) outside the repository checkout, plus Markdown
notes in the Obsidian vault.

**Testing**: `pytest`, fully offline: recorded feed/page fixtures served by a fake fetcher and
a fake model client (constitution VI).

**Target Platform**: macOS (Q's Mac, self-hosted runner) for real runs; Linux for CI tests.

**Project Type**: Single-project command-line tool.

**Performance Goals**: A full weekly run (27 sources, ~40 model-judged candidates, one writing
call) completes within 30 minutes on Q's Mac (SC-006); collection alone under 2 minutes.

**Constraints**: No network or model needed for tests; bounded per-source time (20 s) and size
(2 MB); model calls bounded (timeout per call, at most 40 candidates judged); writes only inside
the configured vault subfolder.

**Scale/Scope**: One user, one interest, ~27 sources, ~100–300 items seen per week, 12 items
per note. Stage 1 core budget: < 2,000 lines of non-test Python (target ~1,200).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How this plan complies | Status |
| --- | --- | --- |
| I. Small core, three slots | Core = `collect → library → select → judge → write`. Inputs (`inputs/feed.py`, `inputs/page.py`), recipe (`recipes/ai-weekly.yaml` + `lenses/news.md`), output (`outputs/obsidian.py`) are registered by name; see [contracts/slots.md](contracts/slots.md). Nothing outside a slot. | Pass |
| II. One app, built on the Library | Stage 1 ships no UI; its Obsidian note is an Output, and the Library stores stories, roles, reasons and run health so the stage-2 app is a pure reader. | Pass |
| III. Local-first, one model | One OpenAI-compatible endpoint from settings; no routing, no cloud fallback; deterministic fallback note when the model is down. | Pass |
| IV. Deterministic before judgment | Collect, normalise, window, dedupe and seen checks are pure functions; the model only judges and writes; every decision stored with a reason. | Pass |
| V. Honest output | Writing output is validated (every selected link exactly once, no unknown links) or replaced by the fallback; failed sources listed; undated labelled. | Pass |
| VI. Offline, fixture-driven tests | Fake fetcher + fake model; contract tests per slot. | Pass |
| Constraints | Python 3.13 + uv; two runtime deps, justified in research R2; YAML config; one SQLite library; robots.txt respected with honest User-Agent; scheduling only in the workflow file. | Pass |

Post-design re-check (after Phase 1): still passes. The only stateful parts are the library and
the vault folder; the scheduler is the workflow file; no new dependencies were introduced
during design.

## Project Structure

### Documentation (this feature)

```text
specs/001-weekly-ai-note/
├── plan.md              # This file
├── research.md          # Phase 0: decisions and rationale
├── data-model.md        # Phase 1: entities, library schema, state transitions
├── quickstart.md        # Phase 1: how to validate end to end
├── contracts/
│   ├── cli.md           # Commands, options, exit codes
│   ├── config.md        # settings, interest and recipe file formats
│   ├── note-format.md   # The Obsidian note produced
│   ├── model-endpoint.md# Requests made to the local model and expected replies
│   └── slots.md         # Input / Recipe / Output contracts
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
pyproject.toml
lantern.example.yaml          # settings template (vault, model, library paths)
interests/
└── ai.yaml                   # converted from reference/pre-reset ai.yaml
recipes/
└── ai-weekly.yaml
lenses/
└── news.md                   # judging + writing instructions for the "news" lens
src/lantern/
├── __init__.py
├── cli.py                    # run / why / check
├── config.py                 # load + validate settings, interests, recipes
├── items.py                  # Item, Decision dataclasses; URL normalisation; dates; text
├── net.py                    # bounded HTTP GET + robots.txt cache
├── library.py                # SQLite library + run lock
├── select.py                 # filter + heuristic rank + budget/cap selection
├── model.py                  # minimal OpenAI-compatible chat client
├── judge.py                  # model scoring of candidates
├── write.py                  # model writing + validation + fallback renderer
├── run.py                    # orchestrates one recipe run
├── inputs/
│   ├── __init__.py           # registry: {"feed": ..., "page": ...}
│   ├── feed.py
│   └── page.py
└── outputs/
    ├── __init__.py           # registry: {"obsidian": ...}
    └── obsidian.py
tests/
├── fixtures/                 # recorded feeds, pages, robots.txt, model replies
├── conftest.py               # fake fetcher, fake model, temp vault + library
├── contract/                 # one file per slot + CLI + note format
├── unit/                     # items, select, config, library
└── integration/              # full run: with model, without model, failures, rerun
.github/workflows/
├── checks.yml                # ruff + pytest on GitHub-hosted Linux
└── weekly-note.yml           # schedule + workflow_dispatch on [self-hosted, macOS]
```

**Structure Decision**: Single project with a `src/` layout. Configuration (interests, recipes,
lenses) lives as data at the repository root so that adding a source or interest never touches
code (constitution: configuration is data). Slots are subpackages with a name → implementation
registry; recipes are data plus a lens prompt file, so a new recipe is a YAML file, not code.

## Complexity Tracking

No constitution violations. Nothing to justify.
