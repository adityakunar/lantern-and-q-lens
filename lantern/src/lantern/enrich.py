"""Fill in a thin excerpt from the article's own page.

Some sources give only a title: listing pages (Anthropic, The Batch), and feeds with no
description (Hugging Face, some DeepMind posts). The judge then has little to go on, and
primary announcements lose to secondary coverage. For items in the run's window, read the
article once, keep its opening text in the library, and never fetch it again.

Pages often carry site-wide text (a company tagline as the description, a course banner above
every post), so text that matches the site's home page, or repeats across a source's pages in
the same run, is dropped. Listing pages only give a link, so their items also take the
article's own title instead of one made from the URL ("S1 sec").
"""

from __future__ import annotations

import html as htmllib
import re
from collections import Counter
from urllib.parse import urlsplit

from .items import SourceError, strip_html

THIN = 40  # an excerpt shorter than this is a label ("Generative AI"), not a description
PER_SOURCE = 10  # article fetches per source per run
MAX_BYTES = 2 * 1024 * 1024
LIMIT = 600  # same cap as feed excerpts

_META = re.compile(
    r'<meta\s+[^>]*?(?:name|property)\s*=\s*["\'](?:og:description|description|'
    r'twitter:description)["\'][^>]*>',
    re.I,
)
_CONTENT = re.compile(r'content\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', re.I)
_DROP = re.compile(r"<(script|style|noscript|nav|header|footer)\b.*?</\1\s*>", re.I | re.S)
_PARAGRAPH = re.compile(r"<p\b[^>]*>(.*?)</p\s*>", re.I | re.S)
_TITLE_META = re.compile(
    r'<meta\s+[^>]*?(?:name|property)\s*=\s*["\'](?:og:title|twitter:title)["\'][^>]*>', re.I
)
_TITLE_TAG = re.compile(r"<title[^>]*>(.*?)</title\s*>", re.I | re.S)
_SITE_SUFFIX = re.compile(r"\s+(?:\||\\|—|–|-)\s+[^|\\—–]{1,25}$")  # " | Site name"
_MIN_PART = 60  # shorter descriptions and paragraphs are bylines, labels or buttons


def is_thin(text: str | None) -> bool:
    return len(text or "") < THIN


def page_parts(page: str) -> list[str]:
    """The page's own description, then its first real paragraphs, in reading order."""
    parts: list[str] = []
    descriptions = []
    for tag in _META.findall(page):
        if found := _CONTENT.search(tag):
            descriptions.append(htmllib.unescape(found.group(1) or found.group(2) or "").strip())
    if descriptions and len(best := max(descriptions, key=len)) >= _MIN_PART:
        parts.append(re.sub(r"\s+", " ", best))
    body = _DROP.sub(" ", page)
    for raw in _PARAGRAPH.findall(body):
        text = strip_html(raw)
        if len(text) >= _MIN_PART:
            parts.append(text)
        if sum(len(p) for p in parts) >= 2 * LIMIT:
            break
    return parts


def page_title(page: str) -> str:
    """The article's own title (og:title, else <title> without a trailing site name)."""
    text = ""
    for tag in _TITLE_META.findall(page):
        if (found := _CONTENT.search(tag)) and (text := (found.group(1) or found.group(2))):
            break
    if not text and (found := _TITLE_TAG.search(page)):
        text = strip_html(found.group(1))
    return _SITE_SUFFIX.sub("", re.sub(r"\s+", " ", htmllib.unescape(text)).strip())


def join_parts(parts: list[str]) -> str:
    kept: list[str] = []
    for part in parts:
        stem = part.rstrip(".… ")  # a description is often the first paragraph, cut short
        if any(stem in k or k.rstrip(".… ") in part for k in kept):
            continue
        kept.append(part)
        if sum(len(k) + 1 for k in kept) >= LIMIT:
            break
    text = " ".join(kept)[:LIMIT].strip()
    return "" if is_thin(text) else text


class ArticleReader:
    """Reads a source's thin articles; remembers each site's home-page text for the run."""

    def __init__(self, fetch) -> None:
        self.fetch = fetch
        self._home: dict[str, set[str]] = {}

    def read(self, urls: list[str]) -> dict[str, tuple[str, str]]:
        """(title, opening text) per URL, either may be ""; unreadable URLs are left out."""
        pages: dict[str, tuple[str, list[str]]] = {}
        for url in urls:
            if (page := self._get(url)) is not None:
                pages[url] = (page_title(page), page_parts(page))
        repeated = Counter(p for _, parts in pages.values() for p in set(parts))
        found = {}
        for url, (title, parts) in pages.items():
            home = self._home_parts(url)
            own = [p for p in parts if p not in home and repeated[p] < 2]
            text = join_parts(own)
            if title or text:
                found[url] = (title, text)
        return found

    def _get(self, url: str) -> str | None:
        try:
            if not self.fetch.allowed(url):
                return None
            return self.fetch.get(url, MAX_BYTES).decode("utf-8", "replace")
        except SourceError:
            return None

    def _home_parts(self, url: str) -> set[str]:
        home = "{0.scheme}://{0.netloc}/".format(urlsplit(url))
        if home not in self._home:
            page = self._get(home) if home != url else None
            self._home[home] = set(page_parts(page)) if page else set()
        return self._home[home]
