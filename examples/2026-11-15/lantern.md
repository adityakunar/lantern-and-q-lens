---
week: 2026-W46
period: 8 Nov 13:19 → 15 Nov 2026 13:19 UTC
reading_minutes: 69
tags:
- lantern/ai
- ai/agents
- ai/evals
- ai/llm-routing
- ai/coding-agents
run_id: 1
run_recipe: ai-weekly
run_writer: claude-sonnet-5-5
run_generated: 15 Nov 2026 13:23 UTC
run_sources_checked: 64
run_sources_failed:
- thinking_machines (HTTP 404)
run_items_seen: 4369
run_items_judged: 211
run_items: 12
run_stories: 5
run_quick_links: 1
run_seconds: 226.1
run_model_calls: 23
run_tokens_in: 73047
run_tokens_out: 25130
run_cost_usd: 0.3974
---

# AI · Week 46: Agent costs, judge bias and trace visibility

> [!abstract] The week in 30 seconds
> - Coding-agent routing is being judged by what a whole task costs, not by token price.
> - LiteLLM shipped two releases that change failure handling, startup behaviour and spend tracking.
> - LLM judges favor their own answers, and agents need traces and loop limits to stay affordable.

The common thread this week is that agent work is priced and judged per task, not per call. Routing, tool definitions, retries and judge choice all change what a finished task costs and how far you can trust the result. Several posts also argue that you cannot manage this without seeing inside the agent first. This suggests tooling that measures and limits agents is becoming as important as the models themselves.

## LiteLLM ships two releases while AWS shows a gateway built on it
#ai/llm-routing

LiteLLM v1.109.0 adds 11 providers and 311 new model catalog entries. Codex can now discover MCP tools through tool search, and deployments accept daily request and token limits (rpd and tpd). Streams that stall, abort or end without a finish reason now fail visibly, so retries, cooldowns and fallbacks apply to them.

The v1.110.0 release candidate goes further. The router always runs on the Rust core, and a router config the core declines stops the proxy at startup. Spend goes through a ledger by default, and setting general_settings.use_spend_logs_ledger to false restores the old queues. It also adds an Agent Skills Hub with skill upload, version history and an admin review queue. Separately, AWS walks through a self-service LiteLLM gateway on Bedrock that gives platform, finance and security teams visibility and access control.

> [!warning] Caveat
> v1.110.0 is a release candidate, and the startup and spend-logging changes alter existing behaviour, so test before upgrading.

