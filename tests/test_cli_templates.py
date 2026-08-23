"""``plancritic templates`` CLI tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from planner_critic.cli.templates import run_templates


def test_templates_list(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = run_templates(["list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "templates" in out.lower() or "Precondition" in out


def test_templates_add(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = run_templates(["add", "test-tmpl", "--pattern", "db_healthy", "--description", "Check DB"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Registered" in out or "test-tmpl" in out


def test_templates_add_full(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = run_templates(
        [
            "add",
            "full-tmpl",
            "--pattern",
            "deploy_done",
            "--task-id",
            "check-deploy",
            "--description",
            "Verify deployment",
            "--action",
            "verify",
            "--target",
            "deploy_status",
            "--risk-class",
            "high",
        ]
    )
    assert rc == 0


def test_templates_test_missing_template(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(
        json.dumps(
            {
                "id": "p1",
                "goal_id": "g1",
                "plan_schema_version": "0.1.0",
                "version": 1,
                "created_at": "2026-01-01T00:00:00Z",
                "tasks": [{"id": "t1", "description": "task", "action": "do", "target": "x"}],
                "dependencies": [],
            }
        )
    )
    rc = run_templates(["test", "nonexistent", str(plan_file)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "not found" in err.lower()


def test_templates_test_bad_plan(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad_plan = tmp_path / "plan.json"
    bad_plan.write_text("not json")
    rc = run_templates(["test", "nonexistent", str(bad_plan)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "failed to load" in err.lower() or "not found" in err.lower()
