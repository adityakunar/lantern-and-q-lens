# Contract: Command-line interface

Entry point: `lantern` (console script). Settings file from `--settings` or `LANTERN_SETTINGS`
(default `./lantern.yaml`).

## `lantern run <recipe>`

Run one recipe end to end and write its note.

| Option | Meaning |
| --- | --- |
| `--until YYYY-MM-DD` | End of the window (default: now). |
| `--dry-run` | Collect, select and print what would be written; write nothing to the vault or library. |
| `--no-model` | Skip the model even if configured (fallback note). |

Stdout: one summary line per source (`ok N items` / `failed: reason`), then
`note: <path> (<n> items, model|fallback)`.

## `lantern why <url> [--recipe <id>]`

Print every stored decision for the item whose normalised URL matches, newest run first:
`<run date> <recipe> <stage> <outcome> <score?> — <reason>` and the note it appears in, if any.
Unknown URL: message "never seen" and exit 0.

## `lantern check [<interest>]`

Validate settings, interests and recipes; with an interest, also fetch each source once and
print item counts and newest date per source. Writes nothing.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success, including notes written with failed sources or without the model. |
| 1 | Configuration invalid (every problem printed). |
| 2 | Fatal environment problem (vault missing, library unwritable). |
| 3 | Another run holds the library lock. |
