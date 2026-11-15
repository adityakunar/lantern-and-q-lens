# Data Model: Weekly AI Note in Obsidian

Configuration entities live in YAML ([contracts/config.md](contracts/config.md)); run-time
entities live in the SQLite library described here.

## Configuration entities

### Settings (`lantern.yaml`, outside the repo; path from `LANTERN_SETTINGS`)
| Field | Type | Rule |
| --- | --- | --- |
| `vault` | path | Must exist at run time; otherwise exit 2. |
| `library` | path | Created if missing. Default `~/Library/Application Support/Lantern/library.sqlite`. |
| `model.base_url` | URL | e.g. `http://127.0.0.1:9000/v1`. Optional; absent = no model. |
| `model.name` | string | Required when `base_url` is set. |
| `model.timeout_s` | int | Default 120. |

### Interest (`interests/<id>.yaml`)
| Field | Type | Rule |
| --- | --- | --- |
| `id` | slug | Equals file name. |
| `description` | text | Plain-words statement of what matters; used by the judge. Non-empty. |
| `themes` | map theme → list of alias phrases | ≥1 theme; aliases lowercase. |
| `sources` | map name → Source | ≥1; names unique slugs. |

### Source (inside an interest)
| Field | Type | Rule |
| --- | --- | --- |
| `type` | `feed` \| `page` | Must be a registered Input. |
| `url` (feed) / `index_url` (page) | URL | http(s). |
| `link_pattern`, `base_url`, `date_pattern`, `order` | page only | `link_pattern` compiles with ≥1 group. |
| `tags` | list | Optional. |
| `enabled` | bool | Default true. |

### Recipe (`recipes/<id>.yaml`)
| Field | Type | Rule |
| --- | --- | --- |
| `id` | slug | Equals file name. |
| `interests` | list of interest ids | Stage 1: exactly one. |
| `window_days` | int | 1–31; default 7. |
| `lens` | name | `lenses/<lens>.md` must exist. |
| `budget` | int | Total included items; default 12. |
| `max_stories` | int | Default 6 (the rest of the budget can be quick links). |
| `max_quick_links` | int | Default 6. |
| `per_source_cap` | int | Default 3. |
| `min_score` | int | Default 4 (model scores 0–10). |
| `output` | `{type, folder}` | `type` must be a registered Output; `folder` relative to the vault, no `..`. |

## Library (SQLite)

```text
items      (id INTEGER PK, url_key TEXT UNIQUE, url TEXT, title TEXT, source TEXT,
            interest TEXT, published TEXT NULL, excerpt TEXT, words INTEGER NULL,
            first_seen TEXT, last_seen TEXT)
runs       (id INTEGER PK, recipe TEXT, started TEXT, finished TEXT NULL,
            period_start TEXT, period_end TEXT, model_used INTEGER, status TEXT,
            sources_ok INTEGER, sources_failed TEXT /* JSON [{source, reason}] */)
decisions  (run_id INTEGER FK runs, item_id INTEGER FK items, stage TEXT, outcome TEXT,
            heuristic REAL NULL, score INTEGER NULL, theme TEXT NULL, reason TEXT,
            PRIMARY KEY (run_id, item_id))
stories    (note_id TEXT FK notes, position INTEGER, headline TEXT, themes TEXT /* JSON */,
            caveat TEXT NULL, why TEXT, PRIMARY KEY (note_id, position))
            -- parsed from the written note so the stage-2 app can show stories without
            -- re-parsing Markdown; fallback notes have no stories rows.
notes      (id TEXT PK /* e.g. ai-weekly/2026-W44 */, recipe TEXT, path TEXT,
            run_id INTEGER FK runs, written TEXT)
inclusions (note_id TEXT FK notes, item_id INTEGER FK items, position INTEGER,
            role TEXT /* story | quick_link | fallback */, story INTEGER NULL,
            PRIMARY KEY (note_id, item_id))
```

- `url_key` is the normalised URL (research R6); identity of an Item.
- `decisions.stage` ∈ `window`, `seen`, `duplicate`, `sponsored`, `rank`, `judge`, `budget`;
  `outcome` ∈ `excluded`, `included`. One row per item per run: the stage that decided.
- Rewriting a note in the same ISO week deletes its `inclusions` and re-inserts them.

## Item lifecycle within a run

```text
collected ─► window? ─no─► excluded(window)
               │yes
               ▼
            seen in another note? ─yes─► excluded(seen)
               │no
               ▼
            duplicate? ─yes─► excluded(duplicate: "same as <url>")
               │no
               ▼
            sponsored? ─yes─► excluded(sponsored)
               │no
               ▼
            ranked (heuristic) ── beyond 300 (flood guard) ─► excluded(rank)
               │
               ▼
            judged (model or heuristic) ── score < min ─► excluded(judge: reason)
               │
               ▼
            budget/cap ── over ─► excluded(budget: "source cap reached" / "budget full")
               │
               ▼
            included ─► written into note ─► inclusions row
```

## Run states

`running` → `written` (note written, model used or fallback) | `failed` (fatal: config, vault
missing, lock held). A run whose every source failed still writes a note (status `written`)
stating that nothing could be collected.
