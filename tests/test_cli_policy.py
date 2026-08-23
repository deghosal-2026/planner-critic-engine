"""``plancritic policy`` CLI tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from planner_critic.cli.policy import run_policy


def _make_plan(tmp_path: Path) -> str:
    plan = {
        "id": "p1",
        "goal_id": "g1",
        "plan_schema_version": "0.1.0",
        "version": 1,
        "created_at": "2026-01-01T00:00:00Z",
        "tasks": [
            {"id": "t1", "description": "task", "action": "do", "target": "x", "risk_class": "low"}
        ],
        "dependencies": [],
    }
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    return str(path)


def test_policy_list(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = run_policy(["list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Built-in" in out or "policy" in out.lower()


def test_policy_add_not_found(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = run_policy(["add", str(tmp_path / "nonexistent.rego")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "not found" in err.lower()


def test_policy_add_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rego = tmp_path / "test.rego"
    rego.write_text('package test\nviolation[msg] { msg := "test" }')
    rc = run_policy(["add", str(rego)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Registered" in out


def test_policy_add_dir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pol_dir = tmp_path / "policies"
    pol_dir.mkdir()
    rego = pol_dir / "rule1.rego"
    rego.write_text('package test\nviolation[msg] { msg := "test" }')
    rc = run_policy(["add", str(pol_dir)])
    assert rc == 0


def test_policy_add_yaml_dir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pol_dir = tmp_path / "policies"
    pol_dir.mkdir()
    yaml_file = pol_dir / "rule.yaml"
    yaml_file.write_text(
        yaml.dump(
            {
                "kind": "Policy",
                "name": "test-policy",
                "cel": "true",
                "severity": "warning",
                "message": "test",
            }
        )
    )
    rc = run_policy(["add", str(pol_dir)])
    assert rc == 0


def test_policy_test_builtin_not_found(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    plan_file = _make_plan(tmp_path)
    rc = run_policy(["test", "nonexistent", plan_file])
    assert rc == 1
    err = capsys.readouterr().err
    assert "not found" in err.lower()


def test_policy_test_bad_plan(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("not json")
    rc = run_policy(["test", str(bad), str(bad)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "failed to load plan" in err.lower() or "failed to load policy" in err.lower()


def test_policy_test_file_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rego = tmp_path / "custom.rego"
    rego.write_text('package test\nviolation[msg] { msg := "test" }')
    plan_file = _make_plan(tmp_path)
    rc = run_policy(["test", str(rego), plan_file])
    assert rc == 0 or rc == 1
