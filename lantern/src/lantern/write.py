"""Writing the note: the model's version, its validation, and the fallback (note-format.md)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime

from .config import Interest, Lens, Recipe
from .items import Candidate, excerpt, normalize_url
from .model import ModelError, strip_fence

QUICK_HEADING = "Also worth a look"
_LINK = re.compile(r"\]\((https?://[^)\s]+)\)|(?<![(\[])\b(https?://[^\s)>\]]+)")


@dataclass
class NoteContext:
    recipe: Recipe
    interest: Interest
    start: datetime
    end: datetime
    items: list[Candidate]
    failed: dict[str, str]
    sources_total: int
    seen: int
    judged: int = 0
    model_name: str | None = None
    fallback_reason: str = ""

    @property
    def title_prefix(self) -> str:
        name = self.interest.id.upper() if len(self.interest.id) <= 3 else self.interest.id.title()
        return f"{name} · Week {self.end.isocalendar().week}"


@dataclass
class Written:
    body: str
    by_model: bool
    roles: list[tuple[int, str, int | None]] = field(default_factory=list)
    stories: list[dict] = field(default_factory=list)


def _date(c: Candidate, end: datetime) -> str:
    published = c.item.published
    if published is None:
        return "undated"
    return f"{published:%-d %b}" if published.year == end.year else f"{published:%-d %b %Y}"


def source_line(c: Candidate, end: datetime) -> str:
    parts = [c.item.source.replace("_", " "), _date(c, end)]
    if minutes := c.item.reading_minutes:
        parts.append(f"{minutes} min")
    return " · ".join(parts)


def run_details(ctx: NoteContext) -> str:
    reached = ctx.sources_total - len(ctx.failed)
    lines = [
        "> [!info]- Run details",
        f"> {reached} of {ctx.sources_total} sources reached · {ctx.seen} items seen · "
        f"{ctx.judged} judged · {len(ctx.items)} included.",
    ]
    if ctx.failed:
        failed = sorted(ctx.failed.items())
        lines.append("> Not reached: " + "; ".join(f"{name} ({why})" for name, why in failed))
    return "\n".join(lines)


def render_fallback(ctx: NoteContext) -> Written:
    out = [f"# {ctx.title_prefix}", ""]
    if not ctx.items:
        out += ["> [!info] A quiet week",
                "> Nothing new from your sources passed the filters this week.", ""]
    else:
        reason = ctx.fallback_reason or "the model wasn't reachable"
        out += ["> [!warning] Written without your model",
                f"> Because {reason}, items are ranked by keyword match and recency and shown "
                "with their own excerpts. Re-run once the model is up; the written note replaces "
                "this one.", ""]
    groups: dict[str, list[Candidate]] = {}
    for c in ctx.items:
        groups.setdefault(c.theme, []).append(c)
    order = [t for t in [*ctx.interest.themes, "other"] if t in groups]
    for theme in order:
        out += [f"## {theme.replace('-', ' ').capitalize()}", ""]
        for c in groups[theme]:
            out.append(f"- **[{_md(c.item.title)}]({c.item.url})** · {source_line(c, ctx.end)}")
            if c.item.excerpt:
                out.append(f"  {excerpt(c.item.excerpt)}")
            out.append(f"  *Why: {c.reason}*")
        out.append("")
    out.append(run_details(ctx))
    roles = [(c.item_id, "fallback", None) for c in ctx.items]
    return Written("\n".join(out) + "\n", False, roles, [])


def _md(text: str) -> str:
    return text.replace("[", "(").replace("]", ")")


def write_with_model(ctx: NoteContext, lens: Lens, model) -> Written:
    """Ask the model for the note body; validate it, retry once, else raise ModelError."""
    limits = (
        f"Limits: title line starting '# {ctx.title_prefix}: '; 1–{ctx.recipe.max_stories} "
        f"stories; at most {ctx.recipe.max_quick_links} quick links under "
        f"'## {QUICK_HEADING}'. Use every item exactly once. Do not write run details."
    )
    payload = {
        "period": f"{ctx.start:%Y-%m-%d} to {ctx.end:%Y-%m-%d}",
        "items": [
            {"id": c.item_id, "title": c.item.title, "url": c.item.url,
             "source_line": source_line(c, ctx.end), "theme": c.theme,
             "excerpt": c.item.excerpt[:600], "why": c.reason}
            for c in ctx.items
        ],
    }
    user = json.dumps(payload, ensure_ascii=False, indent=1)
    system = f"{lens.write}\n\n{limits}"
    problems: list[str] = []
    for _ in range(2):
        prompt = user if not problems else (
            user + "\n\nYour previous note broke these rules; fix them:\n- " + "\n- ".join(problems)
        )
        body = strip_fence(model.chat(system, prompt))
        problems = validate(body, ctx)
        if not problems:
            body = canonical_links(body, ctx)
            written = parse(body, ctx)
            written.body = body.rstrip() + "\n\n" + run_details(ctx) + "\n"
            return written
    raise ModelError("model note failed validation: " + "; ".join(problems))


_LINK_LINE = re.compile(r"^- \[.*?\]\((https?://[^)\s]+)\)(.*)$", re.M)


def canonical_links(body: str, ctx: NoteContext) -> str:
    """Rewrite the title prefix and each link line with what Lantern knows.

    Small models paraphrase titles, keep the template's <angle brackets> or name the wrong
    source; Lantern knows both, so only a quick link's one-line comment is the model's.
    """
    by_key = {normalize_url(c.item.url): c for c in ctx.items}

    def fix(m: re.Match) -> str:
        c = by_key.get(normalize_url(m.group(1)))
        if c is None:
            return m.group(0)
        rest = m.group(2).strip()
        comment = rest[1:].split(" · ", 1)[0].strip().strip("<>").strip() if rest[:1] == ":" else ""
        comment = f": {comment}" if comment else ""
        return f"- [{_md(c.item.title)}]({c.item.url}){comment} · {source_line(c, ctx.end)}"

    body = _LINK_LINE.sub(fix, body)
    body = theme_tags(body, ctx)
    # The model sometimes gets the week wrong; the prefix is Lantern's, the idea after it is not.
    first, _, rest = body.partition("\n")
    idea = first.removeprefix("# ").split(": ", 1)[1] if ": " in first else ""
    return f"# {ctx.title_prefix}: {idea}".rstrip(": ") + "\n" + rest


_TAG = re.compile(r"(?<!\S)#([\w-]+)(?![\w/-])")


def theme_tags(body: str, ctx: NoteContext) -> str:
    """Namespace the story tags by interest (#agents → #ai/agents) so they group in Obsidian."""
    known = {*ctx.interest.themes, "other"}

    def fix(m: re.Match) -> str:
        return f"#{ctx.interest.id}/{m.group(1)}" if m.group(1) in known else m.group(0)

    return _TAG.sub(fix, body)


def _sections(body: str) -> list[tuple[str, str]]:
    parts = re.split(r"^## (.+)$", body, flags=re.M)
    return list(zip(parts[1::2], parts[2::2], strict=True))


def validate(body: str, ctx: NoteContext) -> list[str]:
    problems = []
    if not body.startswith("# "):
        problems.append("the note must start with a '# ' title line")
    head = body.split("\n## ", 1)[0]
    callout = re.search(r"^> \[!abstract\][^\n]*\n((?:>[^\n]*\n?)*)", head, re.M)
    if not callout:
        problems.append("missing '> [!abstract] The week in 30 seconds' callout before the stories")
    elif len(re.findall(r"^> ?- ", callout.group(1), re.M)) != 3:
        problems.append("the 30-second callout must have exactly three bullet lines")
    sections = _sections(body)
    stories = [s for s in sections if s[0].strip() != QUICK_HEADING]
    quick = next((text for title, text in sections if title.strip() == QUICK_HEADING), "")
    if not 1 <= len(stories) <= ctx.recipe.max_stories:
        problems.append(f"write between 1 and {ctx.recipe.max_stories} stories")
    if len(re.findall(r"^- ", quick, re.M)) > ctx.recipe.max_quick_links:
        problems.append(f"at most {ctx.recipe.max_quick_links} quick links")
    if "Run details" in body:
        problems.append("do not write run details; Lantern adds them")
    expected = {normalize_url(c.item.url): c for c in ctx.items}
    counts: dict[str, int] = {}
    for m in _LINK.finditer(body):
        key = normalize_url(m.group(1) or m.group(2))
        counts[key] = counts.get(key, 0) + 1
    for key, n in counts.items():
        if key not in expected:
            problems.append(f"link not in the supplied items: {key}")
        elif n > 1:
            problems.append(f"link used {n} times, must be once: {key}")
    problems += [f"item missing from the note: {c.item.url}"
                 for key, c in expected.items() if key not in counts]
    if len(body.split()) > 1500:
        problems.append("keep the note under 1,500 words")
    return problems


def parse(body: str, ctx: NoteContext) -> Written:
    """Recover stories and each item's role so the Library (and the app) can use them."""
    by_key = {normalize_url(c.item.url): c for c in ctx.items}
    roles: list[tuple[int, str, int | None]] = []
    stories: list[dict] = []
    for title, text in _sections(body):
        keys = [normalize_url(m.group(1) or m.group(2)) for m in _LINK.finditer(text)]
        ids = [by_key[k].item_id for k in keys if k in by_key]
        if title.strip() == QUICK_HEADING:
            roles += [(i, "quick_link", None) for i in ids]
            continue
        position = len(stories)
        caveat = re.search(r"^> \[!warning\][^\n]*\n((?:>[^\n]*\n?)*)", text, re.M)
        why = re.search(r"\*Why you're seeing this: (.+?)\*", text)
        stories.append({
            "position": position,
            "headline": title.strip(),
            "themes": [t.rsplit("/", 1)[-1] for t in re.findall(r"(?<!\S)#([\w/-]+)", text)],
            "caveat": re.sub(r"^> ?", "", caveat.group(1), flags=re.M).strip() if caveat else None,
            "why": why.group(1).strip() if why else None,
        })
        roles += [(i, "story", position) for i in ids]
    return Written(body, True, roles, stories)
