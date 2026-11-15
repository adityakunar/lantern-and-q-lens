import json
from datetime import UTC, datetime, timedelta

import pytest

from lantern.config import Interest, Lens, Recipe
from lantern.items import Candidate, Item
from lantern.model import ModelError
from lantern.write import (
    NoteContext,
    canonical_links,
    parse,
    render_fallback,
    validate,
    write_with_model,
)
from tests.conftest import FakeModel, good_note

END = datetime(2026, 10, 25, 23, 59, tzinfo=UTC)
LENS = Lens("news", "judge", "write")


def ctx(n=3, **extra):
    items = []
    for i in range(n):
        published = None if i == 2 else END - timedelta(days=i + 1)
        c = Candidate(Item(f"https://x.test/{i}", f"Title {i}", "my_blog", published,
                           excerpt="Excerpt.", words=500 if i == 0 else None), i + 1)
        c.theme, c.reason = ("agents" if i % 2 else "evals"), f"scored 8/10: reason {i}"
        items.append(c)
    return NoteContext(Recipe("ai-weekly", ["ai"], "news", {}),
                       Interest("ai", "d", {"agents": [], "evals": []}, {}),
                       END - timedelta(days=7), END, items, {"down": "HTTP 403"}, 3, 20, **extra)


def payload(c):
    from lantern.write import source_line
    return [{"title": i.item.title, "url": i.item.url, "theme": i.theme, "why": i.reason,
             "source_line": source_line(i, c.end)} for i in c.items]


def test_good_note_passes_and_parses_roles_and_stories():
    c = ctx()
    body = good_note(payload(c), c.title_prefix)
    assert c.title_prefix == "AI · Week 43"
    assert validate(body, c) == []
    written = parse(body, c)
    assert [role for _, role, _ in written.roles] == ["story", "story", "quick_link"]
    assert written.stories[0]["caveat"] == "Early results."
    assert written.stories[1]["themes"] == ["agents"]
    assert written.stories[0]["why"] == "scored 8/10: reason 0"


@pytest.mark.parametrize("breakage, problem", [
    (lambda b: b.replace("> - three\n", ""), "exactly three bullet"),
    (lambda b: b.replace("https://x.test/2", "https://elsewhere.test/2"), "not in the supplied"),
    (lambda b: b + "\n[again](https://x.test/0)", "used 2 times"),
    (lambda b: b.replace("> [!abstract] The week in 30 seconds", "Hi"), "missing '> [!abstract]"),
    (lambda b: b + "\n> [!info]- Run details", "do not write run details"),
    (lambda b: b + " word" * 1500, "under 1,500 words"),
    (lambda b: b.replace("# AI", "AI"), "'# ' title"),
])
def test_validation_catches_broken_notes(breakage, problem):
    c = ctx()
    problems = validate(breakage(good_note(payload(c), c.title_prefix)), c)
    assert any(problem in p for p in problems), problems


def test_too_many_stories():
    c = ctx(8)
    body = good_note(payload(c), c.title_prefix).replace("## Also worth a look\n", "")
    body = body.replace("\n- [Title", "\n## Extra\n- [Title")
    assert any("between 1 and 6" in p for p in validate(body, c))


def test_a_merged_story_with_two_links_passes():
    c = ctx(2)
    p = payload(c)
    body = good_note(p[:1], c.title_prefix).replace(
        "\n\n*Why", f"\n- [{p[1]['title']}]({p[1]['url']}) · x\n\n*Why")
    assert validate(body, c) == []
    assert [r for _, r, s in parse(body, c).roles] == ["story", "story"]


def test_model_note_retries_once_with_the_problems_then_succeeds():
    c = ctx()
    model = FakeModel(notes=["no title here"])
    written = write_with_model(c, LENS, model)
    assert written.by_model and "> [!info]- Run details" in written.body
    assert "previous note broke these rules" in model.calls[-1][1]
    assert "Not reached: down (HTTP 403)" in written.body


def test_model_note_gives_up_after_two_failures():
    with pytest.raises(ModelError, match="failed validation"):
        write_with_model(ctx(), LENS, FakeModel(notes=["bad", "still bad"]))


def test_fallback_note_groups_by_theme_and_says_why():
    c = ctx(fallback_reason="the local model wasn't reachable")
    written = render_fallback(c)
    body = written.body
    assert body.startswith("# AI · Week 43\n") and "[!warning] Written without your model" in body
    assert body.index("## Agents") < body.index("## Evals")  # interest's theme order
    assert "· undated" in body and "· 3 min" in body and "*Why: scored 8/10" in body
    for item in c.items:
        assert body.count(item.item.url) == 1
    assert {r for _, r, _ in written.roles} == {"fallback"}


def test_quiet_week_says_so():
    body = render_fallback(ctx(0)).body
    assert "A quiet week" in body and "0 included" in body


def test_payload_is_json_the_model_can_read():
    c = ctx()
    model = FakeModel()
    write_with_model(c, LENS, model)
    sent = json.loads(model.calls[0][1])
    assert sent["period"] == "2026-10-18 to 2026-10-25" and len(sent["items"]) == 3


def test_link_lines_get_the_real_title_and_source():
    c = ctx()
    body = ("# AI · Week 41: Agents grow up\n\n"
            "## Story\n\n- [<Short name>](https://x.test/0) · Wrong source · 1 Jan\n\n"
            "## Also worth a look\n- [<T>](https://x.test/1): <Worth it> · nope\n"
            "- [T](https://x.test/2)\n")
    lines = canonical_links(body, c).splitlines()
    assert lines[0] == "# AI · Week 43: Agents grow up"
    lines = lines[2:]
    from lantern.write import source_line
    assert lines[2] == f"- [Title 0](https://x.test/0) · {source_line(c.items[0], c.end)}"
    assert lines[5] == f"- [Title 1](https://x.test/1): Worth it · {source_line(c.items[1], c.end)}"
    assert lines[6] == f"- [Title 2](https://x.test/2) · {source_line(c.items[2], c.end)}"


def test_story_tags_are_namespaced_by_interest():
    c = ctx()
    body = canonical_links(good_note(payload(c), c.title_prefix), c)
    assert "\n#ai/evals\n" in body and "\n#ai/agents\n" in body and "\n#evals\n" not in body
    assert canonical_links(body, c) == body  # already namespaced tags are left alone
    assert parse(body, c).stories[1]["themes"] == ["agents"]
