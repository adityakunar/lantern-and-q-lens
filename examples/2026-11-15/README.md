# Example output: the notes of 15 November 2026

These three files show what the two programs produce, so you can judge the results without
running anything. They were made by the code in this repository on Sunday 15 November 2026,
from a fresh copy of it, for the news of 8 to 15 November.

| File | What it is |
|---|---|
| [lantern.md](lantern.md) | The note Lantern wrote, with Claude Sonnet 5.5 |
| [q-lens.md](q-lens.md) | The note Q Lens wrote, with Claude Opus 5.5, as fetched by `q-lens/fetch-latest-note.sh` |
| [Benchmark.md](Benchmark.md) | The table `uv run lantern benchmark` built from the two notes' properties |

Both programs used the example taste file shipped in [lantern/taste.yaml](../../lantern/taste.yaml),
which describes a made-up reader who builds a support assistant for a small online shop. That
is why the notes say "your support agent". Q Lens started with an empty memory. The
comparison of the two notes is in [benchmark/README.md](../../benchmark/README.md).

The files are as the programs wrote them, with one change: the ID of the cloud session that
wrote the Q Lens note was removed from its properties. A few things only make sense inside
Obsidian, the note-taking app the notes are written for:

- The block between the two `---` lines at the top is the note's properties: the week, tags,
  and the `run_*` record of how the note was made (sources, items, seconds, tokens, cost).
- `> [!abstract]`, `> [!warning]` and `> [!info]-` are Obsidian callouts: boxed text, the last
  one folded.
- The `[[...]]` links in `Benchmark.md` point to notes inside the vault. Only the two AI notes
  are included here; the table also lists a security note that Lantern wrote the same day.
- File names inside the vault use the ISO week number, so both notes were saved as `2026-W46.md`.

The notes summarise and link to articles by other publishers. The linked articles, and any
short quotes from them, belong to their publishers.
