"""Input slot: source types that turn a configured source into Items (contracts/slots.md)."""

from __future__ import annotations

from typing import Any, Protocol

from ..items import Item
from . import feed, page


class Fetch(Protocol):
    def get(self, url: str) -> bytes: ...
    def allowed(self, url: str) -> bool: ...


class Input(Protocol):
    type: str

    def validate(self, cfg: dict[str, Any]) -> list[str]: ...
    def collect(self, name: str, cfg: dict[str, Any], fetch: Fetch) -> list[Item]: ...


INPUTS: dict[str, Input] = {module.type: module for module in (feed, page)}
