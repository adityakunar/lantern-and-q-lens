"""RSS/Atom feeds: the default, most robust source type."""

from __future__ import annotations

from typing import Any

import feedparser

from ..items import Item, SourceError, parse_date, strip_html

type = "feed"  # noqa: A001 - the slot's registry key

_SPONSORED = ("sponsored", "partner content", "advertorial", "[ad]")


def validate(cfg: dict[str, Any]) -> list[str]:
    keys = {"type", "url", "max_mb", "tags", "enabled", "notes"}
    errors = [f"unknown key '{k}'" for k in sorted(set(cfg) - keys)]
    if not str(cfg.get("url", "")).startswith(("http://", "https://")):
        errors.append("'url' must be an http(s) address")
    max_mb = cfg.get("max_mb", 2)
    if not isinstance(max_mb, int) or isinstance(max_mb, bool) or not 1 <= max_mb <= 32:
        errors.append("'max_mb' must be a whole number from 1 to 32")
    return errors


def collect(name: str, cfg: dict[str, Any], fetch) -> list[Item]:
    # Full-content feeds can be large; 'max_mb' raises the 2 MB default for one feed.
    max_bytes = cfg["max_mb"] * 1024 * 1024 if "max_mb" in cfg else None
    parsed = feedparser.parse(fetch.get(cfg["url"], max_bytes))
    if not parsed.entries:
        if parsed.bozo:
            raise SourceError("feed is malformed or not a feed")
        return []
    items = []
    for entry in parsed.entries:
        link = entry.get("link")
        if not link:
            continue
        body = strip_html(entry.content[0].value) if entry.get("content") else ""
        summary = body or strip_html(entry.get("summary", ""))
        title = strip_html(entry.get("title", "")) or link
        labels = " ".join(t.get("term", "") for t in entry.get("tags", [])).lower()
        sponsored = any(m in labels or title.lower().startswith(m) for m in _SPONSORED)
        items.append(
            Item(
                url=link,
                title=title,
                source=name,
                published=parse_date(entry.get("published") or entry.get("updated")),
                excerpt=summary[:600],
                words=len(body.split()) if body else None,
                sponsored=sponsored,
            )
        )
    return items
