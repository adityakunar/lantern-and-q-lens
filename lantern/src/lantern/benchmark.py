"""`lantern benchmark`: one table comparing what each weekly note cost and how long it took.

Reads the run_* properties of every note under <vault>/Lantern, whether Lantern wrote it or Q Lens
did (its fetch script adds the same properties), and rewrites
<vault>/Lantern/Benchmark.md. Rebuilt from the notes each time, so it is safe to run often.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

FILE = "Benchmark.md"


def read_front(path: Path) -> dict[str, Any] | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    try:
        front = yaml.safe_load(text[4:end]) if end > 0 else None
    except yaml.YAMLError:
        return None
    return front if isinstance(front, dict) else None


def _topic(path: Path, folder: Path) -> str:
    """Short note name for an agent note: its topic folder ("AI news/Agent/2026-W44" -> "ai"),
    or the old file prefix for notes still named like "ai-weekly-2026-W44"."""
    parts = path.relative_to(folder).parts
    if len(parts) > 2:
        return parts[0].split()[0].lower()
    return path.stem.rsplit("-", 2)[0]


def rows(folder: Path) -> list[dict[str, Any]]:
    found = []
    for path in sorted(folder.rglob("*.md")):
        if path.name == FILE or path.name.startswith("."):
            continue
        front = read_front(path)
        if not front or "week" not in front or "run_writer" not in front:
            continue
        agent = "run_recipe" not in front
        name = str(front["run_recipe"]) if not agent else _topic(path, folder)
        found.append({
            "week": str(front["week"]),
            "note": name.removesuffix("-weekly"),
            "maker": "Agent" if agent else "Lantern",
            "writer": str(front.get("run_model") or front["run_writer"]),
            "items": front.get("run_items", front.get("run_events")),
            "seconds": front.get("run_seconds"),
            "cost": front.get("run_cost_usd"),
            "tokens_in": front.get("run_tokens_in"),
            "tokens_out": front.get("run_tokens_out"),
            "link": path.relative_to(folder).with_suffix("").as_posix(),
        })
    return sorted(found, key=lambda r: (r["week"], r["note"], r["maker"]), reverse=True)


def _money(value: Any) -> str:
    return f"${value:.2f}" if isinstance(value, int | float) else "?"


def _time(value: Any) -> str:
    if not isinstance(value, int | float):
        return "?"
    return f"{value:.0f} s" if value < 120 else f"{value / 60:.1f} min"


def _tokens(r: dict[str, Any]) -> str:
    if not isinstance(r["tokens_in"], int):
        return "?"
    return f"{r['tokens_in'] / 1000:.0f}k / {(r['tokens_out'] or 0) / 1000:.0f}k"


def render(found: list[dict[str, Any]]) -> str:
    lines = [
        "# Benchmark: Lantern and the news agent",
        "",
        "Rebuilt by `uv run lantern benchmark` from each note's `run_*` properties. Cost is the "
        "list price in US dollars. Time is wall-clock for Lantern and active time for the agent "
        "(its time spent working, not waiting). A ? means that run was made before logging "
        "started.",
        "",
    ]
    pairs = []
    for week in sorted({r["week"] for r in found}, reverse=True):
        mine = {r["maker"]: r for r in found if r["week"] == week and r["note"] == "ai"}
        a, b = mine.get("Lantern"), mine.get("Agent")
        if a and b and isinstance(a["cost"], int | float) and isinstance(b["cost"], int | float):
            ratio = f", {b['cost'] / a['cost']:.0f}x the cost" if a["cost"] else ""
            pairs.append(f"- **{week} AI note**: Lantern {_money(a['cost'])} in "
                         f"{_time(a['seconds'])}, agent {_money(b['cost'])} in "
                         f"{_time(b['seconds'])}{ratio}.")
    if pairs:
        lines += ["## AI note, side by side", "", *pairs, ""]
    lines += [
        "## Every note",
        "",
        "| Week | Note | Made by | Model | Items | Cost | Time | Tokens in / out |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for r in found:
        lines.append(
            f"| {r['week']} | [[{r['link']}\\|{r['note']}]] | {r['maker']} | {r['writer']} | "
            f"{r['items'] if r['items'] is not None else '?'} | {_money(r['cost'])} | "
            f"{_time(r['seconds'])} | {_tokens(r)} |"
        )
    return "\n".join(lines) + "\n"


def write(vault: Path) -> Path:
    folder = vault / "Lantern"
    target = folder / FILE
    text = "---\ntags: [lantern/benchmark]\n---\n\n" + render(rows(folder))
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".lantern-", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return target
