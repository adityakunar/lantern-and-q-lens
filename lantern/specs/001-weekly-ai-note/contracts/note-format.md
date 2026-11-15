# Contract: Obsidian note

Path: `<vault>/<recipe.output.folder>/<ISO year>-W<ISO week>.md`, e.g. `Lantern/AI/2026-W44.md`.
Written atomically; replaced on rerun in the same ISO week.

## Frontmatter

Two groups, in this order. Reader properties come first. The `run_*` properties trace how the
note was made, so a note can always be matched to its run in the Library.

```yaml
---
week: 2026-W44
period: 19 Oct 06:00 → 26 Oct 2026 06:00 UTC   # year on both ends when they differ
reading_minutes: 11         # sum of known reading times; absent if none known
tags:
  - lantern/ai              # always: lantern/<interest>
  - ai/agents               # one per theme covered, in the interest's theme order
  - ai/evals
  - lantern/fallback        # only on a fallback note
run_id: 42                  # the Library's runs.id
run_recipe: ai-weekly
run_writer: bonsai2-27b-2bit   # the model's name, or: fallback
run_generated: 26 Oct 2026 06:07 UTC
run_sources_checked: 27
run_sources_failed: [imec_aistack (HTTP 403)]
run_items_seen: 143
run_items_judged: 41
run_items: 9
run_stories: 3
run_quick_links: 3
---
```

Theme tags come from the stories' tags (model note) or the items' themes (fallback); `other`
is never a frontmatter tag. A quiet week carries only `lantern/<interest>`.

## Body: model-written

Obsidian callout syntax renders as boxes; `-` after the type folds the callout.

```markdown
# AI · Week 44: <the week's idea in a few words>

> [!abstract] The week in 30 seconds
> - <line 1>
> - <line 2>
> - <line 3>

<One short paragraph (≤ 80 words) with the week's common thread.>

## <Story headline stating what happened>
#ai/agents #ai/evals

<At most two short paragraphs (≤ 90 words each). Interpretation is phrased as such.>

> [!warning] Caveat
> <limitation, when relevant>

- [Title](url) · Source · 14 Sep · 9 min
- [Title](url) · Source · Sep · 14 min

*Why you're seeing this: <judge reason>*

## <next story> …

## Also worth a look
- [Title](url): <one line> · Source · 23 Oct

> [!info]- Run details
> 26 of 27 sources reached · 143 items seen · 41 judged · 9 included.
> Not reached: imec_aistack (HTTP 403).
```

Rules: 3–6 stories (fewer in a quiet week); each story has 1–3 links; up to 6 quick links;
story tags are the interest's theme ids, which the model writes plain (`#agents`) and
Lantern namespaces by interest (`#ai/agents`); reading time only when estimable (FR-017b).

## Body: fallback

```markdown
# AI · Week 44

> [!warning] Written without your model
> The local model wasn't reachable, so items are ranked by keyword match and recency and
> shown with their own excerpts. Re-run once the model is up; the written note replaces this one.

## Agents
- **[Title](url)** · Source · 14 Sep · 9 min
  Excerpt (≤ 280 characters).
  *Why: matches agents, mcp*

## Evals
- …

> [!info]- Run details
> …
```

A quiet week (0–2 items) produces a short note that says so and never pads with older items.

## Invariants (tested)

- Every included item's URL appears exactly once (story or quick link); no other URLs appear.
- Model-written notes contain the title, the 30-second callout with exactly three bullets,
  1–6 story headings, at most 6 quick links and the run-details callout, in that order.
- Undated items show "undated" instead of a date.
- Item count in the body equals `run_items` in the frontmatter; `run_stories` and
  `run_quick_links` counts match too.
- A quiet week (0 items) still produces a note that says so.
