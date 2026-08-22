from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from planner_critic.gates.base import BaseGate
from planner_critic.schema.plan import PlanVersion, RiskClass, Task
from planner_critic.types import Finding, Severity


class _TestGate(BaseGate):
    name: str = "test_gate"
    author: str | None = "alice"
    rationale: str | None = "Prevents unsafe parallel operations"
    added_at: datetime | None = datetime(2026, 1, 1, tzinfo=UTC)
    stale_at: datetime | None = None
    amend_conditions: str | None = "Requires team lead approval"

    def run(self, plan: PlanVersion) -> list[Finding]:
        return []


class _StaleGate(BaseGate):
    name: str = "stale_gate"
    author: str | None = "bob"
    rationale: str | None = "Old rule from migration"
    added_at: datetime | None = datetime(2024, 1, 1, tzinfo=UTC)
    stale_at: datetime | None = datetime(2025, 1, 1, tzinfo=UTC)

    def run(self, plan: PlanVersion) -> list[Finding]:
        return []


class _EmptyGate(BaseGate):
    name: str = "empty"

    def run(self, plan: PlanVersion) -> list[Finding]:
        return []


class TestGateMetadata:
    def test_metadata_includes_rationale(self) -> None:
        gate = _TestGate()
        meta = gate.metadata
        assert meta["name"] == "test_gate"
        assert meta["author"] == "alice"
        assert meta["rationale"] == "Prevents unsafe parallel operations"
        assert meta["amend_conditions"] == "Requires team lead approval"
        assert meta["is_stale"] is False

    def test_stale_gate_detected(self) -> None:
        gate = _StaleGate()
        meta = gate.metadata
        assert meta["author"] == "bob"
        assert meta["is_stale"] is True

    def test_gate_without_rationale(self) -> None:
        gate = _EmptyGate()
        meta = gate.metadata
        assert meta["author"] is None
        assert meta["rationale"] is None
        assert meta["is_stale"] is False

    def test_repr_includes_author(self) -> None:
        gate = _TestGate()
        assert "alice" in repr(gate)

    def test_repr_without_author(self) -> None:
        gate = _EmptyGate()
        assert "EmptyGate" in repr(gate)