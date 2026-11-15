"""Feedless sites: read post links (and dates) from a server-rendered listing page."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from ..items import Item, SourceError, parse_date, strip_html

type = "page"  # noqa: A001 - the registry key

_KEYS = {
    "type", "index_url", "link_pattern", "base_url", "date_pattern", "order", "limit",
    "tags", "enabled", "notes",
}


def validate(cfg: dict[str, Any]) -> list[str]:
    errors = [f"unknown key '{k}'" for k in sorted(set(cfg) - _KEYS)]
    if not str(cfg.get("index_url", "")).startswith(("http://", "https://")):
        errors.append("'index_url' must be an http(s) address")
    for key in ("link_pattern", "date_pattern"):
        if key in cfg:
            try:
                if re.compile(cfg[key]).groups < 1:
                    errors.append(f"'{key}' needs at least one (group)")
            except re.error as exc:
                errors.append(f"'{key}' is not a valid pattern ({exc})")
    if "link_pattern" not in cfg:
        errors.append("'link_pattern' is required")
    if cfg.get("order", "document") not in ("document", "numeric"):
        errors.append("'order' must be 'document' or 'numeric'")
    return errors


def collect(name: str, cfg: dict[str, Any], fetch) -> list[Item]:
    index_url = cfg["index_url"]
    if not fetch.allowed(index_url):
        raise SourceError("robots.txt does not allow Lantern to read this page")
    html = fetch.get(index_url).decode("utf-8", "replace")
    found: dict[str, tuple[int | None, Item]] = {}
    matches = list(re.finditer(cfg["link_pattern"], html))
    for n, match in enumerate(matches):
        path = match.group(1)
        if path in found:
            continue
        number = match.group(2) if match.re.groups >= 2 else None
        # Read the date only up to the next other post's link, so it never borrows a neighbour's.
        following = next((m.start() for m in matches[n + 1 :] if m.group(1) != path), len(html))
        after = html[match.end() : min(match.end() + 1500, following)]
        published = None
        if date_pattern := cfg.get("date_pattern"):
            if date_match := re.search(date_pattern, after):
                published = parse_date(date_match.group(1))
        item = Item(
            url=urljoin(cfg.get("base_url", index_url), path),
            title=_link_text(after) or _title_from_slug(path),
            source=name,
            published=published,
        )
        found[path] = (int(number) if number and number.isdigit() else None, item)
    if not found:
        raise SourceError("no links matched link_pattern; the page layout may have changed")
    entries = list(found.values())
    if cfg.get("order") == "numeric":
        entries.sort(key=lambda e: e[0] if e[0] is not None else -1, reverse=True)
    return [item for _, item in entries[: int(cfg.get("limit", 10))]]


def _link_text(after_href: str) -> str:
    """Text of the anchor whose href just matched, if it reads like a title."""
    start = after_href.find(">")
    end = after_href.find("</a>")
    if start < 0 or end < start:
        return ""
    text = strip_html(after_href[start + 1 : end])
    return text if 8 <= len(text) <= 200 else ""


def _title_from_slug(path: str) -> str:
    slug = re.sub(r"\.html?$", "", path.rstrip("/").rsplit("/", 1)[-1])
    return slug.replace("-", " ").strip().capitalize() or path
