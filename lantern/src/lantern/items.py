"""The common item shape, plus date, text and URL helpers every stage shares."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class SourceError(Exception):
    """A source could not be collected; the run records it and carries on."""


@dataclass
class Item:
    url: str
    title: str
    source: str
    published: datetime | None = None
    excerpt: str = ""
    words: int | None = None
    sponsored: bool = False

    @property
    def key(self) -> str:
        return normalize_url(self.url)

    @property
    def reading_minutes(self) -> int | None:
        # Research R8a: only estimate when the feed carried the article body.
        if not self.words or self.words < 150:
            return None
        return -(-self.words // 230)


@dataclass
class Candidate:
    """An item moving through selection, with everything needed to explain the outcome."""

    item: Item
    item_id: int
    heuristic: float = 0.0
    theme: str = "other"
    matches: list[str] = field(default_factory=list)
    score: int | None = None
    reason: str = ""


_TRACKING = re.compile(r"^(utm_.*|ref|ref_src|fbclid|gclid|mc_cid|mc_eid)$")


def normalize_url(url: str) -> str:
    """Identity of an item: scheme-, www-, fragment-, tracking- and slash-insensitive."""
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower().removeprefix("www.")
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not _TRACKING.match(k)])
    path = re.sub(r"/+", "/", parts.path).rstrip("/")
    return urlunsplit(("", host, path, query, ""))[2:]


class _TextOnly(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self.chunks.append(data)


def strip_html(html: str) -> str:
    parser = _TextOnly()
    parser.feed(html or "")
    return re.sub(r"\s+", " ", " ".join(parser.chunks)).strip()


_DAY_FORMATS = ("%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y", "%b %d %Y")


def parse_date(value: object) -> datetime | None:
    """RSS/Atom, ISO and 'Oct 23, 2026' dates, normalised to UTC."""
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError, IndexError, OverflowError):
            parsed = None
        for fmt in _DAY_FORMATS:
            if parsed is not None:
                break
            try:
                parsed = datetime.strptime(text, fmt)
            except ValueError:
                continue
    if parsed is None:
        return None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def excerpt(text: str, limit: int = 280) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",;:.") + "…"
