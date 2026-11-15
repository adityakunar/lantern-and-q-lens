# Tasks: Weekly AI Note in Obsidian

**Input**: Design documents from `/specs/001-weekly-ai-note/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Included. Constitution VI requires offline, fixture-driven tests and a contract test
per slot. Within each story, write the tests first and see them fail before implementing.

**Organization**: Grouped by user story so each story can be built, tested and shown on its own.

## Status (1 Nov 2026)

41 of 43 tasks are done. `main` is at b02148b, 65 tests pass offline and ruff is clean.
Verified end to end on Q's Mac: a Claude run of `ai-weekly` wrote the note to the vault
(after the model-check fixes 3b545ab, 58bd671, b02148b), the model key is read from the macOS
Keychain (PR #17), and all 47 AI sources load, including Nvidia, Meta, Cloudflare and TLDR AI (PR #15).

### Open to-dos

1. **Install the weekly schedule** on the Mac (Q): `scripts/install-schedule.sh`, then
   `uv run lantern status` should say `ok` for this week (quickstart scenario 8, T043). This
   replaces the self-hosted runner: a launchd agent runs `scripts/weekly.sh` Monday 07:00 and
   hourly after that until the week has a note, skips when offline, and writes
   `~/Library/Application Support/Lantern/schedule.json`. Optional: `sudo pmset repeat wake M
   06:55:00` so a sleeping Mac wakes for it.
2. ~~Make Claude the default for scheduled runs~~: done, `weekly.sh` uses
   `~/.config/lantern-claude.yaml` (Keychain service `anthropic`) unless `LANTERN_SETTINGS` is set.
3. ~~**T038**~~: done as `tests/unit/test_schedule.py` (plist, `weekly.sh` gates, `lantern status`).
4. **T043**: write the quickstart results into `quickstart.md`.
5. **Optional: `lantern themes`**, a trend report across weeks. Needs a short spec first.
6. **Spec 002 (news strands, PR #10)** is paused on FR-014: may a second local model sort items
   into strands? See `docs/handoff-2026-10-26.md`.

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on unfinished tasks)
- **[Story]**: US1, US2, US3 from spec.md
- Paths are relative to the repository root

---

## Phase 1: Setup

**Purpose**: Project skeleton and tooling

- [x] T001 Create `pyproject.toml` (Python 3.13, deps `feedparser`, `PyYAML`; dev group `pytest`, `ruff`; console script `lantern = "lantern.cli:main"`; ruff and pytest settings) and run `uv lock` to create `uv.lock`
- [x] T002 [P] Create `.gitignore` (venv, caches, `lantern.yaml`, `*.sqlite`, `*.lock`) and `.python-version` (`3.13`)
- [x] T003 [P] Create package skeleton: `src/lantern/__init__.py`, `src/lantern/inputs/__init__.py`, `src/lantern/outputs/__init__.py`, `tests/conftest.py`, and the `tests/{unit,contract,integration,fixtures}/` folders
- [x] T004 [P] Create `.github/workflows/checks.yml`: on push/PR, ubuntu-latest, `uv sync --locked`, `uv run ruff check`, `uv run pytest`

---

## Phase 2: Foundational (blocks every story)

**Purpose**: Configuration, item model, library and test doubles that all stories use

- [x] T005 [P] Port `parse_publication_date`, `publication_in_window` and `strip_html` from `reference/pre-reset:research_pipeline/tools/core/lib.py`, plus URL normalisation (research R6), into `src/lantern/items.py` with `Item` and `Decision` dataclasses (data-model.md)
- [x] T006 [P] Unit tests for `items.py` in `tests/unit/test_items.py`: RFC 822 / ISO / date-only dates, timezone handling, URL normalisation cases (utm, fragment, www, trailing slash, http/https)
- [x] T007 Implement `src/lantern/config.py`: load and validate settings, interests, recipes and lens files per contracts/config.md, reporting every error with file, key and reason; reject unknown keys
- [x] T008 [P] Unit tests for config validation in `tests/unit/test_config.py` (valid files; missing description; bad regex; unknown key; unknown input/output type; output folder with `..`)
- [x] T009 Convert `reference/pre-reset:research_pipeline/tools/profiles/ai.yaml` into `interests/ai.yaml` (21 feeds, 6 pages, 17 themes with aliases, plain-words description; keep verification notes as comments; add `date_pattern` for The Batch, Data Points, Anthropic News and both Spotify pages)
- [x] T010 [P] Create `recipes/ai-weekly.yaml` (contracts/config.md) and `lantern.example.yaml`
- [x] T011 Implement `src/lantern/library.py`: create schema (data-model.md), `fcntl` run lock on `<library>.lock` (exit code 3 when held), and functions to upsert items, start/finish runs, record decisions, replace a note's inclusions, and look up decisions by URL
- [x] T012 [P] Unit tests for the library in `tests/unit/test_library.py` (schema creation, upsert keeps `first_seen`, inclusions replaced on rewrite, lock refuses a second holder) *(covered in `tests/integration/test_run.py`: lock, rerun replaces inclusions, stored decisions; no separate unit file)*
- [x] T013 [P] Implement `src/lantern/net.py`: `get(url)` with timeout 20 s, 2 MB cap, gzip, honest User-Agent; per-run robots.txt cache with `allowed(url)`
- [x] T014 Build test doubles in `tests/conftest.py`: `FakeFetch` serving files from `tests/fixtures/` by URL (and raising for configured failures), `FakeModel` returning scripted replies, temp vault and library fixtures

**Checkpoint**: Configuration loads, the library works, tests run offline.

---

## Phase 3: User Story 1 — Get this week's AI note in my vault (P1) 🎯 MVP

**Goal**: A deterministic, de-duplicated weekly note in the vault, with failed sources listed, no model needed.

**Independent Test**: `lantern run ai-weekly --no-model` against fixtures writes `Lantern/AI/<year>-W<week>.md` containing only this week's never-before-included items, each linked once, plus a run-details callout naming failed sources.

### Tests for User Story 1 (write first, expect failure)

- [x] T015 [P] [US1] Record fixtures in `tests/fixtures/`: two RSS feeds, one Atom feed, one malformed feed, The Batch and Anthropic News listing pages, a robots.txt that disallows `/` *(trimmed to one feed and one listing page in `tests/fixtures/`; contract tests build the rest inline)*
- [x] T016 [P] [US1] Contract tests for Inputs in `tests/contract/test_inputs.py`: each registered input returns Items in the common shape; page input reads dates via `date_pattern`, orders numerically, refuses robots-disallowed sites; failures raise `SourceError`
- [x] T017 [P] [US1] Unit tests for selection in `tests/unit/test_select.py`: window (incl. undated first-seen rule), seen-in-other-note, duplicate URL and near-duplicate title (earliest wins), sponsored, heuristic ranking and theme assignment, budget and per-source cap; every exclusion carries a reason
- [x] T018 [P] [US1] Contract tests for the Obsidian output and fallback note in `tests/contract/test_obsidian.py`: path naming, frontmatter keys, invariants from contracts/note-format.md, atomic replace on rerun, folder created, vault missing → error
- [x] T019 [P] [US1] Integration tests in `tests/integration/test_run_fallback.py`: full run without model; second run a week later repeats nothing (SC-002); rerun in the same week replaces the note (FR-021); one failing source still yields a note (US1-4); zero eligible items yields a "quiet week" note *(merged into `tests/integration/test_run.py`; quiet week is tested in `tests/unit/test_write.py`)*

### Implementation for User Story 1

- [x] T020 [P] [US1] Implement the feed Input in `src/lantern/inputs/feed.py` (port the entry loop from `reference/pre-reset:research_pipeline/tools/harvest/discover.py`, excerpt via `strip_html`, word count from full content for reading time (research R8a), sponsored hints from categories) and register it in `src/lantern/inputs/__init__.py`
- [x] T021 [P] [US1] Implement the page Input in `src/lantern/inputs/page.py` (port scrape regex/ordering from `discover.py`, link text as title, `date_pattern` window, robots check via injected `allowed`) and register it
- [x] T022 [US1] Implement `src/lantern/select.py`: filters in the order of data-model.md with reasons, port `_title_is_near_duplicate` and stop words from `reference/pre-reset:research_pipeline/tools/pipeline/score.py`, heuristic score and theme, budget/cap selection
- [x] T023 [US1] Implement the fallback renderer in `src/lantern/write.py` per contracts/note-format.md "Body: fallback" (warning callout, grouped by theme, excerpt ≤ 280 chars, reading time when known, "Why:" line, undated label, quiet-week text, folded run-details callout)
- [x] T024 [US1] Implement the Obsidian Output in `src/lantern/outputs/obsidian.py` (path, frontmatter, atomic write, folder creation) and register it
- [x] T025 [US1] Implement `src/lantern/run.py`: lock → load config → collect each source via registry (record failures) → upsert items → select → render → deliver → record run, decisions, note and inclusions
- [x] T026 [US1] Implement `lantern run` with `--until`, `--dry-run`, `--no-model` and `lantern check` in `src/lantern/cli.py` per contracts/cli.md (exit codes 0/1/2/3)

**Checkpoint**: MVP. Quickstart scenarios 1–3 and 6 pass; a usable weekly note exists without any model.

---

## Phase 4: User Story 2 — Let my local model pick and write (P2)

**Goal**: Model scores candidates with reasons and writes the note in connected prose; every decision is explainable.

**Independent Test**: With `FakeModel` scripted replies, selection follows model scores, budget and cap; the written note passes the invariants; `lantern why` prints stored reasons.

### Tests for User Story 2 (write first, expect failure)

- [x] T027 [P] [US2] Unit tests for the model client in `tests/unit/test_model.py`: availability check, timeout → unavailable, JSON extraction from fenced replies *(model client tests live in `tests/unit/test_config.py`; JSON extraction in `tests/unit/test_judge.py`)*
- [x] T028 [P] [US2] Unit tests for judging in `tests/unit/test_judge.py`: batches of ≤10 from the top 40, invalid entries fall back to heuristic, `min_score` threshold, theme restricted to known themes, reasons stored
- [x] T029 [P] [US2] Unit tests for writing validation in `tests/unit/test_write.py`: missing link, duplicate link, foreign link, wrong section order, 30-second callout without exactly 3 bullets, more than 6 stories or quick links, too long → retry with violations; second failure → fallback body flagged in frontmatter; merged story with two links passes
- [x] T030 [P] [US2] Integration tests in `tests/integration/test_run_model.py`: full run with scripted model; model dies mid-run → fallback for the affected part (US2-3); `lantern why` output for included and excluded links (FR-015) *(merged into `tests/integration/test_run.py`)*

### Implementation for User Story 2

- [x] T031 [P] [US2] Write `lenses/news.md` with `## Judge` and `## Write` sections: the note layout from contracts/note-format.md (three reading depths, stories not articles, caveat callouts, quick links), grounding rules from `reference/pre-reset:research_pipeline/tools/prompts/templates/digest/`, the style guide in `reference/pre-reset:research_pipeline/docs/NEXT_STEPS.md`, and one short example note
- [x] T032 [P] [US2] Implement `src/lantern/model.py`: minimal OpenAI-compatible chat client over `urllib` (availability probe, timeout, JSON extraction) per contracts/model-endpoint.md
- [x] T033 [US2] Implement `src/lantern/judge.py`: batch requests, reply validation, merge with heuristic, record `judge` decisions
- [x] T034 [US2] Extend `src/lantern/write.py` with model writing, validation against note-format invariants (section order, counts, links once), insertion of frontmatter and run details, one retry, fallback; record each item's role (story / quick link) in `inclusions` and each story's headline, themes, caveat and reason in `stories`
- [x] T035 [US2] Wire judging and writing into `src/lantern/run.py` (skip when `--no-model` or unavailable; set `written_by` and `model` in frontmatter)
- [x] T036 [US2] Implement `lantern why <url> [--recipe]` in `src/lantern/cli.py`

