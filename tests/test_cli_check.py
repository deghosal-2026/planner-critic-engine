"""``plancritic check`` CLI tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from planner_critic.cli.check import run_check


def _make_plan(tmp_path: Path) -> str:
    plan = {
        "id": "p1", "goal_id": "g1", "plan_schema_version": "0.1.0",
        "version": 1, "created_at": "2026-01-01T00:00:00Z",
        "tasks": [
            {"id": "t1", "description": "first", "action": "do", "target": "x",
             "risk_class": "low"},
            {"id": "t2", "description": "second", "action": "do", "target": "y",
             "risk_class": "low"},
        ],
        "dependencies": [{"from_task": "t1", "to_task": "t2", "kind": "hard", "reason": "order"}],
    }
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    return str(path)


def _make_high_risk_plan(tmp_path: Path) -> str:
    plan = {
        "id": "p2", "goal_id": "g2", "plan_schema_version": "0.1.0",
        "version": 1, "created_at": "2026-01-01T00:00:00Z",
        "tasks": [
            {"id": "t1", "description": "risky op", "action": "delete", "target": "db",
             "risk_class": "high"},
        ],
        "dependencies": [],
    }
    path = tmp_path / "high-risk-plan.json"
    path.write_text(json.dumps(plan))
    return str(path)


def test_check_missing_plan(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    rc = run_check([str(tmp_path / "nonexistent.json")])
    assert rc == 4


def test_check_bad_json(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("not json")
    rc = run_check([str(bad)])
    assert rc == 4


def test_check_clean_plan_passes(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    plan_file = _make_plan(tmp_path)
    rc = run_check([plan_file])
    assert rc == 0
    out = capsys.readouterr().out
    assert "PASSED" in out


def test_check_high_risk_plan_fails(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    plan_file = _make_high_risk_plan(tmp_path)
    rc = run_check([plan_file])
    assert rc == 1
    out = capsys.readouterr().out
    assert "FAILED" in out


def test_check_json_output(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    plan_file = _make_plan(tmp_path)
    rc = run_check([plan_file, "--output", "json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "plan" in data
    assert "findings" in data


def test_check_with_domain_not_found(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    plan_file = _make_plan(tmp_path)
    rc = run_check([plan_file, "--domain", "nonexistent"])
    assert rc == 4


def test_check_with_policies_dir_not_found(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    plan_file = _make_plan(tmp_path)
    rc = run_check([plan_file, "--policies-dir", str(tmp_path / "no-policies")])
    assert rc == 4


def test_check_enforcement_strict(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    plan_file = _make_plan(tmp_path)
    rc = run_check([plan_file, "--enforcement", "strict"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STRICT" in out or "PASSED" in out


def test_check_fail_on_warning(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    plan_file = _make_plan(tmp_path)
    rc = run_check([plan_file, "--fail-on-severity", "warning"])
    assert rc == 0


def test_check_yaml_output(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    plan_file = _make_plan(tmp_path)
    rc = run_check([plan_file, "--output", "yaml"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "plan:" in out or "PASSED" in out
