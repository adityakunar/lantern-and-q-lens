# Lantern

> This is version 1 of Lantern, kept unchanged so the published results can be repeated. It is one half of a comparison: the same weekly
> note is also written by a Claude Managed Agent, [Q Lens](../q-lens/). The results and the
> known flaws are in the [top-level README](../README.md).

Spotify for news, run on your own machine. You follow sources the way you follow artists,
group them into interests the way music has genres, and every week your local model writes
you a short mix of what mattered. See [docs/vision.md](docs/vision.md) for where this is going.

**Stage 1 (this code):** weekly notes for AI and Security, written into your Obsidian vault
by the local model on your Mac. The Lantern app (installable, offline, any device) is stage 2.

## How it works

```
sources ──collect──▶ library ──filter──▶ judge ──▶ write ──▶ Obsidian note
 (feeds, pages)     (SQLite)  (rules)    (model)   (model)
```

1. **Collect** every source in the interest (`interests/ai.yaml`: 53 feeds and 11 feedless
   pages; `interests/security.yaml`: 12 feeds and 1 page). A source that
   fails is listed in the note; the run carries on.
2. **Filter** with plain rules first: the week's window, nothing you were already shown,
   duplicates and cross-posts, sponsored posts. The rest is ordered by theme keywords and
   recency, and all of it goes on (up to 300, a guard against floods).
3. **Judge**: your local model scores each one 0–10 for you, with a one-line reason.
4. **Write**: the model writes the note (a 30-second summary, up to 6 stories, quick links).
   Lantern checks it (every link exactly once, nothing invented) and asks for one fix if
   needed. If the model is down or fails twice, you still get a plainer note ranked by
   keywords, marked as such.

Every decision is stored with its reason, so you can always ask why:

```sh
uv run lantern why https://example.com/some-article
```

## Set up on your Mac

```sh
cd lantern
uv sync
cp lantern.example.yaml ~/.config/lantern.yaml   # set your vault, library and model (found by default)
uv run lantern check ai          # free: validate config and try every source once
uv run lantern run ai-weekly --dry-run --no-model   # free: a keyword-ranked preview, nothing saved
uv run lantern run ai-weekly --dry-run   # calls the model: a full preview, nothing saved
uv run lantern run ai-weekly     # writes <vault>/Lantern/AI news/Lantern/<year>-W<week>.md
uv run lantern check security
uv run lantern run security-weekly   # writes <vault>/Lantern/Security/Lantern/<year>-W<week>.md
```

**What a dry run costs.** `--dry-run` does everything a real run does, including asking the
model to judge every item and write the note, and then prints the note instead of saving it.
It also leaves the library untouched. So it takes as long and costs as much as a real run: in
the live test on 15 November 2026 it took about 225 seconds and about $0.40 with Claude
Sonnet 5.5. `--no-model` skips the model and writes a plainer note ranked by keywords; with
`--dry-run` as well, nothing is saved and nothing is paid (about 30 seconds, all of it spent
reading the sources). `uv run pytest` and `lantern check` never call the model.

The model is any OpenAI-compatible server, for example rapid-mlx on `127.0.0.1:9000`. A cloud server such as
NVIDIA NIM works too. Lantern reads the key from macOS Keychain itself, so it never sits in a settings file,
a `.env` file or your shell profile. Store it once (the command asks for the key):

```sh
security add-generic-password -s nvidia -a "$USER" -w
```

then set `keychain_service: nvidia` in the model settings. Claude works the same way through Anthropic's
OpenAI-compatible endpoint (`keychain_service: anthropic`); set `temperature: null`, since newer Claude
models reject a low temperature. `lantern.example.yaml` has ready blocks for both. If you also set
`api_key_env`, that environment variable wins whenever it is set, which is handy for a one-off test.

| Command | What it does |
| --- | --- |
| `lantern run <recipe> [--until YYYY-MM-DD] [--dry-run] [--no-model]` | Write the note. `--dry-run` prints it instead of saving it (the model is still called and paid); `--no-model` writes a keyword-ranked note without the model. |
| `lantern why <url>` | Show every decision about a link. |
| `lantern check [<interest>]` | Validate config; with an interest, fetch each source once. |
| `lantern benchmark` | Rewrite `Lantern/Benchmark.md`: cost, time and tokens of every note, Lantern's and the news agent's. |

Each note records what its run took in `run_seconds`, `run_model_calls`, `run_tokens_in`,
`run_tokens_out` and `run_cost_usd` (list price; 0 for a model on your Mac). Claude Opus and
Sonnet 5.5 prices are built in; for another hosted model add
`price_per_mtok: {input: <$>, output: <$>}` under `model:` in your settings.

Exit codes: 0 ok, 1 config problem, 2 vault or library problem, 3 another run is going.

## Run it every week

A launchd agent on your Mac writes both notes on Mondays at 07:00. Install it once:

```sh
scripts/install-schedule.sh          # --remove uninstalls
uv run lantern status                # how the schedule and the last runs went
```

- **Catches up.** If the Mac slept through Monday 07:00, launchd runs it on wake. It also starts
  hourly and at login, and `scripts/weekly.sh` exits at once unless the week still has no note,
  so a run missed while the Mac was off or a failed run is retried (up to 6 times a week).
- **Never overwrites with an empty note.** If `api.anthropic.com` can't be reached, it records
  `offline` and tries again within the hour instead of running.
- **Settings and key.** It uses `~/.config/lantern-claude.yaml` (set `LANTERN_SETTINGS` to
  change), and the model key comes from your login Keychain, which is open to agents in your
  logged-in session.
- **Health.** Each attempt writes `~/Library/Application Support/Lantern/schedule.json`; the log
  is `~/Library/Logs/Lantern/weekly.log`. Run now with `scripts/weekly.sh --force`.
- **Optional:** `sudo pmset repeat wake M 06:55:00` wakes a sleeping Mac for it.
- **`Operation not permitted` in the log** means macOS privacy blocked the agent from this
  folder (`~/Downloads` and iCloud Drive are protected). Give `/bin/bash` Full Disk Access in
  System Settings → Privacy & Security, or move the checkout out of `~/Downloads`.

## Change what you get

- **Sources and themes:** `interests/ai.yaml` and `interests/security.yaml`. A `feed` needs a `url`; a `page` reads post
  links from a listing page with a `link_pattern` (and optionally a `date_pattern`). A full-content feed over 2 MB can set `max_mb`.
  Adding a source is one entry under `sources:` (prefer a category or tag feed over a sitewide one); then run
  `uv run lantern check ai` to try it.
- **How much:** `recipes/ai-weekly.yaml` and `recipes/security-weekly.yaml` (budget, stories, quick links, per-source cap,
  minimum score).
- **A new interest:** add `interests/<id>.yaml` and `recipes/<id>-weekly.yaml` (copy the
  security pair), then add it to `recipes` in `scripts/weekly.sh`.
- **Taste and voice:** `lenses/news.md`, the instructions the model gets for judging and writing.
- **What you build and up/down-votes:** `taste.yaml`: your projects (an item that would change one earns `own_stack`) and named traits with points. The model says which traits apply; Lantern adds the points to its 0-10 score. Q Lens copies this file with `./sync-shared.sh`. The file here is an example profile; replace it with your own.

## Develop

```sh
uv run ruff check
uv run pytest      # offline: every test uses fixtures and a fake model
```

The design lives in `specs/001-weekly-ai-note/` (made with Spec Kit) and the rules in
`docs/constitution.md`.
