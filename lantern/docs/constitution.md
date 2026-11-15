# Lantern Constitution

Lantern is "Spotify for news and ideas": follow sources like artists, group them into
interests like genres, keep everything in one library, and turn slices of it into notes,
digests and, later, podcasts. This constitution exists to stop the sprawl that ended the
previous codebase (tag `reference/pre-reset`).

## Core Principles

### I. Small Core, Three Slots

The core is: collect → library → filter → judge → write. Everything else MUST plug into
exactly one of three slots:

- **Input**: a source type that produces Items (feed, page; later podcast, video).
- **Recipe**: a saved selection plus writing instruction (interests, window, lens, budget).
- **Output**: a delivery target for a recipe's result (Obsidian note; later NotebookLM pack, audio).

A feature that fits no slot MUST NOT be built until the constitution is amended. Adding an
Input, Recipe or Output MUST NOT require changes to the core's other parts.
Rationale: the old repo grew two apps, two fetchers and two scorers because nothing said no.

### II. One App, Built on the Library

Lantern has exactly one reading interface: the Lantern app, a local web app that is an
**Output** over the Library. The app MUST only read the Library and write back the user's
reactions (keep, less like this, follow, go deeper); collecting, selecting, judging and
writing stay in the core and MUST NOT be duplicated in the app. The Obsidian note is a
second Output for long-term notes and MUST stay available. No other UI (desktop, TUI,
second web app) may be added. A command-line interface for running and configuring
Lantern is allowed.
Rationale: the user wants a Spotify-like overview Obsidian cannot give, and the old repo
showed what happens when a UI grows its own pipeline.

### III. Local-First, One Model

All language-model work MUST go through a single configurable OpenAI-compatible endpoint,
by default a local server on the user's Mac (rapid-mlx, Ollama, LM Studio). Lantern MUST NOT
contain multi-provider routing, model escalation or cloud fallbacks. When the model is
unavailable, every recipe MUST still produce its output in a deterministic form, clearly
labelled as such.
Rationale: one model removes an entire layer of the old code and keeps reading private.

### IV. Deterministic Before Judgment

Collecting, normalising, windowing, de-duplicating and "already seen" checks MUST be
deterministic and free of model calls. The model is used only to judge relevance and to
write. Every selection decision (accepted or rejected) MUST be stored in the library with
a human-readable reason.
Rationale: cheap, testable steps first; "why did I (not) see this?" always has an answer.

### V. Honest Output

Every item in an output MUST link to its original source. Written prose MUST NOT state
facts absent from the collected material, and interpretation MUST be distinguishable from
reporting. Each output MUST list the sources that failed during the run. Each item MUST be
discussed once; no second layer of summaries repeating the prose.
Rationale: this is the editorial standard the user set for earlier digests.

### VI. Offline, Fixture-Driven Tests

Tests MUST run without network access or a running model, using recorded feed and page
fixtures and a fake model client. Each Input, Recipe and Output MUST have tests for its
contract. A change that breaks a contract MUST update its tests in the same commit.
Rationale: the pipeline must be verifiable anywhere, including CI.

## Constraints

- Language and tooling: Python 3.13, managed with `uv`, one `pyproject.toml`, one lockfile.
- Dependencies: each runtime dependency MUST be justified in the plan; prefer the standard
  library. No vector database, no agent framework. The core uses no web framework; the
  app's stack is chosen and justified in its own plan.
- Configuration is data: interests, sources and recipes are YAML files; adding an interest
  or source MUST NOT require code changes.
- State: one local library file (SQLite) plus the vault. No other persistent stores; the
  app keeps only a device cache of what it last synced and a queue of unsent reactions.
- Size budget: stage 1 core SHOULD stay under ~2,000 lines of non-test Python; exceeding it
  requires a written justification in the plan's Complexity Tracking.
- Scraping: page sources MUST respect the site's `robots.txt` wildcard rules and identify
  Lantern with an honest User-Agent.
- Scheduling: runs are triggered by GitHub Actions on a self-hosted runner on the user's Mac,
  or manually from the CLI. The app server serves reading and reactions only; Lantern
  contains no scheduler.
- Any device: the Mac produces; any device reads. The app MUST be a web app that runs in
  any modern browser and installs to a phone's home screen (PWA), with no native builds.
  It MUST get its data only through one documented read contract (the Library snapshot:
  mixes, stories, items, sources, run health) plus one reactions endpoint, so it can be
  served live from the Mac or from a static copy without code changes. It MUST keep working
  offline on the latest synced snapshot and queue reactions until it can deliver them.
- Privacy: the Library and app MUST NOT be reachable by anyone but the owner; whichever way
  the phone reaches them (private network or an access-protected host) is chosen in the
  stage-2 plan.

## Development Workflow

- Each roadmap stage is specified with Spec Kit (specify → plan → tasks) before code.
- One stage per feature branch; each stage MUST deliver a usable result on its own.
- Pushing, merging and opening pull requests require the owner's explicit go-ahead.
- Code from `reference/pre-reset` may be ported only when the plan names it and it passes
  these principles; it is never copied wholesale.

## Governance

This constitution supersedes other practices and documentation in the repository. Every
plan MUST include a Constitution Check against these principles, and every review MUST
verify compliance. Amendments require a written rationale, the owner's approval and a
version bump: MAJOR for removing or redefining a principle, MINOR for adding a principle or
section, PATCH for clarifications. Complexity beyond these rules MUST be justified in the
plan's Complexity Tracking table or removed.

**Version**: 2.1.0 | **Ratified**: 2026-10-25 | **Last Amended**: 2026-10-25

Amendment 2.0.0 (2026-10-25): Principle II redefined from "Obsidian Is the App" to "One
App, Built on the Library" at the owner's request (MAJOR). Constraints updated to match.
Amendment 2.1.0 (2026-10-25): "Any device" constraint added (PWA, snapshot read contract,
offline reading, queued reactions) at the owner's request (MINOR).
