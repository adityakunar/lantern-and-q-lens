from lantern.config import Interest, Lens, Taste, Vote
from lantern.items import Candidate, Item
from lantern.judge import judge
from lantern.model import ModelError, extract_json, strip_fence
from tests.conftest import FakeModel

INTEREST = Interest("ai", "Agents.", {"agents": [], "evals": []}, {})
LENS = Lens("news", "Score each article", "w")


def cands(n):
    out = []
    for i in range(n):
        c = Candidate(Item(f"https://x.test/{i}", f"Agent post {i}", "s"), i)
        c.reason = "matches agents"
        out.append(c)
    return out


def test_judge_scores_in_batches_of_ten():
    model = FakeModel()
    items = cands(23)
    assert judge(items, INTEREST, LENS, model) == 23
    assert len(model.calls) == 3
    assert items[0].score == 8 and items[0].theme == "agents"
    assert items[0].reason.startswith("scored 8/10: relevant")


def test_bad_replies_keep_the_keyword_ranking():
    model = FakeModel(judge='```json\n[{"id": 0, "score": 11, "reason": "x"},'
                            ' {"id": 1, "score": 5, "theme": "nonsense", "reason": "ok"},'
                            ' {"id": 99, "score": 5, "reason": "ghost"}]\n```')
    items = cands(3)
    assert judge(items, INTEREST, LENS, model) == 1
    assert items[0].score is None and items[0].reason == "matches agents"
    assert items[1].score == 5 and items[1].theme == "other"


def test_unparseable_reply_skips_the_batch():
    assert judge(cands(2), INTEREST, LENS, FakeModel(judge="I cannot help")) == 0


def test_json_helpers():
    assert strip_fence("```md\n# hi\n```") == "# hi"
    assert extract_json('Sure! [{"id": 1}] hope that helps') == [{"id": 1}]
    try:
        extract_json("nothing")
    except ModelError:
        pass
    else:
        raise AssertionError


TASTE = Taste("Lantern, a news pipeline.", {
    "own_stack": Vote(2, "Changes a project."),
    "marketing": Vote(-3, "Sells a product."),
})


def test_votes_are_added_by_code_and_clamped():
    model = FakeModel(judge='[{"id": 0, "score": 9, "theme": "agents", "reason": "new",'
                            ' "votes": ["own_stack", "own_stack", "made_up"]},'
                            ' {"id": 1, "score": 2, "reason": "ad", "votes": ["marketing"]},'
                            ' {"id": 2, "score": 6, "reason": "fine", "votes": "own_stack"}]')
    items = cands(3)
    assert judge(items, INTEREST, LENS, model, TASTE) == 3
    assert items[0].score == 10 and items[0].reason == "scored 10/10 (base 9, +2 own_stack): new"
    assert items[1].score == 0 and "(base 2, -3 marketing)" in items[1].reason
    assert items[2].score == 6 and items[2].reason == "scored 6/10: fine"
    system = model.calls[0][0]
    assert "What the reader is building:\nLantern" in system
    assert "- own_stack: Changes a project." in system


def test_no_taste_judges_as_before():
    model = FakeModel()
    items = cands(1)
    judge(items, INTEREST, LENS, model)
    assert "Votes:" not in model.calls[0][0]
