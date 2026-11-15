"""Delivery targets: where a finished note goes (docs/design.md)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from ..config import Settings
from . import obsidian


@dataclass
class RenderedNote:
    note_id: str  # e.g. "ai-weekly/2026-W44"
    frontmatter: dict[str, Any]
    body: str
    period_end: datetime


class Output(Protocol):
    type: str

    def validate(self, cfg: dict[str, Any]) -> list[str]: ...
    def deliver(self, note: RenderedNote, cfg: dict[str, Any], settings: Settings) -> str: ...


OUTPUTS: dict[str, Output] = {module.type: module for module in (obsidian,)}


def week_label(end: datetime) -> str:
    year, week, _ = end.isocalendar()
    return f"{year}-W{week:02d}"
