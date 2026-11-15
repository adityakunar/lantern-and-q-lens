# Quickstart: validating the weekly AI note

## Prerequisites

- macOS with `uv`, the repository cloned, and an Obsidian vault folder.
- Optional: local model server, e.g.
  `rapid-mlx serve bonsai2-27b-2bit --host 127.0.0.1 --port 9000 --no-thinking`.

## Setup

```bash
uv sync --locked
cp lantern.example.yaml ~/.config/lantern.yaml    # set vault, library, model
export LANTERN_SETTINGS=~/.config/lantern.yaml
uv run lantern check ai                           # every source: ok/failed, counts, newest date
```

## Scenarios

| # | Do | Expect | Covers |
| --- | --- | --- | --- |
| 1 | `uv run pytest` | All tests pass offline, no model needed. | Constitution VI |
| 2 | `uv run lantern run ai-weekly --dry-run --no-model` | Per-source summary and the would-be note on stdout; vault and library unchanged. | FR-023 |
| 3 | `uv run lantern run ai-weekly --no-model` | `Lantern/AI news/Lantern/<year>-W<week>.md` with `run_writer: fallback` and the `lantern/fallback` tag, ≤12 items, ≤3 per source, failed sources listed. | US1 |
| 4 | Start the model; `uv run lantern run ai-weekly` | Same file replaced, `run_writer: <model>`, title + 30-second callout + thread + 3–6 stories + quick links + run details, each link once. | US2, FR-021 |
| 5 | `uv run lantern why <a link from the note>` and `why <a link not in it>` | Stored decision and reason for each. | FR-015 |
| 6 | Run again with `--until` one week later | New note; none of scenario 4's items repeat. | SC-002 |
| 7 | Stop the model mid-run (or point `base_url` at a dead port) | Fallback note, exit 0. | US1-5, US2-3 |
| 8 | Register the Mac as a self-hosted runner (labels `self-hosted`, `macOS`); on GitHub, Actions → Weekly note → Run workflow | Run completes on the Mac; note in vault; log visible on GitHub. | US3 |

## Runner setup (once)

GitHub → repository Settings → Actions → Runners → New self-hosted runner (macOS), follow the
commands, then `./svc.sh install && ./svc.sh start` so it survives reboots. The run reads
`~/.config/lantern.yaml` and takes the model key from the login Keychain, so the runner needs
no `.env` file. Keep the
repository private.
