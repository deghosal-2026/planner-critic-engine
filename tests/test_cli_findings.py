"""``plancritic findings`` CLI tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from planner_critic.cli.findings import run_findings
from planner_critic.reason_codes import ReasonCode
from planner_critic.schema.plan import PlanVersion, Task
from planner_critic.store.sqlite import SQLiteStore
from planner_critic.types import Finding, Severity


def _seed_finding(store: SQLiteStore, plan_id: str, version: int = 1) -> None:
    plan = PlanVersion(
        id=plan_id, goal_id="g1", version=version,
        tasks=[Task(id="t1", description="task one", action="do", target="x")],
    )
    store.put_plan_version(plan)
    findings = [
        Finding(id="f1", task_id="t1", version=version, severity=Severity.BLOCKER,
                reason_code=cast("ReasonCode", "missing_verification"),
                message="no verification for t1"),
        Finding(id="f2", task_id="t1", version=version, severity=Severity.WARNING,
                reason_code=cast("ReasonCode", "missing_rollback"),
                message="rollback unclear",
                heuristic_family="weak_rollback"),
    ]
    store.put_findings(plan_id, version, findings)


def test_findings_text_output(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    store_path = str(tmp_path / "store.db")
    store = SQLiteStore(store_path)
    _seed_finding(store, "p1")
    store.close()
    rc = run_findings(["p1", "--store", store_path])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Findings for p1" in out
    assert "[BLOCKER]" in out
    assert "missing_verification" in out


def test_findings_json_output(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    store_path = str(tmp_path / "store.db")
    store = SQLiteStore(store_path)
    _seed_finding(store, "p1")
    store.close()
    rc = run_findings(["p1", "--store", store_path, "--output", "json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) == 2
    assert data[0]["reason_code"] == "missing_verification"


def test_findings_not_found(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    store_path = str(tmp_path / "store.db")
    rc = run_findings(["nonexistent", "--store", store_path])
    assert rc == 1
    out = capsys.readouterr().out
    assert "not found" in out.lower()


def test_findings_store_unavailable(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    rc = run_findings(["p1", "--store", str(tmp_path / "no-such-dir" / "store.db")])
    assert rc == 1


def test_findings_specific_version(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    store_path = str(tmp_path / "store.db")
    store = SQLiteStore(store_path)
    plan_v1 = PlanVersion(
        id="p1", goal_id="g1", version=1,
        tasks=[Task(id="t1", description="task one", action="do", target="x")],
    )
    store.put_plan_version(plan_v1)
    store.put_findings("p1", 1, [
        Finding(id="f1", task_id="t1", version=1, severity=Severity.BLOCKER,
                reason_code=cast("ReasonCode", "missing_verification"),
                message="no verification"),
    ])
    plan_v2 = PlanVersion(
        id="p1", goal_id="g1", version=2,
        tasks=[Task(id="t2", description="task two", action="do", target="y")],
    )
    store.put_plan_version(plan_v2)
    store.put_findings("p1", 2, [
        Finding(id="f2", task_id="t2", version=2, severity=Severity.INFO,
                reason_code=cast("ReasonCode", "unverified_precondition"),
                message="minor risk", heuristic_family="risk"),
    ])
    store.close()
    rc = run_findings(["p1", "--version", "2", "--store", store_path])
    assert rc == 0
    out = capsys.readouterr().out
    assert "unverified_precondition" in out or "version 2" in out


def test_findings_include_raw(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    store_path = str(tmp_path / "store.db")
    store = SQLiteStore(store_path)
    _seed_finding(store, "p1")
    store.close()
    rc = run_findings(["p1", "--store", store_path, "--include-raw"])
    assert rc == 0
