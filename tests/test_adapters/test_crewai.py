"""Tests for the CrewAI adapter (crewai.py)."""

import pytest

from conftest import make_plan
from planner_critic.adapters._audit import AuditTrail
from planner_critic.adapters.crewai import PlanAwareTaskInterceptor, TaskNotInPlanError
from planner_critic.approval import ApprovalGate, resolve_threshold
from planner_critic.schema.goal import RiskTolerance
from planner_critic.schema.plan import Task


def _make_approved_plan(*, task_descriptions=None):
    if task_descriptions is None:
        task_descriptions = ["Deploy service", "Run migration"]
    tasks = [
        Task(id=f"t{i}", description=desc, action="do", target=desc)
        for i, desc in enumerate(task_descriptions, 1)
    ]
    gate = ApprovalGate(RiskTolerance.BALANCED)
    satisfied, outcome = resolve_threshold([], RiskTolerance.BALANCED)
    return gate.approve(make_plan(tasks=tasks), outcome)


class TestPlanAwareTaskInterceptor:
    def test_verify_matching_task_succeeds(self):
        approved = _make_approved_plan()
        interceptor = PlanAwareTaskInterceptor(approved)

        assert interceptor.verify_task("Deploy service") is True

    def test_verify_nonmatching_task_raises(self):
        approved = _make_approved_plan()
        interceptor = PlanAwareTaskInterceptor(approved)

        with pytest.raises(TaskNotInPlanError):
            interceptor.verify_task("Nonexistent task")

    def test_verify_substring_match_succeeds(self):
        approved = _make_approved_plan()
        interceptor = PlanAwareTaskInterceptor(approved)

        assert interceptor.verify_task("Deploy") is True

    def test_before_execution_matching(self):
        approved = _make_approved_plan()
        interceptor = PlanAwareTaskInterceptor(approved)

        interceptor.before_execution("Run migration")

    def test_before_execution_nonmatching_raises(self):
        approved = _make_approved_plan()
        interceptor = PlanAwareTaskInterceptor(approved)

        with pytest.raises(TaskNotInPlanError):
            interceptor.before_execution("Unknown operation")

    def test_with_audit_trail(self):
        approved = _make_approved_plan()
        audit = AuditTrail()
        interceptor = PlanAwareTaskInterceptor(approved, audit=audit)

        interceptor.verify_task("Deploy service")

        last = audit.last_event()
        assert last is not None
        assert last.adapter == "crewai"
        assert last.event == "re_gate_check"
        assert last.details.get("found") is True

    def test_audit_records_not_found(self):
        approved = _make_approved_plan()
        audit = AuditTrail()
        interceptor = PlanAwareTaskInterceptor(approved, audit=audit)

        with pytest.raises(TaskNotInPlanError):
            interceptor.verify_task("Bogus")

        last = audit.last_event()
        assert last is not None
        assert last.details.get("found") is False
