---
name: curate-weekly
description: Write the weekly AI news note. Use when asked for this week's AI news, a weekly digest, or a curated briefing for the reader described in interests.md.
---

# Curate the weekly AI note

This skill produces one Markdown note covering the last 7 days of AI news for one reader.
Everything you need is in this folder:

- `interests.md`: who the reader is, what they care about, the themes and how to score.
- `taste.yaml`: what the reader is building and the up/down-votes added to each score.
- `sources.json`: the reader's sources. `feeds` are RSS/Atom, `pages` are listing pages
  without a feed (entries with `"verified": false` may have moved).
- `collect.py`: fetches every feed and prints this week's items as compact JSON lines.
- `note-format.md`: the exact layout of the note.
- `memory.md`: the memory kept between runs (links already posted, ongoing threads, source notes).
- `healing.md`: how to repair broken sources and route around the ones that stay broken.

## Steps

1. **Read `interests.md`, `taste.yaml`, `note-format.md` and `memory.md` first.** Then read the three memory
   files (`posted.md`, `threads.md`, `sources.md`) in the memory folder `memory.md` names.

2. **Collect from the feeds with the script, not by reading feeds yourself.** It is much
   cheaper: only titles and short excerpts reach you.
   ```bash
   MEM=/mnt/memory/q-lens-memory/ai   # this note's memory folder; see memory.md
   mkdir -p "$MEM"
   python3 collect.py --days 7 --state "$MEM/source-health.json" > /tmp/items.jsonl 2> /tmp/collect-summary.json
   wc -l /tmp/items.jsonl; cat /tmp/collect-summary.json
   ```
   (No memory folder mounted: leave out `--state`.) Read `/tmp/items.jsonl` (use `grep`/`head`
   to page through it if it is long). The `health` block says what broke and what healed.

3. **Pages are already in that list.** `collect.py` also reads the `pages` in
   `sources.json` (sites without a feed). Their items may have `"date": null`; keep one only
   if its title or its text (step 5) shows it is from this week. Do not use `web_fetch` for
   these pages: it only opens URLs that already appeared in the conversation, so it refuses
   them.

   **Then heal what broke**, following `healing.md` (at most 5 sources; the note comes first).

4. **Search beyond the list.** Run the searches listed under "Search beyond the sources" in
   `interests.md` (at most 12 `web_search` calls in total). Keep only results from the window
   that are primary sources or substantive technical posts.

5. **Judge.** Score every candidate 0-10 from its title and excerpt with the rubric in
   `interests.md`, then add the votes from `taste.yaml`. When the excerpt is too thin to judge and the item might score 7 or more, read
   it with the script (cheaper than `web_fetch`, and it works for any URL):
   ```bash
   python3 collect.py --read <url> [<url> ...] --chars 3000
   ```
   Read at most 15 articles in total. Use `web_fetch` only for URLs that came from
   `web_search` results.
   - Drop items outside the 7-day window, sponsored posts, and near-duplicates (the same
     story from several outlets: keep the primary source and list the others as extra links).
   - Drop any URL listed in `posted.md`. Keep a story already covered in an earlier week only
     if something new happened (a new release, result or reply), and link the new source.
   - Keep items scoring at least 5. Then pick at most 14 items: at most 6 stories plus up to
     8 quick links, and at most 3 items from any one source.
   - Make sure the picks cover the reader's breadth: if one theme takes more than a third of
     the items, swap the weakest ones for the best items from other themes.

6. **Write the note** in exactly the layout in `note-format.md`. Draw the connections between
   stories the way a well-read colleague would (one story answering another, a trend across
   labs), and mark that as interpretation. When a story continues a thread in `threads.md`,
   say so in its "Connects to" callout (for example "continues the thread from W43").

7. **Save it.** Write the note to `/mnt/session/outputs/ai-weekly-<YYYY>-W<ww>.md`, using the
   ISO week of the last day in the window. This folder is the only place that survives after
   the run. Do not try to reach an Obsidian vault or any other location.

8. **Update memory** as `memory.md` describes, only after the note is saved: add this note's
   URLs to `posted.md`, update `threads.md`, add or refresh notes in `sources.md` (failed feeds,
   weak sources, candidate sources), then trim entries older than 8 weeks.

9. **Reply** with a short run report: feeds checked and failed, pages checked, searches run,
   items seen, items judged, items skipped as already posted, items picked, threads updated,
   source notes added, and the output file name. End with a **Health** block: what broke, what
   you fixed (and how), what stayed broken and how you covered it, and what needs the reader.

## Rules

- Never invent facts, numbers or quotes; use only what the sources say.
- Use each URL once. Link to the original post, not an aggregator, when you know it.
- Write in English; translate non-English sources rather than dropping them.
- If something stops you (no network, every feed failing), save a short note explaining what
  happened to the outputs folder anyway, so the reader sees the failure. Do not add anything
  to `posted.md` for a failed run; a note in `sources.md` about the failure is fine.
