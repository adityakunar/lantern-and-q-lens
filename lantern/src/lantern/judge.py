"""Model judging: a score and a one-line reason per candidate (research R7)."""

from __future__ import annotations

import json

from .config import Interest, Lens, Taste
from .items import Candidate
from .model import ModelError, extract_json

BATCH = 10


def judge(
    candidates: list[Candidate], interest: Interest, lens: Lens, model, taste: Taste | None = None,
) -> int:
    """Score candidates in place; returns how many got a valid model score."""
    system = (
        f"{lens.judge}\n\nWhat the reader cares about:\n{interest.description}\n\n"
        f"Themes: {', '.join(interest.themes)}, other"
    )
    votes = taste.votes if taste else {}
    if taste and taste.building:
        system += f"\n\nWhat the reader is building:\n{taste.building}"
    if votes:
        system += (
            "\n\nVotes: also add a \"votes\" list to each object with the ids of the traits"
            " below that clearly apply to the article (an empty list if none). Score the article"
            " as before; the votes are added to your score afterwards, so do not count them twice."
            + "".join(f"\n- {vid}: {v.when}" for vid, v in votes.items())
        )
    judged = 0
    for start in range(0, len(candidates), BATCH):
        batch = candidates[start : start + BATCH]
        payload = [
            {"id": c.item_id, "title": c.item.title, "source": c.item.source,
             "date": f"{c.item.published:%Y-%m-%d}" if c.item.published else "undated",
             "excerpt": c.item.excerpt[:500]}
            for c in batch
        ]
        try:
            reply = extract_json(model.chat(system, json.dumps(payload, ensure_ascii=False)))
        except ModelError:
            continue  # this batch keeps its keyword ranking
        by_id = {c.item_id: c for c in batch}
        for entry in reply if isinstance(reply, list) else []:
            c = by_id.get(entry.get("id")) if isinstance(entry, dict) else None
            score, reason = (entry.get("score"), entry.get("reason")) if c else (None, None)
            if c is None or not isinstance(score, int) or not 0 <= score <= 10 or not reason:
                continue
            said = entry.get("votes")
            said = said if isinstance(said, list) else []
            applied = list(dict.fromkeys(v for v in said if isinstance(v, str) and v in votes))
            final = max(0, min(10, score + sum(votes[v].points for v in applied)))
            c.score = final
            shown = "".join(f", {votes[v].points:+d} {v}" for v in applied)
            base = f" (base {score}{shown})" if applied else ""
            c.reason = f"scored {final}/10{base}: {str(reason).strip()[:200]}"
            theme = entry.get("theme")
            if theme in interest.themes or theme == "other":
                c.theme = theme
            judged += 1
    return judged
