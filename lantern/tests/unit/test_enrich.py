"""Reading a thin item's opening text from its own page (enrich.py)."""

from lantern.enrich import LIMIT, ArticleReader, join_parts, page_parts, page_title
from lantern.items import SourceError
from tests.conftest import FakeFetch

TAGLINE = "Example Lab is a research company building reliable and steerable AI systems."
BANNER = "New course! Enroll now in our agents course, starting next week for everyone."


def article(description: str, paragraph: str) -> bytes:
    return f"""<html><head>
<meta property="og:description" content="{description}">
<meta content="Short." name="description">
<script>var p = "<p>not this, it is inside a script tag and long enough to count</p>";</script>
</head><body><nav><p>Home, Research, Products, Company, Careers and the rest of the menu</p></nav>
<p>Hi</p><p>{BANNER}</p>
<p>{paragraph}</p></body></html>""".encode()


AGENTS = "Agents that plan before they call tools cut their failed tool calls in half."
JUDGES = "A study of LLM judges, with a new benchmark that shows where they disagree."
CARBON = article("Our next frontier model, built for cyber defenders and long-horizon work.",
                 "Today we are releasing a model that tops every leaderboard we track.")


def test_description_then_real_paragraphs():
    parts = page_parts(CARBON.decode())
    assert parts[0].startswith("Our next frontier model") and parts[-1].startswith("Today we")
    assert not any("script" in p or "menu" in p or p == "Hi" for p in parts)


def test_labels_and_empty_pages_give_nothing():
    assert page_parts('<meta name="description" content="Generative AI">') == []
    assert join_parts([]) == ""


def test_long_pages_are_capped():
    page = "".join(f"<p>{'word ' * 40}{n}</p>" for n in range(20))
    assert len(join_parts(page_parts(page))) == LIMIT


def test_site_text_is_dropped():
    fetch = FakeFetch({
        "https://lab.test/": article(TAGLINE, "Welcome to the home page of Example Lab, read on."),
        "https://lab.test/a": CARBON,
        "https://lab.test/b": article(TAGLINE, AGENTS),
        "https://lab.test/c": article(JUDGES, "We release a benchmark and show where judges fail."),
    })
    found = ArticleReader(fetch).read(["https://lab.test/a", "https://lab.test/b",
                                       "https://lab.test/c"])
    assert found["https://lab.test/a"][1].startswith("Our next frontier model")
    assert found["https://lab.test/b"][1] == AGENTS
    assert not any(BANNER in text or TAGLINE in text for _, text in found.values())
    assert fetch.calls.count("https://lab.test/") == 1


def test_robots_and_errors_leave_an_item_out():
    fetch = FakeFetch({"https://a.test/x": CARBON, "https://a.test/down": SourceError("HTTP 403")},
                      disallowed={"https://a.test/x"})
    assert ArticleReader(fetch).read(["https://a.test/x", "https://a.test/down"]) == {}
    assert "https://a.test/x" not in fetch.calls


def test_page_title():
    og = '<meta property="og:title" content="Gemini 4 Carbon: Our next model">'
    assert page_title(og + "<title>Ignored | DeepMind</title>") == "Gemini 4 Carbon: Our next model"
    assert page_title("<title>Files its S-1 \\ Anthropic</title>") == "Files its S-1"
    assert page_title("<title>Issue 377 | The Batch | DL.AI</title>") == "Issue 377 | The Batch"
    assert page_title('<meta property="og:title" content="Coding in Agent Mode - Arena.ai">'
                      ) == "Coding in Agent Mode"
    assert page_title("<p>no title</p>") == ""
