"""``plancritic replay`` CLI tests (F-76)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from planner_critic.cli.replay import build_replay_parser, run_replay
from planner_critic.schema.plan import PlanVersion
from planner_critic.store.sqlite import SQLiteStore


def _seed_replay(store_path: str, plan_id: str = "plan-a") -> None:
    store = SQLiteStore(store_path)
    store.put_plan_version(
        PlanVersion(
            id=plan_id,
            goal_id="goal-1",
            version=1,
            tasks=[{"id": "t1", "description": "task t1", "action": "do", "target": "t1", "preconditions": []}],
            dependencies=[],
            branches=[],
        )
    )
    store.put_plan_version(
        PlanVersion(
            id=plan_id,
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
    store.put_findings(plan_id, 1, [])
    store.put_findings(plan_id, 2, [])
    store.close()


def test_build_replay_parser() -> None:
    """The parser can be constructed without error."""
    parser = build_replay_parser()
    assert parser.prog == "plancritic replay"


def test_replay_success_text(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Replay prints version history in text format."""
    store_path = str(tmp_path / "store.db")
    _seed_replay(store_path)
    rc = run_replay(["--store", store_path, "plan-a"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "v1:" in out
    assert "v2:" in out


def test_replay_success_json(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Replay with --format json outputs JSON."""
    store_path = str(tmp_path / "store.db")
    _seed_replay(store_path)
    rc = run_replay(["--store", store_path, "plan-a", "--format", "json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["plan_id"] == "plan-a"
    assert len(data["steps"]) == 2


def test_replay_with_step(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Replay with --step limits the number of revisions."""
    store_path = str(tmp_path / "store.db")
    _seed_replay(store_path)
    rc = run_replay(["--store", store_path, "plan-a", "--step", "1"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "v1:" in out
    assert "v2:" not in out


def test_replay_unknown_plan(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Replaying an unknown plan prints 'no history'."""
    store_path = str(tmp_path / "store.db")
    SQLiteStore(store_path).close()
    rc = run_replay(["--store", store_path, "nonexistent"])
    assert rc == 0
    assert "no history" in capsys.readouterr().out


def test_replay_store_failure(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Replay with an unreachable store returns exit code 1."""
    rc = run_replay(["--store", "/nonexistent_dir/store.db", "plan-a"])
    assert rc == 1
    assert "replay failed" in capsys.readouterr().out