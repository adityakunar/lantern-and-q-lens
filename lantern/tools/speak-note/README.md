# Speak note (optional)

Have a note read aloud on your Mac, for example this week's Lantern note. Everything runs
locally: a small Kokoro voice model behind a local server, a stdlib-only Python script, and a
tiny Obsidian plugin with one button. Nice to have, not needed for anything else.

- `speak_note.py` drops frontmatter, code blocks, links and other Markdown noise, follows the
  note's structure (longer pause before a new section, short pause between list items; tune the
  `PAUSES` table), sends the text in short chunks to the server and plays each with `afplay`.
  The audio files are temporary and deleted as it goes.
- `obsidian-plugin/` adds a ribbon button and two commands, **Read note aloud** and
  **Stop reading**. It only ever runs `speak_note.py`, never other shell commands.

Needs macOS on Apple Silicon, `/usr/bin/python3` and [uv](https://docs.astral.sh/uv/).

## 1. Start the voice server

[rapid-mlx](https://pypi.org/project/rapid-mlx/) serves Kokoro with an OpenAI-style
`/v1/audio/speech` endpoint on `localhost:8000`. Python 3.12, because some audio
dependencies have no wheels for newer versions yet:

```sh
uv tool install --python 3.12 'rapid-mlx[audio]==1.1.0'
rapid-mlx serve kokoro        # the first start downloads the model (about 0.5 GB of RAM in use)
```

After that first download you can start it with `HF_HUB_OFFLINE=1` so it never goes online.
To keep model code away from your own files, you can run the server under a separate macOS
user account; the script only talks to it over `localhost`.

## 2. Try it from the terminal

```sh
python3 speak_note.py --print some-note.md    # shows what it would say, and the pauses
python3 speak_note.py some-note.md            # reads it aloud
python3 speak_note.py --stop
```

Options: `--voice af_heart` (any Kokoro voice), `--speed 1.0`. Set `SPEAK_NOTE_URL` if the
server is not on `localhost:8000`.

## 3. Add the button to Obsidian

Copy the plugin and the script into your vault's plugin folder, then turn on **Speak note**
under Settings → Community plugins:

```sh
VAULT=/path/to/your/vault
mkdir -p "$VAULT/.obsidian/plugins/speak-note"
cp obsidian-plugin/main.js obsidian-plugin/manifest.json speak_note.py \
   "$VAULT/.obsidian/plugins/speak-note/"
```

Run the same `cp` again after an update. Errors (for example, the server is not running) show
up as an Obsidian notice.
