# Research: Weekly AI Note in Obsidian

Phase 0 decisions for [plan.md](plan.md). Each entry: decision, rationale, alternatives.

## R1. Language and packaging

- **Decision**: Python 3.13, `uv`, one `pyproject.toml` and `uv.lock`, `src/` layout, console
  script `lantern`.
- **Rationale**: Matches Q's existing environment and the old pipeline; `uv` gives a locked,
  reproducible install on the self-hosted runner.
- **Alternatives**: Two environments as before (rejected: duplication was part of the sprawl).

## R2. Runtime dependencies

- **Decision**: `feedparser` and `PyYAML` only.
- **Rationale**: `feedparser` handles years of RSS/Atom quirks (namespaces, encodings, date
  formats) that a hand-written parser would rediscover; the old app's hand-rolled ElementTree
  parser is one of the duplications we are removing. YAML is the agreed configuration format.
- **Alternatives**: `requests`/`httpx` (stdlib `urllib` suffices and honours system proxies);
  `trafilatura` (full-text extraction is out of scope for stage 1); `openai` SDK and LiteLLM
  (one POST to `/v1/chat/completions` does not justify a dependency; routing is forbidden);
  `pydantic` (dataclasses plus explicit validation are enough for three small files).

## R3. Fetching

- **Decision**: `net.get(url)` using `urllib.request` with a 20 s timeout, 2 MB cap, gzip
  support, User-Agent `Lantern/0.1 (+https://github.com/adityakunar/lantern-and-q-lens)`. Page sources
  check `robots.txt` (cached per host per run) with `urllib.robotparser` for that User-Agent.
- **Rationale**: Sources are a curated list Q controls, so the old SSRF-hardened downloader
  (DNS pinning, private-IP rejection) is unnecessary for stage 1; it also ignored proxies.
  Robots and honest identification are constitution constraints.
- **Alternatives**: Port `core/http.py` (230 lines; rejected for now; revisit when Discovery
  starts fetching URLs Q did not choose, stage 3).

## R4. Page sources (feedless sites)

- **Decision**: A `page` source has `index_url`, `link_pattern` (regex with one group for the
  path), optional `base_url`, optional `date_pattern` (regex applied to the HTML following each
  link, within a bounded window, to read a date like `Oct 23, 2026`), and `order`
  (`document` or `numeric`). Titles come from the link text when available, else from the slug.
- **Rationale**: Ported from the old `discover.py scrape`, which worked. On 2026-10-25 The Batch,
  Anthropic News and both Spotify sites showed dates next to links, so a date pattern removes
  the "undated" problem for most pages. IMEC needed per-article fetches; it stays configured but
  undated (and currently failing).
- **Alternatives**: Fetch each article for metadata (slower, more requests; deferred);
  headless browser (rejected: heavy, and these pages are server-rendered).

## R5. Library

- **Decision**: SQLite file at a path from settings (default
  `~/Library/Application Support/Lantern/library.sqlite`), outside the checkout because the
  runner's workspace can be wiped. Tables: `items`, `runs`, `decisions`, `notes`
  ([data-model.md](data-model.md)). A run takes an exclusive `fcntl.flock` on
  `library.sqlite.lock`; a second run exits with code 3. The workflow also sets a
  `concurrency` group.
- **Rationale**: One file, standard library, queryable for `why`. Lock satisfies FR-025.
- **Alternatives**: JSONL files (the old staging approach; awkward for "why" and cross-week
  checks).

## R6. Deterministic selection

- **Decision**: Pipeline of filters, each recording a decision with a reason:
  1. *window*: published within `[until − window_days, until]`; undated eligible only if first
     seen in this run (ported `publication_in_window` semantics, tightened for undated).
  2. *seen*: excluded if included in a note other than the one being (re)written.
  3. *duplicate*: same normalised URL (lowercase host, strip `www.`, fragment, `utm_*`/`ref`
     params, trailing slash; `http`≡`https`) or near-identical title (ported
     `_title_is_near_duplicate`: ≥3 shared non-stop words covering ≥80% of the shorter title).
     The earliest-seen copy wins.
  4. *sponsored*: title/excerpt starts with or contains a sponsored marker
     (`sponsored`, `partner content`, `[ad]`) or the feed's category says so.
  Ranking: heuristic score = theme alias hits in title (×2) and excerpt (×1) + recency bonus
  (≤2 days: 1.0, ≤5: 0.5). Theme = best-matching theme or `other`.
- **Rationale**: Cheap, explainable, testable; reuses the parts of the old scorer that were
  good without its LLM judging or penalties maths.
- **Alternatives**: Embedding similarity for dedupe (needs a model/vector store; rejected).

## R6a. Thin excerpts

- **Decision**: Before filtering, an item whose excerpt is under 40 characters (none, or a
  category label) and that could still fall in the window (dated from a day before the window
  start, or undated and first seen in this run) gets its excerpt from the article page: the
  page's own description plus its first real paragraphs, up to 600 characters. At most 10 such
  fetches per source per run, robots.txt is respected, and a failure leaves the item as it was.
  Text that matches the site's home page, or repeats across a source's pages in the same run
  (taglines, course banners), is dropped. The excerpt is stored in the Library, so each article
  is read only once. Sponsored items are skipped.
  Items from listing pages (type `page`) also take the article's own title (og:title, else
  `<title>` without a short trailing site name), since the listing gives only a link or a
  title made from the URL ("S1 sec", "Issue 377").
