"""Coverage tests for cli/plan.py — revise, store, and output paths."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from planner_critic.cli.plan import _store_plan, run_plan
from planner_critic.schema.plan import PlanVersion, Task
from planner_critic.types import Finding


def _make_goal_file(tmp_path: Path, **overrides: object) -> str:
    goal = {
        "id": "g1",
        "description": "Test goal",
        "risk_tolerance": "balanced",
    }
    goal.update(overrides)
    path = tmp_path / "goal.json"
    path.write_text(json.dumps(goal))
    return str(path)


def _make_config(tmp_path: Path) -> str:
    config = tmp_path / "plancritic.toml"
    config.write_text(
        '[roles]\nplanner = "local"\ncritic = "local"\n\n'
        '[providers.local]\ntransport = "openai-compatible"\n'
        'base_url = "https://openrouter.ai/api/v1"\n'
        'model = "openai/gpt-4o-mini"\n'
        'api_key = "${OPENROUTER_API_KEY}"\n'
        'max_tokens = 16384\ntimeout_s = 300.0\n'
    )
    return str(config)


def test_store_plan_success(tmp_path: Path) -> None:
    args = MagicMock()
    args.store = str(tmp_path / "store.db")
    plan = PlanVersion(
        id="p1", goal_id="g1", version=1,
        tasks=[Task(id="t1", description="task", action="do", target="x")],
    )
    findings: list[Finding] = []
    _store_plan(args, plan, findings)
    assert (tmp_path / "store.db").exists()


def test_store_plan_failure(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    args = MagicMock()
    args.store = str(tmp_path / "no-such-dir" / "store.db")
    plan = PlanVersion(
        id="p1", goal_id="g1", version=1,
        tasks=[Task(id="t1", description="task", action="do", target="x")],
    )
    _store_plan(args, plan, [])
    out = capsys.readouterr().out
    assert "warning" in out.lower() or "could not store" in out.lower()


def test_run_plan_goal_validation_failed(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    goal_file = tmp_path / "bad-goal.json"
    goal_file.write_text(json.dumps({"id": "g1"}))  # missing description
    rc = run_plan([str(goal_file), "--config", _make_config(tmp_path)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "validation" in out.lower()


def test_run_plan_posture_override(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    goal_file = _make_goal_file(tmp_path)
    config_file = _make_config(tmp_path)
    fake_result = MagicMock()
    fake_result.is_approved = False
    fake_result.reason_code = "budget_exceeded"
    fake_result.escalation = None
    fake_result.plan = None
    fake_result.findings = []

    with patch("planner_critic.cli.plan.Engine") as mock_engine_cls:
        mock_engine_cls.return_value.plan.return_value = fake_result
        rc = run_plan([str(goal_file), "--config", config_file, "--posture", "strict"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "escalated" in out.lower()


def test_run_plan_approved_output(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    goal_file = _make_goal_file(tmp_path)
    config_file = _make_config(tmp_path)
    plan = PlanVersion(
        id="p1", goal_id="g1", version=1,
        tasks=[Task(id="t1", description="task", action="do", target="x")],
    )
    fake_result = MagicMock()
    fake_result.is_approved = True
    fake_result.reason_code = ""
    fake_result.findings = []
    fake_result.approved_plan = MagicMock()
    fake_result.approved_plan.plan = plan

    with patch("planner_critic.cli.plan.Engine") as mock_engine_cls:
        mock_engine_cls.return_value.plan.return_value = fake_result
        rc = run_plan([str(goal_file), "--config", config_file, "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "approved" in out.lower()
    assert "p1" in out


def test_run_plan_escalated_with_plan(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    goal_file = _make_goal_file(tmp_path)
    config_file = _make_config(tmp_path)
    plan = PlanVersion(
        id="p1", goal_id="g1", version=1,
        tasks=[Task(id="t1", description="task", action="do", target="x")],
    )
    fake_result = MagicMock()
    fake_result.is_approved = False
    fake_result.reason_code = "converged_stalled"
    fake_result.escalation = MagicMock()
    fake_result.escalation.question = "Fix the ordering?"
    fake_result.plan = plan
    fake_result.findings = []

    with patch("planner_critic.cli.plan.Engine") as mock_engine_cls:
        mock_engine_cls.return_value.plan.return_value = fake_result
        rc = run_plan([str(goal_file), "--config", config_file, "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "escalated" in out.lower()
    assert "converged_stalled" in out
    assert "Fix the ordering?" in out


def test_run_plan_planning_exception(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    goal_file = _make_goal_file(tmp_path)
    config_file = _make_config(tmp_path)

    with patch("planner_critic.cli.plan.Engine") as mock_engine_cls:
        mock_engine_cls.return_value.plan.side_effect = Exception("LLM timeout")
        rc = run_plan([str(goal_file), "--config", config_file])
    assert rc == 1
    out = capsys.readouterr().out
    assert "planning failed" in out.lower()
