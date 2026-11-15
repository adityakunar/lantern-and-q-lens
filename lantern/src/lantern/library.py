"""The Library: one SQLite file holding items, runs, decisions and notes (docs/design.md)."""

from __future__ import annotations

import fcntl
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .items import Candidate, Item, normalize_url

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY, url_key TEXT UNIQUE NOT NULL, url TEXT NOT NULL, title TEXT NOT NULL,
    source TEXT NOT NULL, interest TEXT NOT NULL, published TEXT, excerpt TEXT NOT NULL,
    words INTEGER, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY, recipe TEXT NOT NULL, started TEXT NOT NULL, finished TEXT,
    period_start TEXT NOT NULL, period_end TEXT NOT NULL, model_used INTEGER, status TEXT NOT NULL,
    sources_ok INTEGER, sources_failed TEXT, seconds REAL, model_calls INTEGER,
    input_tokens INTEGER, output_tokens INTEGER, cost_usd REAL);
CREATE TABLE IF NOT EXISTS decisions (
    run_id INTEGER NOT NULL REFERENCES runs, item_id INTEGER NOT NULL REFERENCES items,
    stage TEXT NOT NULL, outcome TEXT NOT NULL, heuristic REAL, score INTEGER, theme TEXT,
    reason TEXT NOT NULL, PRIMARY KEY (run_id, item_id));
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY, recipe TEXT NOT NULL, path TEXT NOT NULL,
    run_id INTEGER NOT NULL REFERENCES runs, written TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS inclusions (
    note_id TEXT NOT NULL REFERENCES notes, item_id INTEGER NOT NULL REFERENCES items,
    position INTEGER NOT NULL, role TEXT NOT NULL, story INTEGER,
    PRIMARY KEY (note_id, item_id));
CREATE TABLE IF NOT EXISTS stories (
    note_id TEXT NOT NULL REFERENCES notes, position INTEGER NOT NULL, headline TEXT NOT NULL,
    themes TEXT NOT NULL, caveat TEXT, why TEXT, PRIMARY KEY (note_id, position));
