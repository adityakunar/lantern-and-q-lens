# Contract: Local model endpoint

One OpenAI-compatible endpoint: `POST {model.base_url}/chat/completions` with
`{"model": <name>, "messages": [...], "temperature": 0.2}`. No streaming, no tools.
`temperature` comes from `model.temperature` (default 0.2; `null` leaves it out, which Claude 4.7
and later need) and `max_tokens` is added only when `model.max_tokens` is set.
Availability check: `GET {base_url}/models` with a 5 s timeout before the first call;
failure means a fallback note.

## Judge request (≤ 4 per run, ≤ 10 items each)

System: lens `## Judge` section + interest description + theme list.
User: JSON array `[{"id", "title", "source", "date", "excerpt"}]`.
Expected reply (JSON only, may be wrapped in a code fence):

```json
[{"id": 17, "score": 8, "theme": "agents", "reason": "First-party write-up of a new agent memory design with benchmarks."}]
```

Rules: `score` integer 0–10; `theme` one of the listed themes or `other`; `reason` ≤ 200
characters. Entries that break the rules are ignored and that item falls back to its heuristic.

## Write request (1 per note, plus at most 1 retry)

System: lens `## Write` section (style guide).
User: the selected items, each with id, title, source, date or "undated", reading time if
known, link, excerpt, theme and judge reason; the period; and the limits (3–6 stories, ≤ 6
quick links).
Expected reply: Markdown body in the layout of [note-format.md](note-format.md), choosing
which items become stories (merging items about the same development) and which become
quick links. Lantern inserts the run-details callout itself; the model must not write it. On a failed validation, the retry includes the list of
violations; a second failure means the fallback body.
