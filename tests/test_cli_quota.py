"""``plancritic quota`` CLI tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from planner_critic.cli.quota import run_quota


def test_quota_list(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    rc = run_quota(["list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Quotas" in out


def test_quota_list_with_domain(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    rc = run_quota(["list", "--domain", "secops"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "secops" in out


def test_quota_set(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    rc = run_quota(["set", "max_resource_changes", "10"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "max_resource_changes" in out
    assert "10" in out


def test_quota_set_with_domain(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    rc = run_quota(["set", "max_destructive_actions", "3", "--domain", "secops"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "max_destructive_actions" in out


def test_quota_set_database(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    rc = run_quota(["set", "max_database_alterations", "5"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "max_database_alterations" in out


def test_quota_check_pass(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    quotas_file = tmp_path / "quotas.yaml"
    quotas_file.write_text(yaml.dump({"quotas": {"max_resource_changes": 100}}))
    plan_file = tmp_path / "plan.json"
    plan = {
        "id": "p1", "goal_id": "g1", "plan_schema_version": "0.1.0",
        "version": 1, "created_at": "2026-01-01T00:00:00Z",
        "tasks": [{"id": "t1", "description": "task", "action": "do", "target": "x"}],
        "dependencies": [],
    }
    plan_file.write_text(json.dumps(plan))
    rc = run_quota(["check", str(plan_file), "--quotas", str(quotas_file)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "passes" in out


def test_quota_check_bad_quotas_file(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    plan_file = tmp_path / "plan.json"
    plan_file.write_text("{}")
    rc = run_quota(["check", str(plan_file), "--quotas", str(tmp_path / "nonexistent.yaml")])
    assert rc == 1
    out = capsys.readouterr().out
    assert "failed to load quotas" in out


def test_quota_check_bad_plan_file(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    quotas_file = tmp_path / "quotas.yaml"
    quotas_file.write_text(yaml.dump({"quotas": {}}))
    rc = run_quota(["check", str(tmp_path / "nonexistent.json"), "--quotas", str(quotas_file)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "failed to load plan" in out


def test_quota_check_violation(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    quotas_file = tmp_path / "quotas.yaml"
    quotas_file.write_text(yaml.dump({"quotas": {"max_resource_changes": 0}}))
    plan_file = tmp_path / "plan.json"
    plan = {
        "id": "p1", "goal_id": "g1", "plan_schema_version": "0.1.0",
        "version": 1, "created_at": "2026-01-01T00:00:00Z",
        "tasks": [
            {"id": "t1", "description": "create resource", "action": "create", "target": "vm"},
            {"id": "t2", "description": "delete resource", "action": "delete", "target": "vm"},
        ],
        "dependencies": [],
    }
    plan_file.write_text(json.dumps(plan))
    rc = run_quota(["check", str(plan_file), "--quotas", str(quotas_file)])
    assert rc == 1