**Checkpoint**: Quickstart scenarios 4, 5 and 7 pass.

---

## Phase 5: User Story 3 — Have it arrive every Monday without me (P3)

**Goal**: Scheduled runs on Q's Mac through a launchd agent (on-demand: `scripts/weekly.sh --force`).

**Independent Test**: `scripts/install-schedule.sh`; the agent runs at load, the note appears in the vault and `lantern status` reports `ok` (quickstart scenario 8).

- [x] T037 [US3] Create `.github/workflows/weekly-note.yml`: `schedule` (Monday 06:00 UTC), `workflow_dispatch` inputs `until` and `no_model`, `runs-on: [self-hosted, macOS]`, `concurrency: lantern-weekly`, `timeout-minutes: 45`, steps checkout → `uv sync --locked` → `uv run lantern run ai-weekly` with inputs mapped to options
- [x] T038 [P] [US3] Add a test that checks the schedule's triggers and command *(now the launchd plist and `weekly.sh` gates, in `tests/unit/test_schedule.py`)*
- [x] T044 [US3] launchd schedule replacing the runner: `scripts/launchd/dev.lantern.weekly.plist`, `scripts/weekly.sh` (weekly gate, hourly retry up to 6 a week, offline guard, `caffeinate`), `scripts/install-schedule.sh`, health record and `lantern status`
- [x] T039 [US3] Document runner setup (register, `svc.sh install/start`, `LANTERN_SETTINGS` in the runner `.env`, keep repo private, keep the Mac awake or schedule wake) in `README.md` *(README "Run it every week from GitHub"; the model key now comes from the login Keychain, so no runner `.env`)*