- [LiteLLM v1.109.0 adds 11 providers, Codex tool search and daily limits](https://docs.litellm.ai/release_notes/v1.109.0/v1-109-0) · litellm · 11 Nov
- [LiteLLM v1.110.0rc1 adds the Agent Skills Hub and a Rust-only router](https://docs.litellm.ai/release_notes/v1.110.0rc1/v1-110-0-rc-1) · litellm · 11 Nov
- [Building a self-service LLM gateway with Amazon Bedrock and LiteLLM](https://aws.amazon.com/blogs/machine-learning/building-a-self-service-llm-gateway-with-amazon-bedrock-and-litellm/) · aws ml blog · 12 Nov · 16 min

*Why you're seeing this: these changes affect fallbacks, startup and spend tracking in the LiteLLM repo you watch.*

## Routing coding agents by what a whole task costs
#ai/llm-routing #ai/evals

AWS and NVIDIA describe routing coding-agent requests with NeMo Switchyard on Bedrock. Their point is that a developer pays for the task, not for one call. A task can take a few model calls or dozens, so token price alone does not predict the total. The cost depends on how many turns a model needs, how much history each turn replays, and how often a task is retried or never finishes.

OpenRouter's benchmarking guide offers a way to get that evidence. Run identical tasks through OpenRouter and compare graded accuracy, billed cost and request time on your own inputs and output formats. In its example, GPT-6.1 Sol passed 180 of 180 trials across 60 synthetic tasks.

> [!warning] Caveat
> The OpenRouter result comes from synthetic tasks under the tested contracts and settings, so it will not necessarily carry over to your workload.

- [Route coding agent requests to the right model on Amazon Bedrock with NVIDIA NeMo Switchyard](https://aws.amazon.com/blogs/machine-learning/route-coding-agent-requests-to-the-right-model-on-amazon-bedrock-with-nvidia-nemo-switchyard/) · aws ml blog · 13 Nov · 20 min
- [How to Benchmark LLMs](https://openrouter.ai/blog/tutorials/how-to-benchmark-llms/) · openrouter · 12 Nov

*Why you're seeing this: it covers model selection and routing by whole-task cost, and a method for testing on your own tasks.*

## LLM judges favor themselves and vary on style
#ai/evals

Arena tested 12 models on 1,460 real Arena battles. LLM judges preferred their own responses 70% more often than humans did, and they often disagreed with human preferences. Arena also looked at model-family bias.

Apple's paper, accepted at a NeurIPS 2026 workshop, examines judges for personalized writing, where the user's preferred style (such as "upbeat") is known. It studies how the writing task, the generator and judge pairing, the evaluation objective and general reasoning ability affect judge performance. Taken together, this suggests a judge should be checked against human preferences, and kept apart from the model whose output it scores.

> [!warning] Caveat
> The Arena post is undated, and the excerpt of the Apple paper does not state its results.

- [Do LLM Judges Favor Themselves?](https://arena.ai/blog/llm-judge-self-preference) · arena · undated
- [Evaluating the Evaluators: Investigating LLM Judges for Personalized Writing Style Assessment](https://machinelearning.apple.com/research/evaluating-evaluators-llm-judges) · apple ml research · 10 Nov

*Why you're seeing this: both studies bear on how far to trust the LLM judge in your setup.*

## Tool definitions and retry loops are hidden agent costs
#ai/agents

OpenRouter published two pieces on where agent money goes. The first points out that every tool you give an agent sends its definition to the model on every request, billed as input tokens. An MCP server can add tens of thousands of tokens to the context window, so it compares that cost with command-line tools and skills.

The second covers infinite loops. An agent gets stuck when a model keeps calling a failing tool, usually with the same arguments, because nothing in the loop tells it to stop. Each retry resends the whole conversation, so every turn costs more than the last, and a loop left running overnight can cost thousands of dollars.

- [MCP vs CLI vs Skills: What Each Costs in Context](https://openrouter.ai/blog/insights/mcp-vs-cli-vs-skills/) · openrouter · 11 Nov
- [How to Stop an AI Agent Stuck in an Infinite Loop](https://openrouter.ai/blog/tutorials/ai-agent-infinite-loop/) · openrouter · 12 Nov

*Why you're seeing this: both apply to an MCP-served support agent that handles refunds and orders.*

## Seeing inside coding agents and designing their harness
#ai/coding-agents

Pydantic argues that despite rapid gains in models and harnesses, coding agents remain opaque. When an agent fails or spins in endless exploration, it is hard to tell why from the outside. Its article covers using traces to see what the agent did and improve your workflows.

Anthropic's engineering post comes at the same problem from the design side. It describes work on getting Claude to produce high-quality frontend designs and to build complete applications without human intervention. Earlier prompt engineering and harness design lifted performance well above baseline but hit ceilings, which led to new approaches that held across both domains.

- [Using coding agent traces to improve your workflows](https://pydantic.dev/articles/coding-harness-tracing) · pydantic · 13 Nov · 17 min
- [Harness design for long-running apps](https://www.anthropic.com/research/harness-design-long-running-apps) · anthropic engineering · undated

*Why you're seeing this: it ties to your trace and observability work and to designing your own agent harness.*

## Also worth a look
- [v1.0.3](https://github.com/raullenchai/Rapid-MLX/releases/tag/v1.0.3): faster decode on qualified models, more reliable tool calling and structured answers, and a desktop app that can share its API on your network · rapid mlx · 12 Nov · 16 min

> [!info]- Run details
> 63 of 64 sources reached · 4369 items seen · 211 judged · 12 included.
> Not reached: thinking_machines (HTTP 404)
