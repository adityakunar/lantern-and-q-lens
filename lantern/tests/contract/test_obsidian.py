"""The Obsidian Output honours contracts/note-format.md and slots.md."""

from datetime import UTC, datetime

import pytest
import yaml

from lantern.config import Settings
from lantern.outputs import OUTPUTS, RenderedNote
from lantern.outputs.obsidian import VaultMissing

OBSIDIAN = OUTPUTS["obsidian"]
CFG = {"type": "obsidian", "folder": "Lantern/AI"}
END = datetime(2026, 10, 26, 6, tzinfo=UTC)


def note(body="# AI · Week 44\n"):
    return RenderedNote("ai-weekly/2026-W44", {"week": "2026-W44", "run_items": 0}, body, END)


def test_writes_iso_week_file_with_frontmatter(tmp_path):
    settings = Settings(tmp_path, tmp_path / "lib.sqlite")
    location = OBSIDIAN.deliver(note(), CFG, settings)
    path = tmp_path / "Lantern" / "AI" / "2026-W44.md"
    assert location == str(path)
    text = path.read_text()
    front = yaml.safe_load(text.split("---\n")[1])
    assert front == {"week": "2026-W44", "run_items": 0}
    assert text.endswith("# AI · Week 44\n")


def test_rerun_replaces_the_note_and_leaves_no_temp_files(tmp_path):
    settings = Settings(tmp_path, tmp_path / "lib.sqlite")
    OBSIDIAN.deliver(note("first\n"), CFG, settings)
    OBSIDIAN.deliver(note("second\n"), CFG, settings)
    folder = tmp_path / "Lantern" / "AI"
    assert [p.name for p in folder.iterdir()] == ["2026-W44.md"]
    assert (folder / "2026-W44.md").read_text().endswith("second\n")


def test_missing_vault_is_an_error(tmp_path):
    with pytest.raises(VaultMissing):
        OBSIDIAN.deliver(note(), CFG, Settings(tmp_path / "nope", tmp_path / "lib.sqlite"))


def test_validate():
    assert OBSIDIAN.validate(CFG) == []
    assert OBSIDIAN.validate({"type": "obsidian", "folder": "/abs"})
    assert OBSIDIAN.validate({"type": "obsidian", "folder": "a/../../b"})
    assert OBSIDIAN.validate({"type": "obsidian"})
