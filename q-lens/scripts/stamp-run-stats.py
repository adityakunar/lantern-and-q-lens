#!/usr/bin/env python3
"""Add the run's cost and time to a fetched note, so Lantern's benchmark can compare them.

    ant beta:sessions retrieve --session-id "$SID" --format json | scripts/stamp-run-stats.py NOTE.md

Writes run_session, run_model, run_seconds (active time), run_wall_seconds, run_tokens_in,
run_tokens_out and run_cost_usd into the note's front matter, replacing older values. Fields the
session doesn't report are left out. Never fails the fetch: problems go to stderr.
"""
import json
import re
import sys
from datetime import datetime


def stats(session):
    usage = session.get("usage") or {}
    out = {"run_session": session.get("id")}
    agent = session.get("agent")
    model = agent.get("model") if isinstance(agent, dict) else None
    out["run_model"] = model.get("id") if isinstance(model, dict) else model
    if isinstance(usage.get("active_seconds"), (int, float)):
        out["run_seconds"] = round(usage["active_seconds"])
    try:
        start = datetime.fromisoformat(session["created_at"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(session["updated_at"].replace("Z", "+00:00"))
        out["run_wall_seconds"] = round((end - start).total_seconds())
    except (KeyError, AttributeError, TypeError, ValueError):
        pass
    tokens_in = [v for k, v in usage.items() if k.endswith("input_tokens") and isinstance(v, int)]
    if tokens_in:
        out["run_tokens_in"] = sum(tokens_in)
    if isinstance(usage.get("output_tokens"), int):
        out["run_tokens_out"] = usage["output_tokens"]
    cost = usage.get("list_cost")
    amount = cost.get("amount") if isinstance(cost, dict) else None
    if isinstance(amount, (int, float, str)):
        out["run_cost_usd"] = round(float(amount) / 100, 2)  # the Console reports cents
    return {k: v for k, v in out.items() if v is not None}


def stamp(text, fields):
    if not text.startswith("---\n") or "\n---" not in text[3:]:
        return None
    end = text.index("\n---", 3)
    head = [line for line in text[4:end].split("\n")
            if line and not any(line.startswith(k + ":") for k in fields)]
    head += [f"{k}: {json.dumps(v)}" for k, v in fields.items()]
    return "---\n" + "\n".join(head) + text[end:]


def main():
    try:
        fields = stats(json.load(sys.stdin))
        path = sys.argv[1]
        text = open(path, encoding="utf-8").read()
        new = stamp(text, fields)
        if new is None:
            print(f"stamp: {path} has no front matter; left as is", file=sys.stderr)
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(new)
        shown = ", ".join(f"{k.removeprefix('run_')} {v}" for k, v in fields.items()
                          if k != "run_session")
        print(f"Run stats: {shown}")
    except Exception as exc:  # noqa: BLE001 - stats are a bonus, the note matters more
        print(f"stamp: could not add run stats ({type(exc).__name__}: {exc})", file=sys.stderr)


if __name__ == "__main__":
    main()
