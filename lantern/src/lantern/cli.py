"""`lantern run | why | check | status | benchmark` (contracts/cli.md)."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import UTC, datetime, time
from pathlib import Path

from .config import ConfigError, load_interest, load_recipe, load_settings, load_taste
from .inputs import INPUTS
from .items import SourceError
from .library import Library, LockHeld
from .net import Fetcher
from .outputs.obsidian import VaultMissing


def _default_settings() -> str:
    """LANTERN_SETTINGS if set, else ./lantern.yaml if present, else ~/.config/lantern.yaml."""
    if env := os.environ.get("LANTERN_SETTINGS"):
        return env
    return "lantern.yaml" if os.path.exists("lantern.yaml") else os.path.expanduser(
        "~/.config/lantern.yaml"
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lantern", description="Your weekly news, your model.")
    parser.add_argument("--settings", default=_default_settings())
    parser.add_argument("--root", default=".", help="folder holding interests/, recipes/, lenses/")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run a recipe and write its note")
    run.add_argument("recipe")
    run.add_argument("--until", help="end of the window, YYYY-MM-DD (default: now)")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--no-model", action="store_true")
    why = sub.add_parser("why", help="explain what happened to a link")
    why.add_argument("url")
    check = sub.add_parser("check", help="validate config; with an interest, try its sources")
    check.add_argument("interest", nargs="?")
    sub.add_parser("status", help="how the weekly schedule and the last runs went")
    sub.add_parser("benchmark", help="rewrite Lantern/Benchmark.md: cost and time of each note")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.root)
    try:
        settings = load_settings(Path(args.settings))
        if args.command == "run":
            from .run import run

            until = None
            if args.until:
                day = datetime.strptime(args.until, "%Y-%m-%d").date()
                until = datetime.combine(day, time(23, 59, 59), UTC)
            run(root, settings, args.recipe, until=until, dry_run=args.dry_run,
                no_model=args.no_model)
        elif args.command == "why":
            _why(settings, args.url)
        elif args.command == "status":
            return _status(settings)
        elif args.command == "benchmark":
            from .benchmark import write

            if not settings.vault.is_dir():
                raise VaultMissing(f"vault folder not found: {settings.vault}")
            print(f"benchmark: {write(settings.vault)}")
        else:
            _check(root, args.interest)
    except ConfigError as exc:
        for error in exc.errors:
            print(f"config: {error}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (VaultMissing, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except LockHeld as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    return 0


def _why(settings, url: str) -> None:
    if not settings.library.exists():
        print("never seen")
        return
    with Library(settings.library, lock=False) as library:
        rows = library.why(url)
    if not rows:
        print("never seen")
    for r in rows:
        score = f" {r['score']}/10" if r["score"] is not None else ""
        note = f" (in {r['note']})" if r["note"] else ""
        print(f"{r['started'][:10]} {r['recipe']} {r['stage']} {r['outcome']}{score} — "
              f"{r['reason']}{note}")


def _status(settings) -> int:
    """Print the schedule's health record (scripts/weekly.sh) and each recipe's last run.

    Exit 0 when healthy, 1 when the schedule needs a look."""
    state = Path(os.environ.get("LANTERN_STATE", settings.library.parent))
    path = state / "schedule.json"
    record = json.loads(path.read_text()) if path.exists() else None
    if record is None:
        print("schedule: never ran (install it with scripts/install-schedule.sh)")
    else:
        print(f"schedule: {record['status']} for {record['week']} "
              f"(attempt {record['attempts']}, last {record['last_attempt']})")
        print(f"  {record['detail']}")
        print(f"  last success: {record['last_success'] or 'never'}    log: {record['log']}")
    if settings.library.exists():
        try:
            with Library(settings.library, lock=False) as library:
                runs = library.last_runs()
        except sqlite3.OperationalError as exc:
            print(f"library: busy, a run is writing to it ({exc}); try again shortly")
            runs = []
        for r in runs:
            writer = "model" if r["model_used"] else "fallback"
            failed = len(json.loads(r["sources_failed"] or "[]"))
            took = ""
            if "seconds" in r.keys() and r["seconds"] is not None:
                took = f", {r['seconds']:.0f} s"
                if r["cost_usd"] is not None:
                    took += f", ${r['cost_usd']:.2f}"
            print(f"{r['recipe']}: {r['started'][:16]} {r['status']}, {writer}, "
                  f"{r['sources_ok']} sources ok, {failed} failed{took}")
    healthy = _schedule_healthy(record, datetime.now(UTC))
    print("verdict: " + ("healthy" if healthy else "needs a look"))
    return 0 if healthy else 1


def _schedule_healthy(record: dict | None, now: datetime) -> bool:
    """Whether the weekly schedule is doing its job, judged from its health record."""
    if record is None:
        return False
    # TODO(human)
    return record["status"] == "ok"


def _check(root: Path, interest_id: str | None) -> None:
    errors: list[str] = []
    for path in sorted((root / "recipes").glob("*.yaml")):
        try:
            load_recipe(root, path.stem)
        except ConfigError as exc:
            errors += exc.errors
    try:
        load_taste(root)
    except ConfigError as exc:
        errors += exc.errors
    ids = [interest_id] if interest_id else [p.stem for p in (root / "interests").glob("*.yaml")]
    interests = []
    for i in ids:
        try:
            interests.append(load_interest(root, i))
        except ConfigError as exc:
            errors += exc.errors
    if errors:
        raise ConfigError(errors)
    print("config: ok")
    if not interest_id:
        return
    fetch = Fetcher()
    for name, cfg in interests[0].sources.items():
        try:
            items = INPUTS[cfg["type"]].collect(name, cfg, fetch)
        except SourceError as exc:
            print(f"{name}: failed: {exc}")
            continue
        dates = [i.published for i in items if i.published]
        newest = f", newest {max(dates):%Y-%m-%d}" if dates else ", no dates"
        print(f"{name}: ok {len(items)} items{newest}")


if __name__ == "__main__":
    sys.exit(main())
