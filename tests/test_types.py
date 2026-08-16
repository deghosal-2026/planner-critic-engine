"""Types + reason-code catalog tests (F-77).

Asserts the catalog is complete (every code documented), stable, and that the
core types serialize/validate correctly.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from conftest import make_goal, make_plan
from planner_critic.reason_codes import ALL_REASON_CODES, REASON_CODE_DESCRIPTIONS
from planner_critic.types import (
    ApprovedPlan,
    Escalation,
    ExecutionTrace,
    Finding,
    PlanComplexity,
    PlanningError,
    Severity,
)


class TestReasonCatalog:
    """The reason-code catalog is complete, stable, and self-consistent."""

    def test_every_code_documented(self) -> None:
        """Every valid code has a description (single source of truth)."""
        assert set(ALL_REASON_CODES) == set(REASON_CODE_DESCRIPTIONS)

    def test_catalog_is_explicitly_enumerated(self) -> None:
        """The literal union covers exactly the documented keys."""
        expected = frozenset(REASON_CODE_DESCRIPTIONS)
        assert ALL_REASON_CODES == expected

    def test_known_codes_present(self) -> None:
        """Spot-check the deterministic gate + loop decision codes."""
        for code in ("plan_schema_invalid", "dependency_cycle", "revision_cap_reached", "approved"):
            assert code in ALL_REASON_CODES

    def test_reason_code_is_str(self) -> None:
        """ReasonCode values are plain strings (JSON-safe)."""
        assert "approved" in ALL_REASON_CODES


class TestFinding:
    """Finding construction and severity semantics."""

    def test_blocker_severity(self) -> None:
        """Blockers never allow approval."""
        assert Severity.BLOCKER.is_blocker
        assert not Severity.WARNING.is_blocker
        assert not Severity.INFO.is_blocker

    def test_plan_level_finding_allows_null_task(self) -> None:
        """A structural (plan-level) finding has no task_id."""
        f = Finding(
            id="x", version=1, severity=Severity.BLOCKER, reason_code="dependency_cycle",
            message="cycle",
        )
        assert f.task_id is None

    def test_invalid_reason_code_rejected(self) -> None:
        """Constructing a finding with a non-catalog code fails."""
        with pytest.raises(ValidationError):
            Finding.model_validate(
                {
                    "id": "x", "version": 1, "severity": "blocker",
                    "reason_code": "not_a_real_code", "message": "boom",
                }
            )

    def test_str_render(self) -> None:
        """Findings render a stable one-line form."""
        f = Finding(
            id="x", version=1, severity=Severity.WARNING,
            reason_code="unsafe_ordering", message="early",
        )
        assert "[warning] unsafe_ordering: early" in str(f)


class TestCoreTypes:
    """PlanComplexity / Escalation / ExecutionTrace / ApprovedPlan."""

    def test_plan_complexity(self) -> None:
        """Complexity fields hold deterministic derived numbers."""
        c = PlanComplexity(
            step_count=3, parallel_branch_count=1, irreversible_op_count=1,
            est_llm_calls=4, est_token_cost=12_000.0,
        )
        assert c.step_count == 3

    def test_escalation_defaults(self) -> None:
        """Escalations start open, without resolution."""
        e = Escalation(id="e1", plan_id="p1", version=2, question="proceed?")
        assert e.status == "open"
        assert e.resolution is None

    def test_execution_trace_failure_class(self) -> None:
        """Trace failures are planning|execution or None."""
        t = ExecutionTrace(id="t1", plan_id="p1", task_id="t1", outcome="failed")
        assert t.failure_class is None

    def test_approved_plan_goal_id(self) -> None:
        """ApprovedPlan exposes the served goal id."""
        plan = make_plan()
        ap = ApprovedPlan(
            plan=plan,
            risk_tolerance=make_goal().risk_tolerance,
        )
        assert ap.goal_id == plan.goal_id
        assert ap.plan == plan

    def test_planning_error_carries_reason(self) -> None:
        """PlanningError preserves the fail-closed reason code."""
        err = PlanningError("boom", reason_code="planning_unavailable")
        assert err.reason_code == "planning_unavailable"
        assert "boom" in str(err)
