# Benchmark: Lantern compared with Q Lens

On each date below, both programs wrote the weekly AI news digest (the "note") for the same
7 days, from nearly the same list of about 60 sources.

How each one chooses:

- **Lantern** (the workflow) sends every item's title and first 500 characters to Claude
  Sonnet 5.5, ten items at a time, and gets back a score from 0 to 10 for each. Code then
  keeps at most 12 items: the highest scores first, nothing below 4, and at most 3 from any
  one source. The model writes the note from those.
- **Q Lens** (the agent) runs on Claude Opus 5.5. It scores every item too, but it may open
  up to 15 articles in full when a title is not enough, may search the web, and decides
  itself what goes in.

How to read the tables:

- **Cost** is what the model provider charges at its published prices.
- **Tokens** are the unit models are billed in, roughly three quarters of a word. "In" is
  text the model read, "out" is text it wrote.
- **Judged** is how many items got a score. **Picked** is how many made it into the note.
- A **story** gets a paragraph in the note. A **quick link** gets one line.
- A **primary source** is the original announcement or paper, as opposed to an article
  about it.

The two programs score in similar but not identical ways, so compare what ended up in the
notes, not the scores.

## Note of Sunday 15 November 2026 (news from 8 to 15 November)

This run was the live test of this published repository. Both programs were started from a
fresh copy of it, downloaded from GitHub, with the example taste file that is shipped here
instead of the reader's own. Q Lens started with an empty memory, so it knew nothing about
earlier weeks. The two weeks below ran on the author's own setup, so this week is not an
exact repeat of them.

| | Lantern | Q Lens |
|---|---:|---:|
| Cost | $0.40 | $2.11 (5.3 times as much) |
| Time | 226 seconds | 253 seconds |
| Calls to the model | 23 | not reported by the service |
| Tokens in / out | 73,000 / 25,000 | 2,012,000 / 21,000 |
| Items judged / picked | 211 / 12 | 215 / 14 |
| Stories / quick links | 5 / 1 | 6 / 8 |
| Sources that could not be read | 1 of 64 | 2 |
| Articles read in full | none (by design) | 15 |
| Web searches | none (by design) | 10 |

Six links were in both notes, half of Lantern's 12: AWS and NVIDIA on sending each coding
task to the right model, release 1.110 of LiteLLM (a test version of a program that sits
between an app and many model providers), version 1.0.3 of Rapid-MLX, an Apple paper on AI
models that grade writing style, an OpenRouter article on how much text tool definitions add
to every request, and a Pydantic article on using recorded steps of coding agents to improve
them.

What each note covered:

| Topic | Lantern | Q Lens |
|---|---|---|
| New releases of LiteLLM, and AWS's gateway built on it | story | part of a story (one release only) |
| Paying for a whole coding task, not for one model call | story | quick link |
| AI models that grade other models' answers, and their bias | story | quick link |
| Hidden costs of agents: tool definitions and endless retries | story | story (tool definitions only) |
| Seeing inside coding agents, and designing the program around them | story | quick link |
| Running models on your own Mac | quick link | two quick links |
| New models built to work alongside other models (Gemini 4 Hydrogen, Claude Fable 5.2) | not covered | story |
| Models that return a decision with a probability instead of text (Google, OpenRouter, Perplexity) | not covered | story |
| Inkling 2 Small from Thinking Machines: free weights, and training in 4-bit numbers | not covered | story |
| New models and services from Chinese labs (DeepSeek, Qwen4-Max and others) | not covered | story |
| Agents that tried to break into a website during a safety test (report by Epoch AI) | not covered | story |
| Accuracy of hosted model providers, recommender systems | not covered | quick links |

What this week shows:

1. Lantern again left out the week's big model releases: Gemini 4 Hydrogen, Claude Fable 5.2
   and the free weights of Inkling 2 Small.
2. Both programs found the same dead source: the Thinking Machines feed answered "page not
   found". Both listed it in the note and carried on.
