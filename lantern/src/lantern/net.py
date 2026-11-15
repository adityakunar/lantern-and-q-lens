"""Bounded HTTP fetching and robots.txt checks for the real run (tests use a fake)."""

from __future__ import annotations

import gzip
import urllib.request
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from .items import SourceError

USER_AGENT = "Lantern/0.1 (+https://github.com/adityakunar/lantern-and-q-lens)"
MAX_BYTES = 2 * 1024 * 1024


class Fetcher:
    def __init__(self, timeout: float = 20, max_bytes: int = MAX_BYTES) -> None:
        self.timeout = timeout
        self.max_bytes = max_bytes
        self._robots: dict[str, RobotFileParser | None] = {}

    def get(self, url: str, max_bytes: int | None = None) -> bytes:
        limit = max_bytes or self.max_bytes
        request = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"}
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read(limit + 1)
                encoding = response.headers.get("Content-Encoding", "")
        except Exception as exc:  # urllib raises many unrelated types
            raise SourceError(_describe(exc)) from exc
        if len(body) > limit:
            raise SourceError(f"response larger than {limit // (1024 * 1024)} MB")
        return gzip.decompress(body) if encoding == "gzip" else body

    def allowed(self, url: str) -> bool:
        host = "{0.scheme}://{0.netloc}".format(urlsplit(url))
        if host not in self._robots:
            parser = RobotFileParser()
            try:
                parser.parse(self.get(host + "/robots.txt").decode("utf-8", "replace").splitlines())
            except SourceError:
                parser = None  # No readable robots.txt means no stated restriction.
            self._robots[host] = parser
        parser = self._robots[host]
        return parser is None or parser.can_fetch(USER_AGENT, url)


def _describe(exc: Exception) -> str:
    code = getattr(exc, "code", None)
    if code:
        return f"HTTP {code}"
    reason = getattr(exc, "reason", None) or exc
    return f"unreachable ({reason})"
