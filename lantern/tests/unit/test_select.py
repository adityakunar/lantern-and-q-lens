from datetime import UTC, datetime, timedelta

from lantern.config import Interest, Recipe
from lantern.items import Candidate, Item
from lantern.select import MAX_JUDGED, near_duplicate, pick, prefilter

END = datetime(2026, 10, 25, 23, 59, tzinfo=UTC)
START = END - timedelta(days=7)
INTEREST = Interest("ai", "d", {"agents": ["agent", "tool calling"], "evals": ["benchmark"]}, {})
RECIPE = Recipe("r", ["ai"], "news", {}, budget=3, per_source_cap=2, min_score=4)


def cand(i, title, *, source="s", days_ago=1, sponsored=False, score=None):
    published = END - timedelta(days=days_ago) if days_ago is not None else None
    c = Candidate(Item(f"https://x.test/{i}", title, source, published, sponsored=sponsored), i)
    c.score = score
    return c


def test_prefilter_records_every_exclusion_with_a_reason():
    cands = [
        cand(1, "Agent tool calling at scale"),
        cand(2, "Agent tool calling at scale!"),  # near-duplicate
        cand(3, "Old benchmark", days_ago=30),
        cand(4, "Undated and old", days_ago=None),
        cand(5, "Undated but new", days_ago=None),
        cand(6, "Sponsored agent", sponsored=True),
        cand(7, "Already in a note"),
    ]
    kept, excluded = prefilter(cands, INTEREST, start=START, end=END, new_ids={5},
                               seen_elsewhere={7})
    assert [c.item_id for c in kept] == [1, 5]
    stages = {c.item_id: stage for c, stage in excluded}
    assert stages == {2: "duplicate", 3: "window", 4: "window", 6: "sponsored", 7: "seen"}
    assert all(c.reason for c, _ in excluded)
    assert kept[0].theme == "agents" and kept[0].reason.startswith("matches agents")


def test_date_only_items_count_on_the_window_edge():
    edge = cand(1, "x")
    edge.item.published = datetime(START.year, START.month, START.day, tzinfo=UTC)
    kept, _ = prefilter([edge], INTEREST, start=START, end=END, new_ids=set(), seen_elsewhere=set())
    assert kept


def test_prefilter_caps_what_the_model_judges():
    cands = [cand(i, f"Post {i}") for i in range(MAX_JUDGED + 5)]
    kept, excluded = prefilter(cands, INTEREST, start=START, end=END, new_ids=set(),
                               seen_elsewhere=set())
    assert len(kept) == MAX_JUDGED and sum(stage == "rank" for _, stage in excluded) == 5


def test_pick_applies_threshold_cap_and_budget():
    cands = [cand(1, "a", score=9), cand(2, "b", score=8), cand(3, "c", score=7),
             cand(4, "d", source="t", score=6), cand(5, "e", source="t", score=5),
             cand(6, "f", source="t", score=3)]
    included, excluded = pick(cands, RECIPE, judged=True)
    assert [c.item_id for c in included] == [1, 2, 4]
    assert {c.item_id: s for c, s in excluded} == {3: "budget", 5: "budget", 6: "judge"}
    assert "source cap" in cands[2].reason and "budget" in cands[4].reason


def test_near_duplicate():
    assert near_duplicate("OpenAI releases GPT-6 model today", "OpenAI releases GPT-6 model")
    assert not near_duplicate("Agents and evals", "Agents and memory")