3. Q Lens worked around its two broken sources with a search of each site. Its note still
   has the Inkling 2 Small posts from the Thinking Machines site, and for the Qwen blog it
   used a news digest and said so in a warning. It also listed suggested fixes for the
   broken sources, for a person to approve.
4. With the same example taste file and no memory, the two notes shared more than in earlier
   weeks: 6 links. Lantern still leaned towards how to build and run agents, Q Lens towards
   announcements.

## Note of Monday 9 November 2026 (news from 2 to 9 November)

| | Lantern | Q Lens |
|---|---:|---:|
| Cost | $0.29 | $2.56 (8.9 times as much) |
| Time | 171 seconds | 291 seconds |
| Calls to the model | 17 | not reported by the service |
| Tokens in / out | 62,000 / 17,000 | 3,021,000 / 24,000 |
| Items judged / picked | 157 / 12 | 173 / 14 |
| Stories / quick links | 4 / 2 | 6 / 8 |
| Sources that could not be read | 0 of 56 | 2 |

Three items were in both notes: OpenRouter's automatic model routers, an article by Arize
on testing whether a cheaper model is good enough, and version 1.0.2 of Rapid-MLX, a
program that runs AI models on Apple computers.

What each note covered:

| Topic | Lantern | Q Lens |
|---|---|---|
| Testing AI agents that are already in use | story | not covered |
| Memory for AI agents | story | one quick link |
| Choosing a cheaper model automatically | story | story |
| Running models on your own Mac | story | quick link |
| New freely downloadable models (Kimi K3.1 Pro, Hy4, ERNIE 5.5) | not covered | story |
| New models from US companies (Inkling 2 Small from Thinking Machines, SWE-2 Flash from Cognition) | not covered | story |
| A report by the evaluation group METR on AI speeding up research at Anthropic | not covered | story |
| New training methods | not covered | story |
| Security, mathematical proof tools, recommender systems | not covered | quick links |

Where the picks came from: 7 of Lantern's 12 were primary sources, 4 were tutorials or
product articles from vendors, and 1 was an article about someone else's announcement. Q
Lens picked almost only primary sources and used news roundups as supporting links.

What this week shows:

1. Lantern missed four major items: the Kimi, Inkling and SWE-2 releases and the METR
   report. Two of those came from sources it reads every week.
2. Lantern used 2 of its 12 places on two versions of the same Rapid-MLX release.
3. Lantern picked an Anthropic article on how memory for AI agents is built, which Q Lens
   passed over. Lantern's picks lean towards how to build things; Q Lens's lean towards
   announcements and analysis.
4. Q Lens linked this week's stories to ones from earlier weeks, using its memory. Lantern
   keeps no memory between weeks.

## Note of Monday 2 November 2026 (news from 26 October to 2 November)

| | Lantern | Q Lens |
|---|---:|---:|
| Cost | $0.32 | $2.35 |
| Time | 179 seconds | 267 seconds |
| Calls to the model | 18 | not reported by the service |
| Tokens in / out | 67,000 / 18,000 | 2,605,000 / 19,000 |
| Items judged | 170 | 136 |

Two stories were in both notes: a new model-routing feature in GitHub Copilot, and version
1.0.1 of Rapid-MLX.

What this week shows: Lantern gave sensible scores to posts from the AI labs, but too many
items got the top score. 21 items scored 10, and the note has 12 places, so which of them
got in was arbitrary, and nothing scored below 10 could get in at all. That left out
Google DeepMind's new model Gemini 4 Carbon, which scored 8, and several lab posts that
scored 9 or 10.

## Reproduce

Each note starts with a block of properties that record its own run: `run_seconds`,
`run_model_calls`, `run_tokens_in`, `run_tokens_out` and `run_cost_usd`. The command
`uv run lantern benchmark`, run in the `lantern/` folder, reads the notes of both programs
from the vault (the folder of Markdown notes they are saved to) and writes one table of all
runs to `Lantern/Benchmark.md` in that vault.
