"""End to end on fixtures: sources → library → note in the vault (quickstart scenarios)."""

from datetime import timedelta

import pytest
import yaml

from lantern.cli import main
from lantern.library import Library, LockHeld
from lantern.run import run
from tests.conftest import UNTIL, FakeModel


def read_note(settings, week="2026-W43"):
    text = (settings.vault / "Lantern" / "AI news" / "Lantern" / f"{week}.md").read_text()
    _, front, body = text.split("---\n", 2)
    return yaml.safe_load(front), body.lstrip("\n")


def test_model_written_note(workspace, fetch):
    root, settings = workspace
    lines = []
    result = run(root, settings, "ai-weekly", until=UNTIL, fetch=fetch, model=FakeModel(),
                 say=lines.append)
    front, body = read_note(settings)
    assert front["week"] == "2026-W43" and front["period"].endswith(" UTC")
    assert front["tags"][0] == "lantern/ai" and "lantern/fallback" not in front["tags"]
    assert all(t.startswith("ai/") for t in front["tags"][1:])
    assert front["run_writer"] == "fake-model" and front["run_recipe"] == "ai-weekly"
    assert front["run_sources_failed"] == ["broken (HTTP 403)"]
    assert front["run_sources_checked"] == 3 and isinstance(front["run_id"], int)
    # 4 in-window, non-sponsored, distinct items; "older" scored 2 by the fake judge
    assert front["run_items"] == result.included == 4
    assert front["run_stories"] == 2 and front["run_quick_links"] == 2
    assert front["reading_minutes"] == 2
    assert body.startswith("# AI · Week 43: ")
    assert "Not reached: broken (HTTP 403)" in body
    assert "gpu-cloud" not in body and "old-quantization" not in body
    assert body.count("agents-plan") == 1  # the cross-posted twin is dropped
    assert "broken: failed: HTTP 403" in lines and lines[-1].endswith("(4 items, model)")


def test_fallback_when_the_model_is_down(workspace, fetch):
    root, settings = workspace
    run(root, settings, "ai-weekly", until=UNTIL, fetch=fetch, model=FakeModel(up=False),
        say=lambda _: None)
    front, body = read_note(settings)
    assert front["run_writer"] == "fallback" and "lantern/fallback" in front["tags"]
    assert "Written without your model" in body and "wasn't reachable" in body


def test_invalid_model_note_twice_falls_back(workspace, fetch):
    root, settings = workspace
    model = FakeModel(notes=["nope", "still nope"])
    run(root, settings, "ai-weekly", until=UNTIL, fetch=fetch, model=model, say=lambda _: None)
    front, body = read_note(settings)
    assert front["run_writer"] == "fallback" and "broke the note format twice" in body


def test_rerun_replaces_and_next_week_skips_what_was_shown(workspace, fetch):
    root, settings = workspace
    quiet = {"say": lambda _: None, "fetch": fetch, "model": FakeModel()}
    run(root, settings, "ai-weekly", until=UNTIL, **quiet)
    run(root, settings, "ai-weekly", until=UNTIL, **quiet)  # same week: replaces, same items
    assert read_note(settings)[0]["run_items"] == 4
    nxt = run(root, settings, "ai-weekly", until=UNTIL + timedelta(days=3), **quiet)
    front, body = read_note(settings, "2026-W44")
    assert nxt.included == front["run_items"] == 0 and "A quiet week" in body


def test_dry_run_writes_nothing(workspace, fetch):
    root, settings = workspace
    lines = []
    run(root, settings, "ai-weekly", until=UNTIL, fetch=fetch, model=FakeModel(), dry_run=True,
        say=lines.append)
    assert not (settings.vault / "Lantern").exists() and not settings.library.exists()
    assert any("dry run" in line for line in lines)


def test_no_model_flag(workspace, fetch):
    root, settings = workspace
    model = FakeModel()
    run(root, settings, "ai-weekly", until=UNTIL, fetch=fetch, model=model, no_model=True,
        say=lambda _: None)
    assert model.calls == [] and read_note(settings)[0]["run_writer"] == "fallback"


def test_library_explains_decisions(workspace, fetch, capsys, tmp_path):
    root, settings = workspace
    run(root, settings, "ai-weekly", until=UNTIL, fetch=fetch, model=FakeModel(),
        say=lambda _: None)
    with Library(settings.library, lock=False) as library:
        rows = library.why("https://example.com/gpu-cloud")
        assert rows[0]["stage"] == "sponsored"
        roles = library.db.execute("SELECT role, COUNT(*) FROM inclusions GROUP BY role").fetchall()
        assert dict(map(tuple, roles)) == {"story": 2, "quick_link": 2}
    cfg = tmp_path / "lantern.yaml"
    cfg.write_text(yaml.safe_dump({"vault": str(settings.vault), "library": str(settings.library)}))
    assert main(["--settings", str(cfg), "why", "https://lab.example/news/older-post"]) == 0
    assert "window excluded" in capsys.readouterr().out
    assert main(["--settings", str(cfg), "why", "https://never.test/x"]) == 0
    assert "never seen" in capsys.readouterr().out


