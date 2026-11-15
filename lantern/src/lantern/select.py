"""Deterministic filtering and ranking, then the budget (research R6). No model calls."""

from __future__ import annotations

import re
from datetime import datetime, time

from .config import Interest, Recipe
from .items import Candidate

# The model judges every item that passes the plain filters. The keyword ranking only orders
# them (and decides when the model is down); this cap is a guard against a flood, such as a
# fresh library, not a cut a normal week reaches (about 180 items in Nov 2026).
MAX_JUDGED = 300

# Ported from reference/pre-reset research_pipeline/tools/pipeline/score.py.
_TITLE_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "in", "into", "is",
    "it", "its", "new", "of", "on", "or", "our", "the", "this", "to", "we", "what", "why",
    "with", "you", "your",
}


def _words(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def near_duplicate(title: str, other: str) -> bool:
    """Catch syndications and cross-posts without merging merely related articles."""
    if title.strip().casefold() == other.strip().casefold():
        return True
    left, right = _words(title) - _TITLE_STOP_WORDS, _words(other) - _TITLE_STOP_WORDS
    if not left or not right:
        return False
    shared = len(left & right)
    return shared >= 3 and shared / min(len(left), len(right)) >= 0.8


def in_window(published: datetime, start: datetime, end: datetime) -> bool:
    if published.time() == time(0, 0):  # date-only publishers: compare days, not instants
        return start.date() <= published.date() <= end.date()
    return start <= published <= end


def score_heuristic(candidate: Candidate, interest: Interest, end: datetime) -> None:
    title = candidate.item.title.lower()
    body = candidate.item.excerpt.lower()
    best, total, matched = "other", 0.0, []
    best_hits = 0.0
    for theme, aliases in interest.themes.items():
        hits = 0.0
        for phrase in {theme.replace("-", " "), *aliases}:
            pattern = rf"\b{re.escape(phrase)}s?\b"
            hits += 2 * bool(re.search(pattern, title)) + bool(re.search(pattern, body))
        if hits:
            matched.append(theme)
            total += hits
            if hits > best_hits:
                best, best_hits = theme, hits
    if published := candidate.item.published:
        age_days = (end - published).total_seconds() / 86400
        total += 1.0 if age_days <= 2 else 0.5 if age_days <= 5 else 0.0
    candidate.heuristic, candidate.theme, candidate.matches = total, best, matched
    candidate.reason = (
        "matches " + ", ".join(matched[:3]) if matched else "from a followed source; no theme match"
    )


def prefilter(
    candidates: list[Candidate], interest: Interest, *, start: datetime, end: datetime,
    new_ids: set[int], seen_elsewhere: set[int],
) -> tuple[list[Candidate], list[tuple[Candidate, str]]]:
    """Return ranked survivors (at most MAX_JUDGED) and every exclusion with its stage."""
    excluded: list[tuple[Candidate, str]] = []
    kept: list[Candidate] = []
    seen_ids: set[int] = set()
    # A cross-post of something already shown counts as shown, so twins are checked against it.
    shown = [c for c in candidates if c.item_id in seen_elsewhere]
    for c in sorted(candidates, key=lambda c: c.item_id):
        if c.item_id in seen_ids:
            continue
        seen_ids.add(c.item_id)
        published = c.item.published
        if published is None and c.item_id not in new_ids:
            c.reason = "undated and already seen in an earlier run"
            excluded.append((c, "window"))
        elif published is not None and not in_window(published, start, end):
            c.reason = f"published {published:%d %b %Y}, outside {start:%d %b}–{end:%d %b}"
            excluded.append((c, "window"))
        elif c.item_id in seen_elsewhere:
            c.reason = "already included in an earlier note"
            excluded.append((c, "seen"))
        elif twin := next(
            (k for k in kept + shown if near_duplicate(c.item.title, k.item.title)), None
        ):
            c.reason = f"duplicate of {twin.item.url}"
            excluded.append((c, "duplicate"))
        elif c.item.sponsored:
            c.reason = "marked as sponsored by the source"
            excluded.append((c, "sponsored"))
        else:
            score_heuristic(c, interest, end)
            kept.append(c)
    kept.sort(key=lambda c: (-c.heuristic, c.item_id))
    for c in kept[MAX_JUDGED:]:
        c.reason = f"ranked below the top {MAX_JUDGED} by keyword match and recency"
        excluded.append((c, "rank"))
    return kept[:MAX_JUDGED], excluded


def pick(
    candidates: list[Candidate], recipe: Recipe, *, judged: bool
) -> tuple[list[Candidate], list[tuple[Candidate, str]]]:
    """Apply score threshold, per-source cap and budget. Returns (included, excluded)."""
    order = sorted(
        candidates,
        key=lambda c: (-(c.score if judged and c.score is not None else -1), -c.heuristic,
                       c.item_id),
    )
    included: list[Candidate] = []
    excluded: list[tuple[Candidate, str]] = []
    per_source: dict[str, int] = {}
    for c in order:
        if judged and c.score is not None and c.score < recipe.min_score:
            excluded.append((c, "judge"))
        elif per_source.get(c.item.source, 0) >= recipe.per_source_cap:
            c.reason = f"{c.reason} (source cap of {recipe.per_source_cap} reached)"
            excluded.append((c, "budget"))
        elif len(included) >= recipe.budget:
            c.reason = f"{c.reason} (weekly budget of {recipe.budget} full)"
            excluded.append((c, "budget"))
        else:
            included.append(c)
            per_source[c.item.source] = per_source.get(c.item.source, 0) + 1
    return included, excluded
