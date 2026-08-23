"""``plancritic domains`` CLI tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from planner_critic.cli.domains import run_domains


def test_domains_list(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    rc = run_domains(["list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "domain packs" in out.lower() or "no domain" in out.lower()


def test_domains_show_not_found(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    rc = run_domains(["show", "nonexistent"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "not found" in err.lower()


def test_domains_add_bad_path(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    rc = run_domains(["add", str(tmp_path / "nonexistent.yaml")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "failed to load" in err.lower()


def test_domains_add_valid(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    manifest = tmp_path / "test-pack.yaml"
    manifest.write_text(yaml.dump({
        "name": "test-pack",
        "version": "1.0",
        "gates": [],
    }))
    rc = run_domains(["add", str(manifest)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Registered" in out or "test-pack" in out


def test_domains_test_missing_pack(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    rc = run_domains(["test", "nonexistent", str(tmp_path / "plan.json")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "not found" in err.lower() or "failed to load" in err.lower()


def test_domains_test_bad_plan(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    bad_plan = tmp_path / "plan.json"
    bad_plan.write_text("not json")
    rc = run_domains(["test", "nonexistent", str(bad_plan)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "not found" in err.lower() or "failed" in err.lower() or "error" in err.lower()


def test_domains_test_with_manifest(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    manifest = tmp_path / "simple-pack.yaml"
    manifest.write_text(yaml.dump({
        "name": "simple",
        "version": "1.0",
        "gates": [],
    }))
    plan = {
        "id": "p1", "goal_id": "g1", "plan_schema_version": "0.1.0",
        "version": 1, "created_at": "2026-01-01T00:00:00Z",
        "tasks": [{"id": "t1", "description": "task", "action": "do", "target": "x"}],
        "dependencies": [],
    }
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan))
    rc = run_domains(["test", str(manifest), str(plan_file)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "PASSED" in out
