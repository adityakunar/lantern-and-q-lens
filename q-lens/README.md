# Q Lens

Q Lens writes the same weekly AI news note as [Lantern](../lantern/), but as an **agent**: an
AI model gets the list of sources, a description of the reader with scoring rules, and a
spending limit, and decides the rest itself: which articles to open in full, what to search
the web for, and which stories belong together. It runs in the cloud as a Claude Managed
Agent, Anthropic's hosted service for running agents on a schedule. The
[top-level README](../README.md) compares what each program costs and finds.

Everything here is plain files that you upload to your own Anthropic account with `ant`,
Anthropic's command-line tool. Managed Agents is a beta product, so commands and file formats
may change. Setting it up creates resources in your account that cost money when they run;
each run is limited to $5.

Where to look:

| I want to | Look at |
|---|---|
| see a note it wrote | [examples/2026-11-15/q-lens.md](../examples/2026-11-15/q-lens.md) |
| read the instructions it follows each week | [skills/curate-weekly/SKILL.md](skills/curate-weekly/SKILL.md) |
| set it up in my account | [Set up](#set-up) |
| know where its files go | [Where the output goes](#where-the-output-goes) |
| change the sources, the reader or the schedule | [Change what you get](#change-what-you-get) |

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

Run it now, wait about five minutes for the run to finish, then fetch the note. The simplest
place for it is Lantern's output folder, so that `lantern benchmark` can compare the two
notes:

```sh
ant beta:deployments run --deployment-id <deployment id from claude-lock.json>
mkdir -p ../lantern/output/notes
./fetch-latest-note.sh ../lantern/output/notes   # any existing folder works
```

Run `fetch-latest-note.sh` from this `q-lens/` folder: it reads the deployment's ID from
`claude-lock.json`. Without a folder argument, it uses the `vault:` line of
`~/.config/lantern.yaml`.

`scripts/install-auto-fetch.sh` installs a macOS LaunchAgent, a background job, that fetches
each new note once, every hour, at login and after wake. It reads the vault from
`~/.config/lantern.yaml`. `scripts/auto-fetch.sh --status` prints its health record.

## Where the output goes

During a run, everything happens in a temporary cloud machine:

- The agent saves the note to `/mnt/session/outputs/ai-weekly-<year>-W<week>.md`. The service
  keeps it as a file of that run (a session) in your account.
- The memory store keeps four files in its `ai/` folder between runs (see [Memory](#memory)).
  Everything else on the machine is deleted when the run ends.

`fetch-latest-note.sh` finds the latest run of the deployment, downloads its note and saves it
on your computer as:

```text
<folder>/Lantern/AI news/Agent/<year>-W<week>.md
```

It then runs `scripts/stamp-run-stats.py`, which adds the run's record to the note's
properties: `run_session` (the run's ID), `run_model`, `run_seconds` (time the agent was
working), `run_wall_seconds`, `run_tokens_in`, `run_tokens_out` and `run_cost_usd`. These are
the properties `lantern benchmark` reads. If you fetch into Lantern's output folder, the two
notes sit side by side:

```text
lantern/output/notes/Lantern/AI news/
├── Lantern/2026-W46.md
└── Agent/2026-W46.md
```

The automatic fetch also keeps, in `~/Library/Application Support/Lantern/`, a health record
(`curator-fetch.json`), the runs already fetched (`curator-fetched-sessions.txt`, so a note
you edit is never overwritten) and the runs still waiting for a note
(`curator-fetch-tries.txt`). Its log is `~/Library/Logs/Lantern/curator-fetch.log`.

`ant apply` writes `claude-lock.json` here with the IDs of your resources; git ignores it.
Nothing a run produces is committed to this repository. The note in
[examples/](../examples/) is a copy.

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
