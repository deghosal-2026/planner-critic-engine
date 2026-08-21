"""Top-level CLI dispatch tests — C5 (field test #85).

The 0.1.0 field-test report's §"Multi-Dimension Results" left the CLI surface
as "not run — deferred". C5 requires each ``plancritic`` subcommand to be a
*faithful wrapper*: every subcommand must dispatch through the same
:func:`planner_critic._cli.main` entry point the console script uses, and each
runner must honour the same exit-code contract (0 on success, non-zero on the
failure modes it documents). These tests exercise the top-level wiring with
hermetic inputs (shelling out to nothing; driving the subprocess-equivalent
:func:`main` directly), so no LLM or network is required.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from planner_critic import _cli


def _goal_file(tmp_path: Path, goal_id: str = "g1") -> str:
    """Write a minimal valid Goal to a temp path and return its string path."""
    path = tmp_path / "goal.json"
    path.write_text(
        json.dumps({"id": goal_id, "description": "Ship a service", "risk_tolerance": "balanced"})
    )
    return str(path)


def test_cli_has_all_c5_subcommands() -> None:
    """Every C5 command is registered on the root CLI (C5 faithful wiring)."""
    expected = {
        "init",
        "plan",
        "critique",
        "escalate",
        "plans",
        "providers",
        "demo",
        "replay",
        "migrate",
        "quickstart",
        "field-test",
    }
    assert expected <= set(_cli._SUBCOMMANDS)


def test_cli_plan_dispatch_missing_goal(tmp_path: Path) -> None:
    """``plan`` returns 1 for a missing goal file (fail-closed, C5)."""
    rc = _cli.main(["plan", str(tmp_path / "nonexistent.json")])
    assert rc == 1


def test_cli_plan_dispatch_invalid_goal(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``plan`` returns 1 for malformed goal JSON (fail-closed, C5)."""
    goal = tmp_path / "goal.json"
    goal.write_text("not json")
    rc = _cli.main(["plan", str(goal)])
    assert rc == 1
    assert "invalid goal JSON" in capsys.readouterr().out


def test_cli_critique_dispatch_missing_plan(tmp_path: Path) -> None:
    """``critique`` returns 1 for a missing plan file (fail-closed, C5)."""
    rc = _cli.main(["critique", str(tmp_path / "nonexistent.json")])
    assert rc == 1


def test_cli_critique_dispatch_valid_plan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``critique`` runs deterministic gates and exit 0 on a valid plan (C5)."""
    plan = tmp_path / "plan.json"
    # A single high-risk task with no rollback must trip the rollback gate.
    plan.write_text(
        json.dumps(
            {
                "id": "p1",
                "goal_id": "g1",
                "version": 1,
                "tasks": [
                    {
                        "id": "t1",
                        "description": "apply migration",
                        "action": "migrate",
                        "target": "schema",
                        "risk_class": "high",
                        "preconditions": [],
                    }
                ],
                "dependencies": [],
                "branches": [],
            }
        )
    )
    rc = _cli.main(["critique", "--store", str(tmp_path / "c.db"), str(plan)])
    assert rc == 1  # fail-closed: a plan with a blocker returns exit 1
    out = capsys.readouterr().out
    assert "missing_rollback" in out


def test_cli_plans_list_dispatch(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``plans list`` dispatches and prints a header on an empty store (C5)."""
    rc = _cli.main(["plans", "--store", str(tmp_path / "empty.db"), "list"])
    assert rc == 0
    assert "no plans stored" in capsys.readouterr().out


def test_cli_escalate_list_dispatch(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``escalate list`` dispatches and exits 0 on an empty store (C5)."""
    rc = _cli.main(["escalate", "--store", str(tmp_path / "empty.db"), "list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "no escalations" in out


def test_cli_migrate_dispatch(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``migrate`` dispatches through top-level main and exits 0 (C5/C23)."""
    rc = _cli.main(["migrate", "--path", str(tmp_path / "plans.db")])
    assert rc == 0
    assert "schema at v" in capsys.readouterr().out


def test_cli_init_dispatch(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``init`` dispatches and scaffolds a project (C5/F-85)."""
    rc = _cli.main(["init", "--dir", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "plancritic.toml").is_file()
    out = capsys.readouterr().out
    assert "Initialized PlannerCritic project" in out


def test_cli_replay_dispatch_unknown_plan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``replay`` dispatches and reports 'no history' for an empty store (C22)."""
    db = str(tmp_path / "empty.db")
    rc = _cli.main(["replay", "--store", db, "nope"])
    assert rc == 0
    assert "no history" in capsys.readouterr().out
