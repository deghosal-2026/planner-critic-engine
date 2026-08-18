"""Execution link + tagging tests (F-50): bind execution to an approved plan.

Every executed task is recorded as an :class:`ExecutionTrace` linked to the
:class:`ApprovedPlan` that authorized it. Failures are classified as
``planning`` (the critic missed a flaw) or ``execution`` (the plan was sound
but the step failed). The classification feeds the missed-critique forensics
in T7.
"""

from __future__ import annotations

import pytest

from conftest import make_plan
from planner_critic.approval import ApprovalGate, resolve_threshold
from planner_critic.execution import ExecutionRecorder
from planner_critic.schema.goal import RiskTolerance
from planner_critic.store.base import InMemoryStore
from planner_critic.types import ApprovedPlan, Finding, Severity


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def approved(store: InMemoryStore) -> ApprovedPlan:
    """An approved plan stored in the store."""
    plan = make_plan(plan_id="plan-1", version=1)
    store.put_plan_version(plan)
    _, outcome = resolve_threshold([], RiskTolerance.BALANCED)
    gate = ApprovalGate(RiskTolerance.BALANCED)
    return gate.approve(plan, outcome)


@pytest.fixture
def recorder(store: InMemoryStore) -> ExecutionRecorder:
    return ExecutionRecorder(store)


class TestRecord:
    """record() persists a trace and links it to the approved plan."""

    def test_record_success(
        self, store: InMemoryStore, recorder: ExecutionRecorder, approved: ApprovedPlan
    ) -> None:
        """A successful task produces a trace with no failure class."""
        trace = recorder.record(approved, task_id="t1", outcome="ok")
        assert trace.plan_id == "plan-1"
        assert trace.task_id == "t1"
        assert trace.outcome == "ok"
        assert trace.failure_class is None

        stored = store.get_execution_traces("plan-1")
        assert len(stored) == 1
        assert stored[0].id == trace.id

    def test_record_links_to_approved_plan(
        self, store: InMemoryStore, recorder: ExecutionRecorder, approved: ApprovedPlan
    ) -> None:
        """The trace is linked to the approved plan revision."""
        trace = recorder.record(approved, task_id="t1", outcome="ok")
        assert ("plan-1", 1, trace.id) in store._links

    def test_record_failure_execution(
        self, store: InMemoryStore, recorder: ExecutionRecorder, approved: ApprovedPlan
    ) -> None:
        """A failure with no linked finding is tagged execution."""
        trace = recorder.record(approved, task_id="t1", outcome="failed")
        assert trace.failure_class == "execution"

    def test_record_failure_planning(
        self, store: InMemoryStore, recorder: ExecutionRecorder, approved: ApprovedPlan
    ) -> None:
        """A failure with a linked finding is tagged planning (missed critique)."""
        finding = Finding(
            id="f:missed",
            task_id="t1",
            version=1,
            severity=Severity.WARNING,
            reason_code="llm_risk",
            message="risk overlooked",
        )
        trace = recorder.record(
            approved, task_id="t1", outcome="failed", linked_finding=finding
        )
        assert trace.failure_class == "planning"
        assert trace.linked_finding_id == "f:missed"

    def test_record_generates_unique_ids(
        self, recorder: ExecutionRecorder, approved: ApprovedPlan
    ) -> None:
        """Multiple traces get unique ids."""
        t1 = recorder.record(approved, task_id="t1", outcome="ok")
        t2 = recorder.record(approved, task_id="t2", outcome="ok")
        assert t1.id != t2.id


class TestGetTraces:
    """get_traces() returns the full execution history for a plan."""

    def test_get_traces_in_order(
        self, store: InMemoryStore, recorder: ExecutionRecorder, approved: ApprovedPlan
    ) -> None:
        """Traces come back in insertion order."""
        recorder.record(approved, task_id="t1", outcome="ok")
        recorder.record(approved, task_id="t2", outcome="failed")
        traces = recorder.get_traces("plan-1")
        assert [t.task_id for t in traces] == ["t1", "t2"]

    def test_get_traces_empty(self, recorder: ExecutionRecorder) -> None:
        """An unknown plan has no traces."""
        assert recorder.get_traces("nope") == []


class TestClassifyFailure:
    """classify_failure() determines planning vs execution blame."""

    def test_with_linked_finding_is_planning(self, recorder: ExecutionRecorder) -> None:
        """A linked finding means the critic missed something."""
        finding = Finding(
            id="f1", task_id="t1", version=1,
            severity=Severity.WARNING, reason_code="llm_risk", message="x",
        )
        assert recorder.classify_failure(linked_finding=finding) == "planning"

    def test_without_finding_is_execution(self, recorder: ExecutionRecorder) -> None:
        """No linked finding means the plan was sound; execution failed."""
        assert recorder.classify_failure(linked_finding=None) == "execution"
