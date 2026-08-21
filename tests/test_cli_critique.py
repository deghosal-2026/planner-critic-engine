"""``plancritic critique`` CLI tests (F-61)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from planner_critic.cli.critique import build_critique_parser, run_critique


def _make_plan_file(tmp_path: Path, **overrides: object) -> str:
    data: dict[str, object] = {
        "id": "plan-1",
        "goal_id": "goal-1",
        "version": 1,
        "tasks": [
            {
                "id": "t1",
                "description": "task t1",
                "action": "do",
                "target": "t1",
                "preconditions": [],
            }
        ],
        "dependencies": [],
        "branches": [],
    }
    data.update(overrides)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(data))
    return str(path)


def test_build_critique_parser() -> None:
    """The parser can be constructed without error."""
    parser = build_critique_parser()
    assert parser.prog == "plancritic critique"


def test_run_critique_missing_plan_file(tmp_path: Path) -> None:
    """A missing plan file returns exit code 1."""
    rc = run_critique([str(tmp_path / "nonexistent.json")])
    assert rc == 1


def test_run_critique_invalid_json(tmp_path: Path) -> None:
    """Invalid plan JSON returns exit code 1."""
    plan_file = tmp_path / "plan.json"
    plan_file.write_text("not json")
    rc = run_critique([str(plan_file)])
    assert rc == 1


def test_run_critique_clean_plan_passes(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """A valid plan with no issues passes deterministic gates."""
    plan_file = _make_plan_file(tmp_path)
    rc = run_critique([str(plan_file), "--store", str(tmp_path / "store.db")])
    assert rc == 0
    out = capsys.readouterr().out
    assert "no findings" in out


def test_run_critique_flags_blockers(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """A plan with bad preconditions is flagged."""
    plan_file = _make_plan_file(
        tmp_path,
        tasks=[
            {
                "id": "t1",
                "description": "task t1",
                "action": "do",
                "target": "t1",
                "preconditions": [
                    {"description": "pre-req", "fact": "some_fact", "established_by": "nonexistent"}
                ],
            }
        ],
    )
    rc = run_critique([str(plan_file), "--store", str(tmp_path / "store.db")])
    assert rc == 1
    out = capsys.readouterr().out
    assert "blocker" in out


def test_run_critique_stores_findings(tmp_path: Path) -> None:
    """Findings are stored in the store."""
    store_path = tmp_path / "store.db"
    plan_file = _make_plan_file(
        tmp_path,
        tasks=[
            {
                "id": "t1",
                "description": "task t1",
                "action": "do",
                "target": "t1",
                "preconditions": [
                    {"description": "pre-req", "fact": "some_fact", "established_by": "nonexistent"}
                ],
            }
        ],
    )
    rc = run_critique([str(plan_file), "--store", str(store_path)])
    assert rc == 1
    assert store_path.exists()


def test_run_critique_plan_validation_failure(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Invalid plan JSON returns exit code 1 (line 38-40)."""
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps({"id": "bad", "version": "notanint"}))
    rc = run_critique([str(plan_file), "--store", str(tmp_path / "store.db")])
    assert rc == 1
    assert "plan validation failed" in capsys.readouterr().out


def test_run_critique_store_failure(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Store failure prints a warning (line 55-56)."""
    plan_file = _make_plan_file(tmp_path)
    rc = run_critique([str(plan_file), "--store", "/nonexistent_dir/bad.db"])
    assert rc == 0
    assert "warning:" in capsys.readouterr().out
