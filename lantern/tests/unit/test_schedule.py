"""The launchd schedule: plist template, weekly.sh gates and `lantern status`."""

import json
import os
import plistlib
import subprocess
from pathlib import Path

from lantern.cli import main

REPO = Path(__file__).parents[2]


def test_plist_runs_weekly_and_retries_hourly():
    text = (REPO / "scripts/launchd/dev.lantern.weekly.plist").read_text()
    plist = plistlib.loads(text.replace("__WEEKLY__", "/x/weekly.sh").encode())
    assert plist["Label"] == "dev.lantern.weekly"
    assert plist["ProgramArguments"] == ["/bin/bash", "/x/weekly.sh"]
    assert plist["StartCalendarInterval"] == {"Weekday": 1, "Hour": 7, "Minute": 0}
    assert plist["StartInterval"] == 3600 and plist["RunAtLoad"] is True


def run_weekly(tmp_path, *args):
    env = {**os.environ, "LANTERN_STATE": str(tmp_path), "LANTERN_RECIPES": "none",
           "LANTERN_PROBE_URL": "http://127.0.0.1:1"}  # nothing listens: offline
    return subprocess.run(["bash", REPO / "scripts/weekly.sh", *args], env=env,
                          capture_output=True, text=True, check=True)


def test_offline_records_health_without_running(tmp_path):
    out = run_weekly(tmp_path, "--force").stdout
    assert "offline, not running" in out and "-- none" not in out
    record = json.loads((tmp_path / "schedule.json").read_text())
    assert record["status"] == "offline" and record["attempts"] == 0


def test_done_week_is_skipped(tmp_path):
    week = subprocess.run(["date", "+%G-W%V"], capture_output=True, text=True).stdout.strip()
    (tmp_path / "schedule.json").write_text(json.dumps({"week": week, "attempts": 1,
                                                        "last_success_week": week}))
    assert run_weekly(tmp_path).stdout == ""


def test_status_reports_record(workspace, tmp_path, capsys, monkeypatch):
    _, settings = workspace
    cfg = tmp_path / "settings.yaml"
    cfg.write_text(f"vault: {settings.vault}\nlibrary: {tmp_path / 'lib.sqlite'}\n")
    assert main(["--settings", str(cfg), "status"]) == 1
    assert "never ran" in capsys.readouterr().out
    (tmp_path / "schedule.json").write_text(json.dumps({
        "week": "2026-W44", "status": "ok", "detail": "ai-weekly", "attempts": 1,
        "last_attempt": "2026-10-26T06:02:00Z", "last_success": "2026-10-26T06:09:00Z",
        "last_success_week": "2026-W44", "log": "weekly.log"}))
    main(["--settings", str(cfg), "status"])
    out = capsys.readouterr().out
    assert "schedule: ok for 2026-W44" in out and "last success: 2026-10-26T06:09:00Z" in out


def test_status_reads_while_a_run_holds_the_library(workspace, tmp_path, capsys):
    _, settings = workspace
    lib = tmp_path / "lib.sqlite"
    cfg = tmp_path / "settings.yaml"
    cfg.write_text(f"vault: {settings.vault}\nlibrary: {lib}\n")
    from lantern.library import Library

    with Library(lib) as writer:  # a run in progress, mid-transaction
        writer.db.execute("INSERT INTO runs (recipe, started, period_start, period_end, status)"
                          " VALUES ('ai-weekly', '2026-11-01T18:58', 'a', 'b', 'running')")
        main(["--settings", str(cfg), "status"])
    assert "Traceback" not in capsys.readouterr().err
