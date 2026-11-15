# Q Lens

A Claude Managed Agent that writes the same weekly AI news note as [Lantern](../lantern/), in
the cloud instead of on your Mac. Everything here is declarative files that you sync to your
own Anthropic workspace with the `ant` CLI. Managed Agents is a beta product, so commands
and file schemas may change.

Lantern follows fixed steps and asks a model to score and write. Q Lens gets the sources, a
description of the reader with scoring rules, and a spending limit, and decides the rest itself: what to open in full, what to search for and
which stories belong together. The [top-level README](../README.md) compares what each one
costs and finds.

## Words used here

Managed Agents has its own vocabulary. Each word below is also one folder of files.

| Word | Meaning |
|---|---|
| **agent** | The model plus its standing instructions and the tools it may use |
| **skill** | A folder of instructions and scripts the agent reads when it does a particular job. Here: how to write the weekly note |
| **deployment** | A schedule that starts the agent with a first message, and a spending limit for each run |
| **environment** | The sandbox a run happens in: a temporary cloud machine, and which websites it may reach |
| **memory store** | A small folder that survives from one run to the next. Everything else in the sandbox is deleted after a run |
| **allowlist** | The list of websites the sandbox may reach. Everything else is blocked |
| **`ant apply`** | The command that reads these files and creates or updates the matching resources in your Anthropic account |
| **vault** | A folder of Markdown notes used with the note-taking app Obsidian. The finished note is saved there |

## What is here

| Path | What it is |
|---|---|
| `agents/q-lens.md` | The agent: model, tools and its standing instructions |
| `skills/curate-weekly/` | The skill it follows: steps, interests, sources, note layout, memory rules and the collector script |
| `deployments/weekly-ai-news-digest.yml` | The deployment "Q Lens weekly AI note": the schedule (Mondays 08:00), the first message of each run and a $5 cost cap per run |
| `environments/q-lens-env.yml` | The sandbox, with a network that reaches only the listed hosts |
| `memory_stores/q-lens-memory.yaml` | What the agent remembers between weeks |
| `network/` | Builds the host allowlist from the skill's sources |
| `shared/` | Files every skill needs; `sync-shared.sh` copies them into each skill |
| `fetch-latest-note.sh`, `scripts/` | Bring the finished note from the run into your Obsidian vault |

## Set up

You need an Anthropic account with Managed Agents, the `ant` CLI signed in (`ant auth login`)
and Python 3.

```sh
cd q-lens
python3 network/build-env.py     # 1. rebuild the allowlist from the sources
./sync-shared.sh                 # 2. copy shared files into the skill
ant apply --dry-run -v .         # 3. preview what will be created
ant apply .                      # 4. create it in your workspace
```

`ant apply` writes `claude-lock.json` with the IDs of the resources it created. That file is
yours and is git-ignored. Keep it next to these files and keep the file names as they are:
IDs are stored by path, so a renamed file becomes a new resource.

Run it now and fetch the note:

```sh
ant beta:deployments run --deployment-id <deployment id from claude-lock.json>
./fetch-latest-note.sh           # vault path is read from ~/.config/lantern.yaml
```

`scripts/install-auto-fetch.sh` installs a macOS LaunchAgent that fetches each new note once,
every hour, at login and after wake. `scripts/auto-fetch.sh --status` prints its health record.

## Memory

One store, mounted in each run at `/mnt/memory/q-lens-memory/`. The note keeps its files in
the `ai/` folder: `posted.md` (links already used), `threads.md` (storylines across weeks),
`sources.md` (notes on sources) and `source-health.json` (kept by the collector). About 8
weeks of history. Never put keys, tokens or personal data in it: every later run reads it back.

## Self-healing

The collector gives each source a status (ok, retried, fallback, stale, failed, quarantined),
keeps it in `source-health.json`, reuses fixes that worked in earlier runs, and lets the agent
look for a moved feed on the same site. Each run report ends with a Health block: broke,
fixed, still broken, needs you. The rules are in `shared/healing.md`.

## Network allowlist

The sandbox reaches only allowed hosts, and web search returns only those hosts too.
`network/build-env.py` builds the list from `skills/curate-weekly/sources.json` plus
`network/extra-hosts.txt`, and writes the environment file and the skill's
`allowed-hosts.txt`. A source that redirects to another site shows up as `blocked` with a
suggested move under "Needs you"; a person approves it by changing the URL or adding the
host. Details: [network/README.md](network/README.md).

## Change what you get

- **Sources:** `skills/curate-weekly/sources.json`, then rebuild the allowlist.
- **Interests and scoring rules:** `skills/curate-weekly/interests.md`.
- **Taste:** edit `../lantern/taste.yaml`; `./sync-shared.sh` copies it here.
- **Schedule and cost cap:** `deployments/weekly-ai-news-digest.yml`.

After any change: `python3 network/build-env.py && ./sync-shared.sh && ant apply .`
