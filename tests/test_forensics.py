"""Forensics tests (F-51, F-52): missed-critique records + suggested checks.

When a planning failure occurs (the critic missed a flaw that caused a
failure during execution), the forensics module records a
:class:`MissedCritique` with the critique snapshot and auto-suggests a
deterministic check that would have caught the flaw pre-approval.
"""

from __future__ import annotations

from conftest import make_plan
from planner_critic.forensics import MissedCritique, analyze_failure
from planner_critic.reason_codes import (
    LLM_RISK,
    LLM_UNSAFE_SEQUENCING,
    LLM_UNVERIFIED_DEPENDENCIES,
    LLM_WEAK_ROLLBACK,
)
from planner_critic.store.base import InMemoryStore
from planner_critic.types import ExecutionTrace, Finding, Severity


def make_finding(
    finding_id: str = "f:missed",
    task_id: str = "t1",
    reason_code: str = LLM_WEAK_ROLLBACK,
) -> Finding:
    """Build a finding the critic produced (but was only a warning)."""
    return Finding(
        id=finding_id,
        task_id=task_id,
        version=1,
        severity=Severity.WARNING,
        reason_code=reason_code,  # type: ignore[arg-type]
        message="critic flagged this but it was only a warning",
    )


def make_failed_trace(
    plan_id: str = "plan-1",
    task_id: str = "t1",
    linked_finding_id: str = "f:missed",
) -> ExecutionTrace:
    """Build a failed execution trace tagged as a planning failure."""
    return ExecutionTrace(
        id="tr-1",
        plan_id=plan_id,
        task_id=task_id,
        outcome="failed",
        failure_class="planning",
        linked_finding_id=linked_finding_id,
    )


class TestAnalyzeFailure:
    """analyze_failure() maps a missed critique to a suggested deterministic check."""

    def test_weak_rollback_suggests_missing_rollback_gate(self) -> None:
        """A missed weak_rollback finding suggests the missing_rollback gate."""
        finding = make_finding(reason_code=LLM_WEAK_ROLLBACK)
        trace = make_failed_trace()
        result = analyze_failure(trace, finding)
        assert result.suggested_gate == "missing_rollback"
        assert result.reason_code == LLM_WEAK_ROLLBACK

    def test_unverified_dependencies_suggests_preconditions_gate(self) -> None:
        """A missed unverified_dependencies finding suggests the preconditions gate."""
        finding = make_finding(reason_code=LLM_UNVERIFIED_DEPENDENCIES)
        trace = make_failed_trace()
        result = analyze_failure(trace, finding)
        assert result.suggested_gate == "unverified_precondition"

    def test_unsafe_sequencing_suggests_parallelization_gate(self) -> None:
        """A missed unsafe_sequencing finding suggests the parallelization gate."""
        finding = make_finding(reason_code=LLM_UNSAFE_SEQUENCING)
        trace = make_failed_trace()
        result = analyze_failure(trace, finding)
        assert result.suggested_gate == "unsafe_parallelization"

    def test_no_deterministic_gate_available(self) -> None:
        """Some findings (e.g. risk) have no deterministic gate to suggest."""
        finding = make_finding(reason_code=LLM_RISK)
        trace = make_failed_trace()
        result = analyze_failure(trace, finding)
        assert result.suggested_gate is None
        assert result.reason_code == LLM_RISK

    def test_missed_critique_carries_snapshot(self) -> None:
        """The record carries the plan, task, finding, and reason code."""
        finding = make_finding()
        trace = make_failed_trace()
        result = analyze_failure(trace, finding)
        assert result.plan_id == "plan-1"
        assert result.task_id == "t1"
        assert result.linked_finding_id == "f:missed"
        assert result.reason_code == LLM_WEAK_ROLLBACK
        assert result.message == finding.message


class TestStoreAndRetrieve:
    """Missed-critique records persist in the store and are queryable."""

    def test_record_and_retrieve(self) -> None:
        """A missed-critique record round-trips through the store."""
        store = InMemoryStore()
        finding = make_finding()
        trace = make_failed_trace()
        record = analyze_failure(trace, finding)

        store.put_plan_version(make_plan(plan_id="plan-1", version=1))
        record.persist(store)

        retrieved = MissedCritique.load(store, "plan-1")
        assert retrieved is not None
        assert retrieved.task_id == "t1"
        assert retrieved.suggested_gate == "missing_rollback"

    def test_load_returns_none_when_absent(self) -> None:
        """Loading from a plan with no missed-critique returns None."""
        store = InMemoryStore()
        store.put_plan_version(make_plan(plan_id="plan-1", version=1))
        assert MissedCritique.load(store, "plan-1") is None
