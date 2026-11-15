"""Shared fakes: no test touches the network or a real model ."""

from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from lantern.config import ModelSettings, Settings
from lantern.items import SourceError
from lantern.model import ModelError

FIXTURES = Path(__file__).parent / "fixtures"
REPO = Path(__file__).parent.parent
UNTIL = datetime(2026, 10, 25, 23, 59, 59, tzinfo=UTC)


class FakeFetch:
    def __init__(self, pages: dict[str, bytes | Exception], disallowed: set[str] = frozenset()):
        self.pages = pages
        self.disallowed = disallowed
        self.calls: list[str] = []
        self.limits: dict[str, int | None] = {}

    def get(self, url: str, max_bytes: int | None = None) -> bytes:
        self.calls.append(url)
        self.limits[url] = max_bytes
        page = self.pages.get(url, SourceError("HTTP 404"))
        if isinstance(page, Exception):
            raise page
        return page

    def allowed(self, url: str) -> bool:
        return url not in self.disallowed


class FakeModel:
    """Judges by keyword and writes a valid note from the payload, unless told otherwise."""

    name = "fake-model"

    def __init__(self, *, up: bool = True, notes: list[str] | None = None, judge=None):
        self.up = up
        self.notes = list(notes or [])
        self.judge_reply = judge
        self.calls: list[tuple[str, str]] = []

    def available(self) -> bool:
        return self.up

    def chat(self, system: str, user: str) -> str:
        if not self.up:
            raise ModelError("down")
        self.calls.append((system, user))
        if "Score each article" in system:
            if self.judge_reply is not None:
                return self.judge_reply
            items = json.loads(user)
            return json.dumps([
                {"id": i["id"], "score": 2 if "older" in i["title"].lower() else 8,
                 "theme": "agents" if "agent" in i["title"].lower() else "evals",
                 "reason": f"relevant: {i['title']}"}
                for i in items
            ])
        if self.notes:
            return self.notes.pop(0)
        items = json.JSONDecoder().raw_decode(user)[0]["items"]
        return good_note(items, re.search(r"'# (.+?): '", system).group(1))


def good_note(items: list[dict], prefix: str) -> str:
    stories, quick = items[:2], items[2:]
    out = [f"# {prefix}: agents grow up", "", "> [!abstract] The week in 30 seconds",
           "> - one", "> - two", "> - three", "", "A thread runs through the week.", ""]
    for item in stories:
        out += [f"## {item['title']}", f"#{item['theme']}", "", "What happened.", "",
                "> [!warning] Caveat", "> Early results.", "",
                f"- [{item['title']}]({item['url']}) · {item['source_line']}", "",
                f"*Why you're seeing this: {item['why']}*", ""]
    if quick:
        out.append("## Also worth a look")
        out += [f"- [{i['title']}]({i['url']}): one line · {i['source_line']}" for i in quick]
    return "\n".join(out)


@pytest.fixture
def workspace(tmp_path: Path):
    """A config root (real recipe and lens, small interest), a vault and a library path."""
    root = tmp_path / "root"
    for folder in ("recipes", "lenses"):
        shutil.copytree(REPO / folder, root / folder)
    (root / "interests").mkdir()
    (root / "interests" / "ai.yaml").write_text(
        """id: ai
description: Agents and evals.
themes:
  agents: [agent, agentic, tool calling]
  evals: [eval, evaluation, benchmark, llm judge]
sources:
  blog: {type: feed, url: "https://example.com/feed.xml"}
  lab:
    type: page
    index_url: https://lab.example/news
    link_pattern: 'href="(/news/[a-z0-9-]+)"'
    base_url: https://lab.example
    date_pattern: '([A-Z][a-z]{2} \\d{1,2}, \\d{4})'
  broken: {type: feed, url: "https://broken.example/feed"}
""",
        encoding="utf-8",
    )
    vault = tmp_path / "vault"
    vault.mkdir()
    settings = Settings(vault, tmp_path / "lib" / "library.sqlite",
                        ModelSettings("http://127.0.0.1:9/v1", "fake-model"))
    return root, settings


@pytest.fixture
def fetch() -> FakeFetch:
    return FakeFetch({
        "https://example.com/feed.xml": (FIXTURES / "feed.xml").read_bytes(),
        "https://lab.example/news": (FIXTURES / "page.html").read_bytes(),
        "https://broken.example/feed": SourceError("HTTP 403"),
    })
