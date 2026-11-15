"""The core: collect → library → filter → judge → write → deliver, for one recipe."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .config import Settings, load_interest, load_lens, load_recipe, load_taste
from .enrich import PER_SOURCE, ArticleReader, is_thin
from .inputs import INPUTS
from .items import Candidate, SourceError
from .judge import judge
from .library import Library
from .model import ModelClient, ModelError
from .net import Fetcher
from .outputs import OUTPUTS, RenderedNote, week_label
from .select import pick, prefilter
from .write import NoteContext, Written, render_fallback, write_with_model


@dataclass
class RunResult:
    location: str
    written: Written
    included: int


def run(
    root: Path, settings: Settings, recipe_id: str, *, until: datetime | None = None,
    dry_run: bool = False, no_model: bool = False, fetch=None, model=None,
    say: Callable[[str], None] = print,
) -> RunResult:
    clock = time.monotonic()
    recipe = load_recipe(root, recipe_id)
    interest = load_interest(root, recipe.interests[0])
    lens = load_lens(root, recipe.lens)
    taste = load_taste(root)
    output = OUTPUTS[recipe.output["type"]]
    end = until or datetime.now(UTC)
    start = end - timedelta(days=recipe.window_days)
    note_id = f"{recipe.id}/{week_label(end)}"
    fetch = fetch or Fetcher()
    if model is None and settings.model and not no_model:
        model = ModelClient(settings.model)
    if no_model:
        model = None

    library = Library.scratch_copy(settings.library) if dry_run else Library(settings.library)
    with library:
        run_id = library.start_run(recipe.id, start, end)
        started = library.db.execute(
            "SELECT started FROM runs WHERE id = ?", (run_id,)
        ).fetchone()[0]

        # Collect: every source is tried; a failure is recorded, never fatal.
        candidates: list[Candidate] = []
        new_ids: set[int] = set()
        failed: dict[str, str] = {}
        sources = {n: c for n, c in interest.sources.items() if c.get("enabled", True)}
        reader = ArticleReader(fetch)
        for name, cfg in sources.items():
            try:
                items = INPUTS[cfg["type"]].collect(name, cfg, fetch)
            except SourceError as exc:
                failed[name] = str(exc)
                say(f"{name}: failed: {exc}")
                continue
            listing = cfg["type"] == "page"  # titles from link text or the URL; take the page's
            thin: dict[str, tuple[Candidate, int]] = {}
            for item in items:
                item_id, first_seen = library.upsert_item(item, interest.id)
                if first_seen >= started:
                    new_ids.add(item_id)
                candidate = Candidate(item, item_id)
                candidates.append(candidate)
                if is_thin(item.excerpt) and not item.sponsored:
                    title, excerpt = library.stored(item_id)
                    item.excerpt = excerpt or item.excerpt
                    item.title = title if listing and title else item.title
                    if (is_thin(item.excerpt) and len(thin) < PER_SOURCE
                            and _recent(item, start, first_seen >= started)):
                        thin.setdefault(item.url, (candidate, item_id))
            found = reader.read(list(thin)) if thin else {}
            texts = 0
            for url, (title, text) in found.items():
                candidate, item_id = thin[url]
                title = title if listing else ""
                candidate.item.title = title or candidate.item.title
                candidate.item.excerpt = text or candidate.item.excerpt
                texts += bool(text)
                library.set_article(item_id, title, text)
            filled_note = f", {texts} excerpts read from the article" if texts else ""
            say(f"{name}: ok {len(items)} items{filled_note}")

        # Filter deterministically, then let the model judge what is left.
        kept, excluded = prefilter(
            candidates, interest, start=start, end=end, new_ids=new_ids,
            seen_elsewhere=library.included_elsewhere(note_id),
        )
        seen = len({c.item_id for c in candidates})
        usable = model is not None and model.available()
        if model is not None and not usable:
            problem = getattr(model, "problem", None) or "no reason given"
            say(f"model {model.name}: not available: {problem}")
        elif usable and getattr(model, "problem", None):
            say(f"model {model.name}: warning: {model.problem}")
        judged = judge(kept, interest, lens, model, taste) if usable and kept else 0
        included, dropped = pick(kept, recipe, judged=judged > 0)
        for c, stage in excluded + dropped:
            library.record(run_id, c, stage, "excluded")
        for c in included:
            library.record(run_id, c, "pick", "included")

        ctx = NoteContext(
            recipe, interest, start, end, included, failed, len(sources), seen, judged,
            model.name if usable else None,
        )
        if not usable:
            ctx.fallback_reason = (
                "you asked for a note without the model" if no_model or not settings.model
                else f"the model ({model.name}) wasn't reachable"
            )
        written = None
        if usable and included:
            try:
                written = write_with_model(ctx, lens, model)
            except ModelError as exc:
                say(f"model note rejected, writing the fallback: {exc}")
                ctx.fallback_reason = "the model's note broke the note format twice"
        written = written or render_fallback(ctx)

        cost = _cost(model, time.monotonic() - clock)
        note = RenderedNote(note_id, _frontmatter(ctx, written, run_id, cost), written.body, end)
        if dry_run:
            say(f"--- dry run: nothing written ---\n{written.body}")
            location = "(dry run)"
        else:
            location = output.deliver(note, recipe.output, settings)
            library.save_note(note_id, recipe.id, location, run_id, written.roles, written.stories)
        library.finish_run(
            run_id, status="ok", model_used=written.by_model,
            sources_ok=len(sources) - len(failed), sources_failed=failed, cost=cost,
        )
    say(f"note: {location} ({len(included)} items, {'model' if written.by_model else 'fallback'})")
    return RunResult(location, written, len(included))


def _recent(item, start: datetime, new: bool) -> bool:
    """Worth an article fetch: could still make this run's window (a day's slack for dates)."""
    if item.published is None:
        return new
    return item.published >= start - timedelta(days=1)


def _cost(model, seconds: float) -> dict:
    """What the run took: wall-clock seconds, model calls, tokens and list price in dollars."""
    cost: dict = {"seconds": round(seconds, 1)}
    usage = getattr(model, "usage", None)
    if usage is not None and usage.calls:
        cost.update(model_calls=usage.calls, input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens, cost_usd=usage.cost_usd(model.settings))
        if not usage.reported:  # the server sent no token counts: don't log zeros as facts
            cost.update(input_tokens=None, output_tokens=None)
    return cost


def _frontmatter(ctx: NoteContext, written: Written, run_id: int, cost: dict) -> dict:
    """Reader properties first; the run_* properties trace how the note was made."""
    roles = [role for _, role, _ in written.roles]
    minutes = sum(c.item.reading_minutes or 0 for c in ctx.items)
    if written.by_model:
        covered = {t for story in written.stories for t in story["themes"]}
    else:
        covered = {c.theme for c in ctx.items}
    themes = [t for t in ctx.interest.themes if t in covered]
    tags = [f"lantern/{ctx.interest.id}", *(f"{ctx.interest.id}/{t}" for t in themes)]
    if not written.by_model:
        tags.append("lantern/fallback")
    front = {
        "week": week_label(ctx.end),
        "period": _period(ctx.start, ctx.end),
        "reading_minutes": minutes or None,
        "tags": tags,
        "run_id": run_id,
        "run_recipe": ctx.recipe.id,
        "run_writer": ctx.model_name if written.by_model else "fallback",
        "run_generated": _human(datetime.now(UTC)),
        "run_sources_checked": ctx.sources_total,
        "run_sources_failed": [f"{name} ({why})" for name, why in sorted(ctx.failed.items())],
        "run_items_seen": ctx.seen,
        "run_items_judged": ctx.judged,
        "run_items": len(ctx.items),
        "run_stories": len(written.stories),
        "run_quick_links": roles.count("quick_link"),
        "run_seconds": cost.get("seconds"),
        "run_model_calls": cost.get("model_calls"),
        "run_tokens_in": cost.get("input_tokens"),
        "run_tokens_out": cost.get("output_tokens"),
        "run_cost_usd": cost.get("cost_usd"),
    }
    return {k: v for k, v in front.items() if v is not None}


def _period(start: datetime, end: datetime) -> str:
    start, end = start.astimezone(UTC), end.astimezone(UTC)
    first = f"{start:%-d %b %H:%M}" if start.year == end.year else f"{start:%-d %b %Y %H:%M}"
    return f"{first} → {end:%-d %b %Y %H:%M} UTC"


def _human(moment: datetime) -> str:
    return f"{moment.astimezone(UTC):%-d %b %Y %H:%M} UTC"
