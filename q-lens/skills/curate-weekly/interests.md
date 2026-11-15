# The reader and what they care about

The reader is a hands-on ML engineer who builds LLM applications and recommender systems and
runs local models on Apple Silicon (MLX, rapid-mlx, LiteLLM). They read the note once a week
in Obsidian and want to come away knowing what genuinely changed in AI that week, worldwide.

They want: new ideas, results and releases; practical lessons from people building in
production; primary sources (lab posts, papers, release notes, engineering blogs) and
substantive technical writing.

They do not want: marketing, funding or hiring news, event announcements, listicles, hype,
or routine patch releases that change nothing they would notice.

Coverage should be global and broad. US labs, Chinese labs (DeepSeek, Alibaba Qwen, Moonshot
Kimi, Zhipu GLM, MiniMax, ByteDance Seed, Tencent Hunyuan, Baidu ERNIE), European and
Japanese labs (Mistral, Sakana AI), open-weight model makers, and the tools developers use
all count. No single lab, country or theme should dominate the note.

# Themes

Use these theme ids as tags. Pick the single best fit per item, or `other`.

| Theme | Covers |
|---|---|
| model-releases | New frontier, open-weight, embedding and small models; notable model cards |
| reasoning | Chain of thought, test-time compute, reasoning traces |
| agents | Agent design, tool calling, memory, multi-agent systems, MCP, computer use |
| coding-agents | Coding agents and code generation (Claude Code, Codex, SWE-bench) |
| ai-dev-tools | Frameworks, SDKs, IDEs, routers and platforms developers build with |
| open-models | Open-weight releases and the ecosystem around them (Hugging Face, licences) |
| global-labs | What labs outside the US are shipping, especially Chinese, European and Japanese |
| post-training | RLHF, RL, fine-tuning, GRPO, DPO, distillation, synthetic data |
| evals | Benchmarks, evaluation methods, LLM judges, calibration |
| inference-efficiency | Serving, quantization, batching, latency, GPU hosting |
| on-device | Local models, Apple Silicon, MLX, small language models, GGUF |
| ml-ops | Deployment, monitoring, observability of models and agents in production |
| llm-applications | RAG and real LLM products, with lessons from building them |
| llm-routing | Choosing, routing and escalating between models |
| recommender-systems | Recsys, ranking, generative and conversational recommendation |
| personalization | Personalised experiences and user modelling |
| experimentation | A/B testing, bandits, online experiments |
| multimodal | Vision, video, world models, image and video generation |
| audio-ml | Speech recognition and synthesis, music and audio models |
| alignment | Safety research, safety cases, model behaviour |
| interpretability | Mechanistic interpretability, SAEs, steering |
| ai-hardware | Chips and systems that change what is possible or affordable |
| from-scratch | Build-it-yourself explanations and implementations |

# Scoring rubric (0-10)

- 8-10: a new idea, result or release the reader would regret missing. Primary sources and
  substantive technical posts.
- 5-7: useful and on-topic, but incremental or second-hand.
- 0-4: marketing, funding or hiring news, event announcements, listicles, or off-topic.

Then apply the up- and down-votes in `taste.yaml`: for each trait under `votes` that clearly
applies, add its points (they can be negative), and keep the result between 0 and 10. Score
the item first and add the votes after, so a trait is not counted twice. `own_stack` means
the item would change one of the projects under `building` in that file, or is news about
one of the repos it lists.

# Search beyond the sources

The sources miss some labs and tools. Run these searches each week, restricted to the last
7 days, and keep only primary or substantive results:

1. DeepSeek, Qwen, Kimi or GLM new model release this week
2. MiniMax, ByteDance Seed, Tencent Hunyuan or Baidu ERNIE AI announcement this week
3. New open-weight LLM released this week
4. New AI developer tool, SDK or agent framework release this week
5. Claude, Gemini or GPT model or API update this week
6. Notable AI research paper this week (arXiv) on agents, reasoning or post-training
7. Recommender systems or personalisation with LLMs, new paper or engineering post
8. Apple MLX, on-device LLM or local model news this week
