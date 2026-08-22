"""Tests for label-migration escape harness (M5, #171)."""

from __future__ import annotations

from pathlib import Path

import pytest

from planner_critic.eval.label_migration import (
    BoundaryCase,
    IrreversibleInvariantGate,
    LabelMigrationRecord,
    build_confusion_matrix,
)
from planner_critic.schema.plan import PlanVersion, Task
from planner_critic.types import Severity


class TestLabelMigrationRecord:
    def test_basic_record(self) -> None:
        record = LabelMigrationRecord(
            finding_id="f1",
            original_family="missing_steps",
            assigned_family="risk",
            original_severity=Severity.BLOCKER,
            assigned_severity=Severity.WARNING,
            finding_text="Missing output encoding",
        )
        assert record.original_family == "missing_steps"
        assert record.assigned_family == "risk"


class TestBuildConfusionMatrix:
    def test_empty_input(self) -> None:
        matrix = build_confusion_matrix([])
        assert matrix == {}

    def test_single_record(self) -> None:
        records = [
            LabelMigrationRecord("f1", "A", "B", Severity.BLOCKER, Severity.BLOCKER, "text"),
        ]
        matrix = build_confusion_matrix(records)
        assert matrix["A"]["B"] == 1

    def test_multiple_assignments(self) -> None:
        records = [
            LabelMigrationRecord("f1", "A", "B", Severity.BLOCKER, Severity.WARNING, "t1"),
            LabelMigrationRecord("f2", "A", "C", Severity.BLOCKER, Severity.INFO, "t2"),
            LabelMigrationRecord("f3", "B", "A", Severity.WARNING, Severity.BLOCKER, "t3"),
        ]
        matrix = build_confusion_matrix(records)
        assert matrix["A"]["B"] == 1
        assert matrix["A"]["C"] == 1
        assert matrix["B"]["A"] == 1


class TestIrreversibleInvariantGate:
    def test_critical_high_without_rollback_blocked(self) -> None:
        task = Task.model_validate({
            "id": "t1", "description": "drop table", "action": "drop",
            "target": "production", "risk_class": "critical",
            "blast_radius": "high",
        })
        plan = PlanVersion(id="p1", goal_id="g1", version=1, tasks=[task])
        gate = IrreversibleInvariantGate()
        findings = gate.run(plan)
        assert len(findings) == 1
        assert findings[0].severity is Severity.BLOCKER

    def test_critical_high_with_rollback_and_precondition_passes(self) -> None:
        task = Task.model_validate({
            "id": "t1", "description": "drop table", "action": "drop",
            "target": "production", "risk_class": "critical",
            "blast_radius": "high",
            "rollback": {"trigger": "verification_fails", "action": "revert",
                         "safety_guard": "backup_confirmed"},
            "preconditions": [{
                "description": "backup verified",
                "fact": "backup_exists",
                "established_by": "env:backup_status",
            }],
        })
        plan = PlanVersion(id="p1", goal_id="g1", version=1, tasks=[task])
        gate = IrreversibleInvariantGate()
        findings = gate.run(plan)
        assert len(findings) == 0

    def test_critical_high_with_verification_only_passes(self) -> None:
        task = Task.model_validate({
            "id": "t1", "description": "modify schema", "action": "alter",
            "target": "db", "risk_class": "critical",
            "blast_radius": "high",
            "verification": {"what": "schema applied", "how": "check", "expected": "match"},
            "rollback": {"trigger": "verification_fails", "action": "revert",
                         "safety_guard": "backup_confirmed"},
        })
        plan = PlanVersion(id="p1", goal_id="g1", version=1, tasks=[task])
        gate = IrreversibleInvariantGate()
        findings = gate.run(plan)
        assert len(findings) == 0

    def test_low_risk_not_affected(self) -> None:
        task = Task.model_validate({
            "id": "t1", "description": "add comment", "action": "add",
            "target": "code", "risk_class": "low",
            "blast_radius": "low",
        })
        plan = PlanVersion(id="p1", goal_id="g1", version=1, tasks=[task])
        gate = IrreversibleInvariantGate()
        findings = gate.run(plan)
        assert len(findings) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])