def test_second_run_is_locked_out(workspace):
    _, settings = workspace
    with Library(settings.library):
        with pytest.raises(LockHeld):
            Library(settings.library)


def test_cli_exit_codes(workspace, tmp_path, capsys):
    root, settings = workspace
    bad = tmp_path / "bad.yaml"
    bad.write_text("vault: [\n")
    assert main(["--settings", str(bad), "run", "ai-weekly"]) == 1
    missing = tmp_path / "missing.yaml"
    missing.write_text(yaml.safe_dump({"vault": str(tmp_path / "no-vault"),
                                       "library": str(tmp_path / "l.sqlite")}))
    (root / "interests" / "ai.yaml").write_text(
        (root / "interests" / "ai.yaml").read_text().split("sources:")[0]
        + "sources:\n  none: {type: feed, url: 'http://127.0.0.1:9/feed'}\n")
    assert main(["--settings", str(missing), "--root", str(root), "run", "ai-weekly",
                 "--no-model"]) == 2
    with Library(tmp_path / "l.sqlite"):
        assert main(["--settings", str(missing), "--root", str(root), "run", "ai-weekly"]) == 3
    assert main(["--settings", str(missing), "--root", str(root), "check"]) == 0
    assert "config: ok" in capsys.readouterr().out


def test_run_logs_time_tokens_and_cost(workspace, fetch):
    from lantern.config import ModelSettings
    from lantern.model import Usage

    root, settings = workspace
    model = FakeModel()
    model.settings = ModelSettings("https://api.anthropic.com/v1", "claude-sonnet-5-5")
    model.usage = Usage()
    real_chat = model.chat

    def chat(system, user):
        model.usage.add({"prompt_tokens": 1000, "completion_tokens": 200})
        return real_chat(system, user)

    model.chat = chat
    run(root, settings, "ai-weekly", until=UNTIL, fetch=fetch, model=model, say=lambda _: None)
    front, _ = read_note(settings)
    calls = len(model.calls)
    assert front["run_model_calls"] == calls and front["run_tokens_in"] == 1000 * calls
    assert front["run_cost_usd"] == round(calls * (1000 * 2 + 200 * 10) / 1e6, 4)
    assert front["run_seconds"] >= 0
    with Library(settings.library, lock=False) as library:
        row = library.last_runs()[0]
    assert row["cost_usd"] == front["run_cost_usd"] and row["model_calls"] == calls

    from lantern.benchmark import write
    agent = settings.vault / "Lantern" / "AI news" / "Agent" / "2026-W43.md"
    agent.parent.mkdir(parents=True)
    agent.write_text("---\nweek: 2026-W43\nrun_writer: q-lens\nrun_items: 14\n"
                     "run_cost_usd: 2.09\nrun_seconds: 270\n---\n\n# x\n")
    table = write(settings.vault).read_text()
    assert "| 2026-W43 | [[AI news/Lantern/2026-W43\\|ai]] | Lantern | fake-model |" in table
    assert "| Agent | q-lens | 14 | $2.09 | 4.5 min | ? |" in table
    assert "| 2026-W43 | [[AI news/Agent/2026-W43\\|ai]] | Agent |" in table
    assert "**2026-W43 AI note**: Lantern $" in table


def test_thin_items_get_their_article_opening_once(workspace, fetch):
    from lantern.library import Library

    root, settings = workspace
    article = "https://lab.example/news/claude-evals-update"
    description = "How we evaluate every new model before release, and what we found."
    fetch.pages[article] = f'<meta name="description" content="{description}">'.encode()
    lines = []
    quiet = {"fetch": fetch, "model": FakeModel(), "say": lines.append}
    run(root, settings, "ai-weekly", until=UNTIL, **quiet)
    assert "lab: ok 4 items, 1 excerpts read from the article" in lines
    # Only in-window title-only items are read; the September post and full feeds are not.
    assert "https://lab.example/news/older-post" not in fetch.calls
    assert not any(c.startswith("https://example.com/") and c != "https://example.com/feed.xml"
                   for c in fetch.calls)
    with Library(settings.library, lock=False) as library:
        row = library.db.execute("SELECT excerpt FROM items WHERE url = ?", (article,)).fetchone()
        assert row["excerpt"] == description
    fetch.calls.clear()
    run(root, settings, "ai-weekly", until=UNTIL, **quiet)
    assert article not in fetch.calls  # kept in the library, never fetched again
