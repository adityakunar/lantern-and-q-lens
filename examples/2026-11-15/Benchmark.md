---
tags: [lantern/benchmark]
---

# Benchmark: Lantern and the news agent

Rebuilt by `uv run lantern benchmark` from each note's `run_*` properties. Cost is the list price in US dollars. Time is wall-clock for Lantern and active time for the agent (its time spent working, not waiting). A ? means that run was made before logging started.

## AI note, side by side

- **2026-W46 AI note**: Lantern $0.40 in 3.8 min, agent $2.11 in 4.2 min, 5x the cost.

## Every note

| Week | Note | Made by | Model | Items | Cost | Time | Tokens in / out |
|---|---|---|---|---:|---:|---:|---:|
| 2026-W46 | [[Security/Lantern/2026-W46\|security]] | Lantern | claude-sonnet-5-5 | 10 | $0.11 | 52 s | 19k / 7k |
| 2026-W46 | [[AI news/Lantern/2026-W46\|ai]] | Lantern | claude-sonnet-5-5 | 12 | $0.40 | 3.8 min | 73k / 25k |
| 2026-W46 | [[AI news/Agent/2026-W46\|ai]] | Agent | claude-opus-5-5 | 14 | $2.11 | 4.2 min | 2012k / 21k |
