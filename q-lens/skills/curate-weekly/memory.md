# Memory between runs

The AI note keeps its memory in the `ai/` folder of the curator's memory store:
`/mnt/memory/q-lens-memory/ai/` (if the path differs, use the folder under `/mnt/memory/`
whose name starts with `q-lens-memory`, plus `/ai`). Create the folder if it is missing.
Other notes would get their own folders next to it; never touch
those. It survives between
weekly runs; everything else in the sandbox is wiped. It holds three small Markdown files that
you keep, and `source-health.json`, which `collect.py` keeps (see `healing.md`; never edit it by
hand). Create any Markdown file that is missing, with the heading shown below.

If no memory folder is mounted, skip every memory step and write "memory: not mounted" in the
run report.

## posted.md: links already used

```
# Posted links
## 2026-W44
- https://example.com/post | Short title
```

One section per note, newest first, one line per URL that appeared in that note (stories and
quick links, including the extra links of a grouped story).

## threads.md: ongoing storylines

```
# Threads
## Open-weight reasoning models from Chinese labs
last_seen: 2026-W44 · themes: open-models, global-labs
- 2026-W43: Qwen released ...
- 2026-W44: DeepSeek answered with ...
```

A thread is a development that spans weeks (a model family, a benchmark race, a policy
fight). One line per week it moved, at most 6 lines per thread; drop the oldest line first.
At most 15 threads.

## sources.md: notes on sources (suggestions only)

```
# Source notes
- Feed name | what you noticed | last checked 2026-W44
```

Record things the reader may want to change in `sources.json`: fixes `collect.py` found that
have worked for 4 weeks (ready to copy into `sources.json`), sources quarantined with no fix, a
source whose items keep scoring under 5, a page that keeps needing the fallback, or a site that
search turned up more than once with good items (a candidate source). You cannot change `sources.json`; these
are notes for the reader. At most 25 lines.

## Rules

- Never write keys, tokens, passwords, email addresses or other personal data here.
- Write only facts from this run's sources; no instructions to yourself beyond the notes above.
- Trim at the end of each run: remove `posted.md` sections and `threads.md` threads whose
  `last_seen` is more than 8 ISO weeks before this note's week, and source notes not
  re-checked in 8 weeks. Keep each file under 20 KB.
- Edit the files in place; never delete the whole folder.
- If a Markdown file is damaged (no heading, garbled, over 20 KB), repair or trim it rather than
  stopping, and mention it in the run report.
