# Feature Specification: Weekly AI Note in Obsidian

**Feature Branch**: `claude/project-thread-6432ls` (spec directory `001-weekly-ai-note`)

**Created**: 2026-10-25

**Status**: Draft

**Input**: User description: "Stage 1 of Lantern ('Spotify for news'): every week, collect the
latest posts from my AI sources (the existing ai.yaml list, including feedless pages such as
The Batch), keep what's new and worth reading from the past week, have my local model judge and
write it up, and save one note into a dedicated folder of my Obsidian vault. Runs on a schedule
via a self-hosted GitHub runner on my Mac and can be triggered manually from my phone. Built as a
small core with Input, Recipe and Output slots so later stages (more interests, feedback,
discovery, concepts, podcasts, NotebookLM) plug in without reshaping it."

## Context

Lantern's north star is "Spotify for news and ideas": sources are followed like artists,
grouped into interests like genres, kept in one library, and turned into notes, digests and
later podcasts. This specification covers **stage 1 only**: one interest (AI), one recipe
(the weekly note) and one output (an Obsidian note). The Obsidian note is the reading
surface until the Lantern app arrives in stage 2 (decided 2026-10-25; screens in the UI
mockups at https://claude.ai/artifact/MKypiFWENmhChEVKXsC1gG). Stage 1 MUST therefore store
everything the app will show in the Library: stories, each item's role, reasons, reading
time and run health. Later stages are listed under
*Out of Scope* so this stage leaves room for them without building them.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get this week's AI note in my vault (Priority: P1)

Q runs Lantern for the AI interest. Lantern reads every configured source, keeps items
published in the last seven days that have not appeared in an earlier note, removes duplicate
and sponsored items, ranks what remains, and writes one note into the Lantern folder of Q's
Obsidian vault. Each item appears once, with its title, source, date, a short excerpt and a
link. The note lists any sources that could not be read.

**Why this priority**: This is the whole product promise in its simplest form. Even without
a language model, a clean, de-duplicated weekly list from Q's own sources, in Obsidian, is
useful and replaces checking 27 sites by hand.

**Independent Test**: Run Lantern against recorded copies of the sources with no model
available; a note appears in the configured vault folder containing only this week's,
never-before-included items, with links, and a list of failed sources.

**Acceptance Scenarios**:

1. **Given** a configured AI interest and a vault folder, **When** Q runs the weekly note,
   **Then** one note for the current week is created in that folder, with frontmatter stating
   the period, number of sources checked, number of items and failed sources.
2. **Given** an item that appeared in last week's note, **When** this week's note is
   written, **Then** that item does not appear again.
3. **Given** the same article reached through two sources or two URLs that differ only in
   tracking parameters, **When** the note is written, **Then** it appears once.
4. **Given** one source is unreachable, **When** the run completes, **Then** the note is
   still written and names the unreachable source in its run-details callout.
5. **Given** the language model is not running, **When** the run completes, **Then** the
   note contains a ranked list grouped by theme and states clearly that it was produced
   without the model.
6. **Given** the note for the current week already exists, **When** Q runs Lantern again in
   the same week, **Then** the note is replaced with an up-to-date version rather than a
   second note being created.

---

### User Story 2 - Let my local model pick and write (Priority: P2)

When Q's local model is running, Lantern asks it to judge each candidate against the AI
interest's plain-words description, giving a score and a one-line reason, and keeps the best
items within the weekly budget. The model then writes the note in three reading depths: a
headline title naming the week's idea, "the week in 30 seconds" (three lines), a short
paragraph with the week's common thread, then 3–6 *stories* (related posts merged into one
story) in short connected prose with a caveat callout where needed, followed by up to six
one-line quick links. The agreed layout is shown in the design review page
(https://claude.ai/artifact/F5H5MunEguGuC23A1Y3ywr) and fixed in
[contracts/note-format.md](contracts/note-format.md).

**Why this priority**: Judgment and good writing turn a list into something worth reading,
which is what Q's earlier digest feedback asked for. It depends on Story 1's collection and
filtering, so it comes second.

**Independent Test**: Run Lantern against recorded sources with a stand-in model that returns
fixed scores and text; verify that selection follows the scores and budget, that every
selected item is linked exactly once, and that every decision has a stored reason.

**Acceptance Scenarios**:

1. **Given** 60 candidates and a budget of 12, **When** the model judges them, **Then** at
   most 12 are included, no source contributes more than its cap, and each included item shows
   the model's one-line reason for its inclusion.
2. **Given** a model-written note, **When** Q reads it, **Then** every item is linked once,
   no separate list repeats the prose, and statements are traceable to the collected excerpts.
5. **Given** two included posts about the same development, **When** the note is written,
   **Then** they appear as one story with both links rather than as two stories.
6. **Given** a model-written note, **When** Q has 30 seconds, **Then** the three-line
   summary at the top covers the week's main stories without opening anything else.
3. **Given** the model fails or times out partway through, **When** the run completes,
   **Then** the note falls back to the plain ranked form for the affected part and says so.
4. **Given** any run, **When** Q asks Lantern why a specific article was or was not included,
   **Then** Lantern shows the stored decision and its reason (e.g. "outside the week",
   "already in note 2026-W43", "duplicate of …", "scored 3/10: vendor marketing").

---

### User Story 3 - Have it arrive every Monday without me (Priority: P3)

The weekly note is produced automatically on a fixed weekly schedule on Q's Mac, where the
local model and the vault live, and Q can also trigger a run on demand from the GitHub
website or mobile app.

**Why this priority**: Automation is what makes this a habit rather than a chore, but it
only wraps Stories 1 and 2.

**Independent Test**: Trigger the scheduled job manually; the note appears in the vault and
the job reports success. Trigger it with the model stopped; it still succeeds with the
fallback note.

**Acceptance Scenarios**:

1. **Given** the schedule is enabled and the Mac is awake, **When** the scheduled time
   arrives, **Then** a new weekly note appears in the vault without Q doing anything.
2. **Given** the Mac was asleep at the scheduled time, **When** it wakes within 24 hours,
   **Then** the run happens then and the note covers the correct week.
3. **Given** Q is away from the Mac, **When** Q presses "Run workflow" on GitHub, **Then** a
   run starts on the Mac and its outcome is visible on GitHub.

---

### Edge Cases

- A source publishes no dates (page sources): an item is included only the first time it is
  seen and is labelled "undated"; it is never re-included in a later week.
- A source returns many old items (first run, or a feed that republishes): only items inside
  the seven-day window are eligible, except undated items as above.
- A quiet week with very few or zero eligible items: the note is still written and says so
  plainly; it never pads with older material or invented commentary.
- A page source's layout changes so that no links match: treated as a failed source and named
  in the note.
- A source responds very slowly or with an oversized response: the source is abandoned after a
  bounded time and named as failed; the run continues.
- The vault folder does not exist: it is created; if the vault itself is missing, the run
  fails with a clear message and writes nothing.
- The same story is covered by several sources with different titles: near-identical titles are
  merged and the item is shown once; clearly different articles on the same story are both
  eligible.
- Sponsored or promotional posts flagged as such by the source are excluded.
- Two runs start at the same time: the second waits for or refuses to run alongside the first so
  the library and note are not corrupted.

## Requirements *(mandatory)*

### Functional Requirements

**Configuration**

- **FR-001**: Users MUST be able to define an interest in one configuration file containing:
  name, a plain-words description of what they care about, themes with optional keyword
  aliases, and sources. How often and how much to deliver (window, budget, per-source cap,
  output folder) belongs to the recipe (FR-016).
- **FR-002**: The AI interest MUST ship pre-filled with the existing source list (21 feed
  sources and the feedless pages that pass the robots.txt and server-rendering checks).
- **FR-003**: Adding, removing or editing a source MUST require only a configuration change.
- **FR-004**: Lantern MUST validate configuration before running and report every invalid entry
  by name.

**Collecting (Input slot)**

- **FR-005**: Lantern MUST support two source types: feeds (RSS/Atom) and pages (a listing page
  scraped with a configured link pattern, optionally with dates read from the page).
- **FR-006**: Each source type MUST produce items in one common shape: title, link, publication
  date (or "undated"), source name, excerpt, and the time it was first seen.
- **FR-007**: Lantern MUST identify itself honestly when fetching and MUST NOT fetch page
  sources whose robots.txt disallows general crawlers.
- **FR-008**: A failure of one source MUST NOT stop the run; each failure MUST be recorded with
  its reason.

**Library**

- **FR-009**: Lantern MUST keep one local library recording every item seen, every selection
  decision with its reason, and which note (if any) included each item.
- **FR-010**: The library MUST persist between runs so that "already included" can be checked
  across weeks.

**Selecting (core)**

- **FR-011**: Lantern MUST deterministically exclude items that are outside the seven-day
  window, already included in an earlier note, duplicates (same normalised link or
  near-identical title), or marked sponsored.
- **FR-012**: Lantern MUST rank remaining items with a cheap deterministic score (theme keyword
  matches and recency) before any model is involved.
- **FR-013**: When the model is available, Lantern MUST have it score the top-ranked candidates
  against the interest description and give a one-line reason per item, then select the best
  items within the budget and per-source cap.
- **FR-014**: When the model is unavailable, Lantern MUST select by the deterministic score
  within the same budget and cap.
- **FR-015**: Users MUST be able to ask why a given article was or was not included and see the
  stored decision and reason.

**Writing (Recipe slot)**

- **FR-016**: The weekly AI note MUST be defined as a recipe in its own configuration file:
  interest, seven-day window, lens ("news"), item budget, per-source cap and output folder.
- **FR-017**: With the model available, the note MUST follow the layout in
  [contracts/note-format.md](contracts/note-format.md): a headline title naming the week's
  idea; a "week in 30 seconds" callout of exactly three lines; one short paragraph with the
  week's common thread; 3–6 stories, each with a headline stating what happened, theme tags,
  at most two short paragraphs, a caveat callout where relevant, source lines and a
  "why you're seeing this" line; up to six one-line quick links; and a folded run-details
  callout.
- **FR-017a**: Posts about the same development MUST be merged into one story listing all
  their links; each item MUST appear exactly once, either in a story or as a quick link.
- **FR-017b**: Each source line MUST show title (linked), source, date (or "undated") and an
  estimated reading time when the feed supplies enough article text to estimate it; otherwise
  the reading time is omitted, never guessed.
- **FR-018**: Without the model, the note MUST start with a callout stating it was written
  without the model and how to get the written version (re-run), then list the selected items
  grouped by theme with title, source, date, excerpt, link and the deterministic reason, and
  end with the same run-details callout.
- **FR-019**: Written text MUST NOT introduce facts absent from the collected material, and MUST
  label undated items as undated.

**Delivering (Output slot)**

- **FR-020**: Lantern MUST write the note as a Markdown file into the configured vault folder,
  named by year and ISO week, with frontmatter in two groups: reader properties (week,
  human-readable period, reading time, tags naming the interest and the themes covered) and
  `run_*` properties that trace the run (run id, recipe, model or fallback, generated time,
  sources checked and failed, items seen, judged and included, stories, quick links).
- **FR-021**: Re-running within the same week MUST replace that week's note, not add a second.
- **FR-022**: Each note MUST end with a folded run-details callout giving sources reached, items seen, judged and included, and naming every source that failed with its reason.

**Running**

- **FR-023**: Lantern MUST be runnable with one command for a given interest, with options to
  override the window end date and to do a dry run that writes nothing.
- **FR-024**: The repository MUST include a scheduled weekly job and a manual trigger that run
  on a self-hosted runner on the user's Mac.
- **FR-025**: Concurrent runs MUST NOT corrupt the library or the note.

### Key Entities

- **Interest**: A named area of curiosity (here: AI) with a plain-words description, themes
  and sources.
- **Source**: Something the user follows; has a name, type (feed or page), address, tags and
  type-specific settings.
- **Item**: One article in the common shape; identified by its normalised link; belongs to a
  source.
- **Decision**: The outcome of selection for one item in one run: included or excluded, the
  stage that decided (filter, rank, judge), a score where applicable and a reason.
- **Run**: One execution of a recipe: when, which window, which sources succeeded or failed,
  whether the model was used, and which note it produced.
- **Recipe**: A saved instruction: interest(s), window, lens, budget, per-source cap and output.
- **Note**: The delivered Markdown file for one recipe and period.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For four consecutive weeks, a note arrives in the vault every week without manual
  action, including weeks where some sources failed or the model was off.
- **SC-002**: Zero items repeat across consecutive weekly notes.
- **SC-003**: Q can get the gist of a week in 30 seconds from the top of the note, and read
  the full note in 15 minutes or less (at most 6 stories and 6 quick links).
- **SC-004**: 100% of items in a note link to their original source, and 100% of selection
  decisions can be explained on request.
- **SC-005**: Adding a new feed source takes under 2 minutes and no code change.
- **SC-006**: A complete weekly run finishes within 30 minutes on Q's Mac.
- **SC-007**: Q judges at least 3 of the first 4 model-written notes "worth reading" and none
  as repetitive in the sense of the earlier digest feedback (items summarised twice).

## Assumptions

- The week is the seven days ending at the run time; notes are named by ISO year and week
  (e.g. `2026-W44`).
- Default weekly budget is 12 items (at most 6 stories plus 6 quick links) with at most 3
  items per source; all configurable.
- One note per interest. A combined "Monday mix" across interests is a later recipe (stage 6),
  not part of stage 1.
- Q's local model is served through an OpenAI-compatible endpoint on the Mac (rapid-mlx today);
  model choice is configuration.
- The Obsidian vault is a folder on the same Mac; Lantern writes under a dedicated subfolder
  (default `Lantern/AI/`) and never modifies other vault files.
- The repository stays private, which makes a self-hosted runner acceptable.
- IMEC AI Stack is kept in the source list but expected to fail intermittently; the other
  feedless pages (The Batch, The Batch Data Points, Anthropic News, Spotify Engineering,
  Spotify Research) were confirmed reachable with dates on 2026-10-25.
- Judging and writing use the text in feeds or listing pages (title, excerpt). When an item in
  the run's window has no real excerpt (under 40 characters), Lantern reads the article once for
  its opening text and keeps that in the Library (research R6a). Full article bodies are a later
  improvement.

## Out of Scope (later stages)

- The Lantern app (Home, Weekly mix, Story; reactions) as an installable web app usable on
  any device, produced on the Mac and read anywhere — stage 2. Stage 1 keeps the Library
  shaped so a read-only snapshot can be exported from it without schema changes.
- Additional interests (Security, Investing) and lenses (alerts, trends); genre and artist
  pages; `lantern add <url>` — stage 3.
- Discover for new sources; feedback beyond the app's reactions — stage 4.
- Concept pages and "ask your library"; "what changed" trend notes — stage 5.
- Podcast and video transcript inputs; custom recipes such as the Monday mix; NotebookLM
  source packs and audio — stage 6 and later.
- Email delivery, a second UI, cloud models or multi-model routing — not planned.
