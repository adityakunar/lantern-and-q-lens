# Contract: Configuration files

## `interests/ai.yaml`

```yaml
id: ai
description: >
  New ideas, releases and practical lessons in AI: reasoning, agents, inference efficiency,
  evals, interpretability, recommender systems and LLM applications. Prefer primary sources
  and substantive technical posts; skip marketing, funding news and listicles.
themes:
  agents: [agent, agentic, tool calling, multi agent]
  evals: [eval, evaluation, benchmark, llm judge]
  # … all 17 themes and aliases carried over from the old ai.yaml
sources:
  openai:
    type: feed
    url: https://openai.com/news/rss.xml
    tags: [openai]
  the_batch:
    type: page
    index_url: https://www.deeplearning.ai/the-batch/
    link_pattern: 'href="(/the-batch/issue-(\d+))/?"'
    base_url: https://www.deeplearning.ai
    order: numeric
    date_pattern: '([A-Z][a-z]{2} \d{1,2}, \d{4})'
  # … 42 feeds + 5 pages in total
```

## `recipes/ai-weekly.yaml`

```yaml
id: ai-weekly
interests: [ai]
window_days: 7
lens: news
budget: 12
max_stories: 6
max_quick_links: 6
per_source_cap: 3
min_score: 4
output:
  type: obsidian
  folder: Lantern/AI
```

## `lenses/news.md`

Markdown with two sections, `## Judge` and `## Write`, holding the instructions sent to the
model ([model-endpoint.md](model-endpoint.md)). Editing the lens changes behaviour without code.

## `lantern.yaml` (settings, not committed; `lantern.example.yaml` is)

```yaml
vault: ~/Documents/Obsidian/Main
library: ~/Library/Application Support/Lantern/library.sqlite
model:
  base_url: http://127.0.0.1:9000/v1
  name: bonsai2-27b-2bit
  timeout_s: 120
  # optional: keychain_service (macOS Keychain generic password holding the key, account
  # $USER), api_key_env (variable that overrides the Keychain key when set), temperature (0–2,
  # or null to send none; default 0.2), max_tokens (positive whole number; default: not sent)
  # The key itself is never written to this file, a .env file or ~/.config.
```

Validation reports every error with file, key and reason; unknown keys are errors (to catch
typos).