- **Rationale**: Title-only items (listing pages, feeds without descriptions) lost the keyword
  cut and the judge's attention to secondary coverage of the same news. W45: DeepMind's own
  Gemini 4 Carbon post had no description, and only Latent Space's summary of it was picked.
- **Alternatives**: Full article bodies for every item (more fetches and tokens; later, with
  the layered library design); summarising pages with the model (costs calls before judging).

## R7. Model judging

- **Decision** (revised 2026-11-02): Send every candidate that passes the filters (ordered by
  heuristic score, capped at 300 as a flood guard) in batches of 10 with
  the interest description, themes and the lens's judging instructions. The model returns JSON:
  `[{"id", "score" 0–10, "theme", "reason"}]`. Invalid/missing entries fall back to the
  heuristic for that item. Select by model score (ties: heuristic), then apply budget (12) and
  per-source cap (3). Threshold: items scoring < 4 are excluded even if budget remains.
- **Rationale**: Batch judging gives the model comparison context; reasons satisfy
  FR-013/FR-015. The original top-40 keyword cut (≤4 calls, for a local model) dropped 49 of
  54 listing-page items in W45, including DeepMind's own Gemini 4 Carbon post, because labs
  rarely use the theme phrases. With a cloud judge, about 18 batches a week cost cents.
- **Alternatives**: Top 40 by keyword (the original; lost primary-lab posts); let marked
  sources skip the cut (adds config); pairwise ranking (more calls).

## R8. Model writing and validation

- **Decision**: One call per note with the selected items (id, title, source, date or
  "undated", reading time, link, excerpt, theme, judge reason) and the lens's writing
  instructions. Layout agreed with Q on 2026-10-25 (design review page): three reading
  depths (title + 30-second callout, thread paragraph, 3–6 stories), stories rather than
  articles, each item once, caveat callouts, "why you're seeing this", quick links, folded
  run details. The model returns the Markdown body; Lantern adds frontmatter and run
  details. Validation: every selected link appears exactly once, no other links, the section
  order and counts of [note-format.md](contracts/note-format.md), length ≤ 1,500 words.
- **Why this layout**: the Sep 2026 essay digests had the voice Q liked but were too dense to
  skim; the Oct 2026 pipeline digests repeated the prose in bullets ("repetitive and dry");
  the browser briefing was traceable but read like an audit. The layout keeps the essay's
  voice and the pipeline's honesty and adds a 30-second layer. On failure, retry once with the validation
  errors; if it fails again, use the fallback renderer and say so in the note.
- **Rationale**: Enforces constitution V mechanically and keeps the fallback path identical to
  the no-model path.
- **Alternatives**: Model writes per section (more calls, more seams); structured JSON prose
  rendered by templates (the old approach that produced the "summary twice" layout Q disliked).

## R8a. Reading time

- **Decision**: Estimate as words ÷ 230 (rounded up) when the feed entry carries the article
  body (`content:encoded` or Atom `content`) with at least 150 words; otherwise omit.
- **Rationale**: Stage 1 does not fetch article pages; a guessed time would break
  constitution V. Many of Q's feeds (Substack, WordPress) include full content.

## R9. Note naming, period and rerun

- **Decision**: Window ends at run time (or `--until`); note file `<vault>/<folder>/<ISO year>-W<ISO
  week>.md` using the ISO week of the window end; frontmatter carries the period to the minute in
  UTC (`period`), and the Library's `runs` row keeps the exact bounds. A rerun in the same ISO week overwrites that file and replaces its `notes` row and
  inclusions. Writes are atomic (write temp file in the same folder, then rename).
- **Rationale**: Predictable names Obsidian sorts well; rerun semantics from FR-021.

## R10. What is ported from reference/pre-reset

| From | To | Notes |
| --- | --- | --- |
| `research_pipeline/tools/profiles/ai.yaml` | `interests/ai.yaml` | Feeds, page sources, themes, aliases; converted to the new schema ([contracts/config.md](contracts/config.md)); comments with verification notes kept. |
| `tools/core/lib.py`: `parse_publication_date`, `publication_in_window`, `strip_html` | `items.py` | ~40 lines. |
| `tools/pipeline/score.py`: `_title_is_near_duplicate`, `_TITLE_STOP_WORDS`, `_words` | `select.py` | ~20 lines. |
| `tools/harvest/discover.py`: RSS entry loop, scrape regex/ordering | `inputs/feed.py`, `inputs/page.py` | Rewritten to the slot contract. |
| `tools/prompts/templates/digest/*`, `docs/NEXT_STEPS.md` editorial notes | `lenses/news.md` | Grounding rules and style guide. |

Everything else in the old tree is not carried over.

## R11. Scheduling and remote trigger

- **Decision**: `.github/workflows/weekly-note.yml` with `schedule: cron "0 6 * * 1"` (Monday
  06:00 UTC) and `workflow_dispatch` (inputs: `until`, `no_model`), `runs-on: [self-hosted,
  macOS]`, `concurrency: lantern-weekly`, `timeout-minutes: 45`. Steps: checkout, `uv sync
  --locked`, `uv run lantern run ai-weekly`. Settings path from the runner's environment
  (`LANTERN_SETTINGS`), so vault and library paths never enter the repository.
  `.github/workflows/checks.yml` runs ruff and pytest on GitHub-hosted Ubuntu for every push.
- **Rationale**: The local model and vault live on the Mac; GitHub provides the schedule, the
  phone trigger and a run log. Queued jobs wait up to 24 h for an offline runner, covering a
  sleeping Mac (spec US3-2).
- **Alternatives**: `launchd` (old approach; no remote trigger or visible history); GitHub-hosted
  runners (cannot reach the local model or vault).
