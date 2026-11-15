"""The stopgap reading surface: one Markdown note per week in the Obsidian vault."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

type = "obsidian"  # noqa: A001 - the registry key


class VaultMissing(Exception):
    """The configured vault folder does not exist (exit code 2)."""


def validate(cfg: dict[str, Any]) -> list[str]:
    errors = [f"unknown key '{k}'" for k in sorted(set(cfg) - {"type", "folder"})]
    folder = str(cfg.get("folder") or "")
    if not folder:
        errors.append("'folder' is required")
    elif PurePosixPath(folder).is_absolute() or ".." in PurePosixPath(folder).parts:
        errors.append("'folder' must be a path inside the vault")
    return errors


def path_for(note, cfg: dict[str, Any], settings) -> Path:
    from . import week_label

    return settings.vault / cfg["folder"] / f"{week_label(note.period_end)}.md"


def deliver(note, cfg: dict[str, Any], settings) -> str:
    if not settings.vault.is_dir():
        raise VaultMissing(f"vault folder not found: {settings.vault}")
    path = path_for(note, cfg, settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    front = yaml.safe_dump(note.frontmatter, sort_keys=False, allow_unicode=True)
    text = f"---\n{front}---\n\n{note.body}"
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".lantern-", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)  # atomic: Obsidian never sees a half-written note
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return str(path)
