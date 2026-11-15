# Note format

Reply with Markdown in exactly this layout. Start the file with the frontmatter block.

```
---
week: <YYYY-Www>
period: <first day> → <last day>
tags: [ai-weekly, agent, <theme ids used>]
run_writer: q-lens
run_items_seen: <n>
run_items_judged: <n>
run_items: <n>
run_sources_failed: [<name (reason)>, ...]
run_sources_healed: [<name (how)>, ...]
run_sources_quarantined: [<name>, ...]
---

# AI weekly: <the week's idea in a few words>

> [!abstract] The week in 30 seconds
> - <one line>
> - <one line>
> - <one line>

<One short paragraph, at most 80 words, naming the thread that connects the week.>

## <Story headline that states what happened>
#<theme> #<theme>

<At most two short paragraphs, at most 90 words each.>

> [!note] Connects to
> <Only when this story relates to another story this week; say how in one sentence.>

> [!warning] Caveat
> <Only when there is a real limitation; otherwise leave this callout out.>

- [<title>](<url>) · <source, date>

*Why you're seeing this: <score>/10, <one line on why it matters to the reader>*

## Also worth a look
- [<title>](<url>): <one line> · <source, date> #<theme>
```

Rules:
- Group items about the same development into one story with up to three links.
- Write plainly: say what happened and why it matters. Mark interpretation as such
  ("this suggests…").
- No bullet lists inside stories, no bold text, no emoji, no closing summary.
