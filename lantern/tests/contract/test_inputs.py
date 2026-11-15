"""Every registered Input honours contracts/slots.md."""

from datetime import UTC, datetime

import pytest

from lantern.inputs import INPUTS
from lantern.items import Item, SourceError
from tests.conftest import FIXTURES, FakeFetch

CONFIGS = {
    "feed": {"type": "feed", "url": "https://example.com/feed.xml"},
    "page": {"type": "page", "index_url": "https://lab.example/news",
             "link_pattern": 'href="(/news/[a-z0-9-]+)"', "base_url": "https://lab.example",
             "date_pattern": r"([A-Z][a-z]{2} \d{1,2}, \d{4})"},
}
FETCH = FakeFetch({"https://example.com/feed.xml": (FIXTURES / "feed.xml").read_bytes(),
                   "https://lab.example/news": (FIXTURES / "page.html").read_bytes()})


@pytest.mark.parametrize("kind", sorted(INPUTS))
def test_collects_items_without_filtering(kind):
    items = INPUTS[kind].collect("src", CONFIGS[kind], FETCH)
    assert len(items) == 4 and all(isinstance(i, Item) and i.source == "src" for i in items)
    assert all(i.url.startswith("https://") and i.title for i in items)
    old = [i for i in items if i.published and i.published < datetime(2026, 10, 10, tzinfo=UTC)]
    assert len(old) == 1  # inputs never filter by date


@pytest.mark.parametrize("kind", sorted(INPUTS))
def test_failure_is_a_source_error(kind):
    with pytest.raises(SourceError):
        INPUTS[kind].collect("src", CONFIGS[kind], FakeFetch({}))


@pytest.mark.parametrize("kind", sorted(INPUTS))
def test_validate_accepts_good_config_and_flags_typos(kind):
    assert INPUTS[kind].validate(CONFIGS[kind]) == []
    errors = INPUTS[kind].validate({**CONFIGS[kind], "urll": 1})
    assert any("unknown key 'urll'" in e for e in errors)


def test_feed_details():
    items = {i.title: i for i in INPUTS["feed"].collect("b", CONFIGS["feed"], FETCH)}
    assert items["Sponsored: Try our GPU cloud"].sponsored
    assert items["A benchmark for LLM judges"].reading_minutes == 2
    assert items["Agents that plan with tool calling"].reading_minutes is None


def test_feed_max_mb_raises_the_size_limit():
    fetch = FakeFetch(FETCH.pages)
    INPUTS["feed"].collect("b", {**CONFIGS["feed"], "max_mb": 16}, fetch)
    assert fetch.limits["https://example.com/feed.xml"] == 16 * 1024 * 1024
    assert INPUTS["feed"].validate({**CONFIGS["feed"], "max_mb": 16}) == []
    assert INPUTS["feed"].validate({**CONFIGS["feed"], "max_mb": "big"})


def test_page_details_and_robots():
    items = INPUTS["page"].collect("lab", CONFIGS["page"], FETCH)
    assert items[0].url == "https://lab.example/news/claude-evals-update"
    assert items[0].title == "How we run evals on new models"
    assert f"{items[0].published:%Y-%m-%d}" == "2026-10-22"
    assert "/news" not in [i.url.removeprefix("https://lab.example") for i in items]
    blocked = FakeFetch(FETCH.pages, disallowed={"https://lab.example/news"})
    with pytest.raises(SourceError, match="robots"):
        INPUTS["page"].collect("lab", CONFIGS["page"], blocked)


def test_page_numeric_order_and_limit():
    html = b'<a href="/issue-7">x</a><a href="/issue-12">y</a><a href="/issue-9">z</a>'
    cfg = {"type": "page", "index_url": "https://n.test/", "link_pattern": r'href="(/issue-(\d+))"',
           "order": "numeric", "limit": 2}
    items = INPUTS["page"].collect("n", cfg, FakeFetch({"https://n.test/": html}))
    assert [i.url for i in items] == ["https://n.test/issue-12", "https://n.test/issue-9"]
    assert items[0].title == "Issue 12"


def test_page_dates_are_never_borrowed_from_the_next_post():
    html = (b'<a href="/p/featured">Featured post title</a><a href="/p/featured">teaser</a>'
            b'<a href="/p/dated">Dated post title</a><time>Oct 22, 2026</time>')
    cfg = {"type": "page", "index_url": "https://d.test/", "link_pattern": r'href="(/p/[a-z]+)"',
           "date_pattern": r"([A-Z][a-z]{2} \d{1,2}, \d{4})"}
    featured, dated = INPUTS["page"].collect("d", cfg, FakeFetch({"https://d.test/": html}))
    assert featured.published is None and f"{dated.published:%d}" == "22"