"""

# Columns added after the first release; older libraries get them on first open.
ADDED_RUN_COLUMNS = {"seconds": "REAL", "model_calls": "INTEGER", "input_tokens": "INTEGER",
                     "output_tokens": "INTEGER", "cost_usd": "REAL"}


class LockHeld(Exception):
    """Another run is using the library."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Library:
    def __init__(self, path: Path | str, *, lock: bool = True) -> None:
        self.path = Path(path)
        self._lock_file = None
        if str(path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if lock:
                self._lock_file = open(f"{self.path}.lock", "w")  # noqa: SIM115
                try:
                    fcntl.flock(self._lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    self._lock_file.close()
                    raise LockHeld(f"another Lantern run is using {self.path}") from exc
        if lock or str(path) == ":memory:":
            self.db = sqlite3.connect(str(path))
            self.db.executescript(SCHEMA)
            have = {row[1] for row in self.db.execute("PRAGMA table_info(runs)")}
            for column, kind in ADDED_RUN_COLUMNS.items():
                if column not in have:
                    self.db.execute(f"ALTER TABLE runs ADD COLUMN {column} {kind}")
        else:  # a reader (why, status): read-only, waits out a running run's commit
            self.db = sqlite3.connect(f"{self.path.resolve().as_uri()}?mode=ro", uri=True,
                                      timeout=10)
        self.db.row_factory = sqlite3.Row

    @classmethod
    def scratch_copy(cls, path: Path) -> Library:
        """An in-memory copy for dry runs: same answers, nothing written back."""
        copy = cls(":memory:")
        if path.exists():
            source = sqlite3.connect(str(path))
            source.backup(copy.db)
            source.close()
        return copy

    def close(self) -> None:
        self.db.commit()
        self.db.close()
        if self._lock_file:
            fcntl.flock(self._lock_file, fcntl.LOCK_UN)
            self._lock_file.close()

    def __enter__(self) -> Library:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def upsert_item(self, item: Item, interest: str) -> tuple[int, str]:
        """Store or refresh an item; returns its id and when it was first seen."""
        now = _now()
        published = item.published.isoformat() if item.published else None
        self.db.execute(
            """INSERT INTO items (url_key, url, title, source, interest, published, excerpt, words,
                                  first_seen, last_seen)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(url_key) DO UPDATE SET last_seen = excluded.last_seen,
                 published = COALESCE(items.published, excluded.published),
                 words = COALESCE(excluded.words, items.words)""",
            (item.key, item.url, item.title, item.source, interest, published, item.excerpt,
             item.words, now, now),
        )
        row = self.db.execute(
            "SELECT id, first_seen FROM items WHERE url_key = ?", (item.key,)
        ).fetchone()
        return row["id"], row["first_seen"]

    def stored(self, item_id: int) -> tuple[str, str]:
        """The item's title and excerpt as the library keeps them."""
        row = self.db.execute(
            "SELECT title, excerpt FROM items WHERE id = ?", (item_id,)
        ).fetchone()
        return (row["title"], row["excerpt"]) if row else ("", "")

    def set_article(self, item_id: int, title: str, excerpt: str) -> None:
        """Keep what was read from the article itself (enrich.py), so it is read only once."""
        self.db.execute(
            "UPDATE items SET title = COALESCE(NULLIF(?, ''), title),"
            " excerpt = COALESCE(NULLIF(?, ''), excerpt) WHERE id = ?",
            (title, excerpt, item_id),
        )

    def start_run(self, recipe: str, period_start: datetime, period_end: datetime) -> int:
        cursor = self.db.execute(
            "INSERT INTO runs (recipe, started, period_start, period_end, status) "
            "VALUES (?, ?, ?, ?, 'running')",
            (recipe, _now(), period_start.isoformat(), period_end.isoformat()),
        )
        return int(cursor.lastrowid)

    def finish_run(self, run_id: int, *, status: str, model_used: bool, sources_ok: int,
                   sources_failed: dict[str, str], cost: dict[str, Any] | None = None) -> None:
        """Close a run; `cost` holds seconds, model_calls, input/output_tokens and cost_usd."""
        cost = cost or {}
        self.db.execute(
            "UPDATE runs SET finished = ?, status = ?, model_used = ?, sources_ok = ?, "
            "sources_failed = ?, seconds = ?, model_calls = ?, input_tokens = ?, "
            "output_tokens = ?, cost_usd = ? WHERE id = ?",
            (_now(), status, int(model_used), sources_ok, json.dumps(sources_failed),
             *(cost.get(k) for k in ADDED_RUN_COLUMNS), run_id),
        )
        self.db.commit()

    def record(self, run_id: int, candidate: Candidate, stage: str, outcome: str) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, candidate.item_id, stage, outcome, candidate.heuristic, candidate.score,
             candidate.theme, candidate.reason),
        )

    def included_elsewhere(self, note_id: str) -> set[int]:
        rows = self.db.execute(
            "SELECT item_id FROM inclusions WHERE note_id != ?", (note_id,)
        ).fetchall()
        return {r["item_id"] for r in rows}

    def note_for(self, item_id: int) -> str | None:
        row = self.db.execute(
            "SELECT note_id FROM inclusions WHERE item_id = ? LIMIT 1", (item_id,)
        ).fetchone()
        return row["note_id"] if row else None

    def save_note(self, note_id: str, recipe: str, path: str, run_id: int,
                  inclusions: list[tuple[int, str, int | None]],
                  stories: list[dict[str, Any]]) -> None:
        """Replace a note's record (reruns in the same week rewrite it)."""
        for table in ("inclusions", "stories"):
            self.db.execute(f"DELETE FROM {table} WHERE note_id = ?", (note_id,))
        self.db.execute(
            "INSERT OR REPLACE INTO notes VALUES (?, ?, ?, ?, ?)",
            (note_id, recipe, path, run_id, _now()),
        )
        self.db.executemany(
            "INSERT INTO inclusions VALUES (?, ?, ?, ?, ?)",
            [(note_id, item_id, pos, role, story)
             for pos, (item_id, role, story) in enumerate(inclusions)],
        )
        self.db.executemany(
            "INSERT INTO stories VALUES (?, ?, ?, ?, ?, ?)",
            [(note_id, s["position"], s["headline"], json.dumps(s["themes"]), s.get("caveat"),
              s.get("why")) for s in stories],
        )

    def why(self, url: str) -> list[sqlite3.Row]:
        return self.db.execute(
            """SELECT r.started, r.recipe, d.stage, d.outcome, d.score, d.reason,
                      (SELECT note_id FROM inclusions i WHERE i.item_id = d.item_id LIMIT 1)
                        AS note
               FROM decisions d JOIN runs r ON r.id = d.run_id JOIN items it ON it.id = d.item_id
               WHERE it.url_key = ? ORDER BY r.id DESC""",
            (normalize_url(url),),
        ).fetchall()

    def last_runs(self) -> list[sqlite3.Row]:
        """Each recipe's latest run."""
        return self.db.execute(
            """SELECT * FROM runs
               WHERE id IN (SELECT MAX(id) FROM runs GROUP BY recipe) ORDER BY recipe"""
        ).fetchall()