**Checkpoint**: All three stories work independently.

---

## Phase 6: Polish & cross-cutting

- [x] T040 [P] Rewrite `README.md`: what Lantern is (north star in two lines), stage-1 quickstart, configuration files, how slots work, link to the spec
- [x] T041 [P] Run `lantern check ai` against the live sources on the Mac and record which sources fail in `interests/ai.yaml` comments (expect IMEC) *(31 Oct: all 47 AI sources load)*
- [x] T042 Size check: confirm non-test Python under `src/` stays below 2,000 lines (constitution constraint); justify in plan Complexity Tracking otherwise *(31 Oct: 1,619 lines)*
- [ ] T043 Run every quickstart.md scenario on the Mac and note results in `specs/001-weekly-ai-note/quickstart.md` *(scenarios 1 and 4 have run for real (tests, Claude note); results not yet written down; scenario 8 waits on installing the schedule)*

---

## Dependencies & Execution Order

- **Setup (Phase 1)** → **Foundational (Phase 2)** → stories.
- **US1** depends only on Phase 2. **US2** builds on US1's run, select and write modules.
  **US3** needs US1 (US2 optional): the workflow just calls `lantern run`.
- Within a story: tests → inputs/outputs → select/write → run → CLI.

```text
T001 ─► T003 ─► T005,T007,T011,T013 ─► T014 ─► US1 (T015–T026) ─► US2 (T027–T036)
                                                       └────────► US3 (T037–T039)
```

## Parallel Opportunities

- Phase 1: T002, T003, T004 together after T001.
- Phase 2: T005/T006, T008, T010, T012, T013 in parallel once T007 and T011 are underway.
- US1: tests T015–T019 in parallel; then T020, T021 in parallel; T023 and T024 in parallel after T022.
- US2: tests T027–T030 in parallel; T031 and T032 in parallel.

### Example: US1 test batch

```text
T015 fixtures · T016 input contracts · T017 selection · T018 obsidian contract · T019 run integration
```

## Implementation Strategy

1. **MVP first**: Phases 1–3 deliver a useful deterministic weekly note. Stop and use it for a
   week before adding the model.
2. **Then US2**: model judging and writing, the main quality step.
3. **Then US3**: schedule it once the note is worth receiving.
4. Each story ends at a checkpoint that is demonstrable on its own.
