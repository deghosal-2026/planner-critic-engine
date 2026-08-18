"""``plancritic plans`` CLI tests (F-61)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from planner_critic.cli.plans import build_plans_parser, run_plans
from planner_critic.schema.plan import PlanVersion
from planner_critic.store.sqlite import SQLiteStore


def _seed_store(path: str) -> None:
    store = SQLiteStore(path)
    store.put_plan_version(
        PlanVersion(
            id="plan-a",
            goal_id="goal-1",
            version=1,
            tasks=[{"id": "t1", "description": "task t1", "action": "do", "target": "t1", "preconditions": []}],
            dependencies=[],
            branches=[],
        )
    )
    store.put_plan_version(
        PlanVersion(
            id="plan-a",
            goal_id="goal-1",
            version=2,
            tasks=[
                {"id": "t1", "description": "task t1", "action": "do", "target": "t1", "preconditions": []},
                {"id": "t2", "description": "task t2", "action": "do", "target": "t2", "preconditions": []},
            ],
            dependencies=[],
            branches=[],
        )
    )
    store.close()


def test_build_plans_parser() -> None:
    """The parser can be constructed without error."""
    parser = build_plans_parser()
    assert parser.prog == "plancritic plans"


def test_plans_list_empty(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """``plans list`` on an empty store prints a message."""
    store_path = tmp_path / "store.db"
    SQLiteStore(str(store_path)).close()
    rc = run_plans(["--store", str(store_path), "list"])
    assert rc == 0
    assert "no plans stored" in capsys.readouterr().out


def test_plans_list_shows_plans(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """``plans list`` shows stored plans."""
    store_path = tmp_path / "store.db"
    _seed_store(str(store_path))
    rc = run_plans(["--store", str(store_path), "list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "plan-a" in out
    assert "v2" in out


def test_plans_show_latest(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """``plans show plan-a`` shows the latest version."""
    store_path = tmp_path / "store.db"
    _seed_store(str(store_path))
    rc = run_plans(["--store", str(store_path), "show", "plan-a"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["version"] == 2


def test_plans_show_version(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """``plans show plan-a --version 1`` shows version 1."""
    store_path = tmp_path / "store.db"
    _seed_store(str(store_path))
    rc = run_plans(["--store", str(store_path), "show", "plan-a", "--version", "1"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["version"] == 1


def test_plans_show_missing(tmp_path: Path) -> None:
    """``plans show nonexistent`` returns exit code 1."""
    store_path = tmp_path / "store.db"
    SQLiteStore(str(store_path)).close()
    rc = run_plans(["--store", str(store_path), "show", "nonexistent"])
    assert rc == 1


def test_plans_diff(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """``plans diff plan-a 1 2`` shows structural changes."""
    store_path = tmp_path / "store.db"
    _seed_store(str(store_path))
    rc = run_plans(["--store", str(store_path), "diff", "plan-a", "1", "2"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "v1 → v2" in out
    assert "added tasks" in out
    assert "t2" in out


def test_plans_diff_missing(tmp_path: Path) -> None:
    """``plans diff`` with missing revisions returns exit code 1."""
    store_path = tmp_path / "store.db"
    SQLiteStore(str(store_path)).close()
    rc = run_plans(["--store", str(store_path), "diff", "plan-a", "1", "99"])
    assert rc == 1


def test_plans_diff_graph(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """``plans diff --graph`` includes a Mermaid DAG."""
    store_path = tmp_path / "store.db"
    _seed_store(str(store_path))
    rc = run_plans(["--store", str(store_path), "diff", "plan-a", "1", "2", "--graph"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "graph TD" in out


def test_plans_diff_identical(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """``plans diff`` with identical versions shows no changes."""
    store_path = tmp_path / "store.db"
    _seed_store(str(store_path))
    rc = run_plans(["--store", str(store_path), "diff", "plan-a", "2", "2"])
    assert rc == 0
    assert "no structural changes" in capsys.readouterr().out


def test_plans_no_action_prints_usage(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """``plans`` without a subcommand prints usage and returns 1."""
    store_path = tmp_path / "store.db"
    rc = run_plans(["--store", str(store_path)])
    assert rc == 1
    assert "usage" in capsys.readouterr().out