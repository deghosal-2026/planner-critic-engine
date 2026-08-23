"""Tests for the LangGraph adapter (langgraph.py)."""

import pytest

from conftest import make_plan
from planner_critic.adapters._audit import AuditTrail
from planner_critic.adapters.langgraph import (
    ApprovalHook,
    PlanNotApprovedError,
    with_approval_hook,
)
from planner_critic.approval import ApprovalGate, resolve_threshold
from planner_critic.schema.goal import RiskTolerance
from planner_critic.types import ApprovedPlan


def _make_approved_plan() -> ApprovedPlan:
    gate = ApprovalGate(RiskTolerance.BALANCED)
    _satisfied, outcome = resolve_threshold([], RiskTolerance.BALANCED)
    return gate.approve(make_plan(), outcome)


class TestApprovalHook:
    def test_check_without_approved_plan_raises(self) -> None:
        hook = ApprovalHook()
        with pytest.raises(PlanNotApprovedError):
            hook.check()

    def test_check_with_approved_plan_succeeds(self) -> None:
        approved = _make_approved_plan()
        hook = ApprovalHook(approved)
        result = hook.check()
        assert result is approved

    def test_approved_plan_property(self) -> None:
        approved = _make_approved_plan()
        hook = ApprovalHook(approved)
        assert hook.approved_plan is approved

    def test_approved_plan_property_none(self) -> None:
        hook = ApprovalHook()
        assert hook.approved_plan is None

    def test_check_records_audit(self) -> None:
        approved = _make_approved_plan()
        audit = AuditTrail()
        hook = ApprovalHook(approved, audit=audit)

        hook.check()

        last = audit.last_event()
        assert last is not None
        assert last.adapter == "langgraph"
        assert last.event == "re_gate_check"


class TestWithApprovalHook:
    def test_decorated_fn_runs_when_approved(self) -> None:
        approved = _make_approved_plan()
        hook = ApprovalHook(approved)
        called = False

        def my_node(state: dict[str, str]) -> dict[str, str]:
            nonlocal called
            called = True
            return state

        wrapped = with_approval_hook(hook, my_node)
        result = wrapped({"key": "val"})
        assert called
        assert result == {"key": "val"}

    def test_decorated_fn_raises_when_not_approved(self) -> None:
        hook = ApprovalHook()
        called = False

        def my_node(state: dict[str, str]) -> dict[str, str]:
            nonlocal called
            called = True
            return state

        wrapped = with_approval_hook(hook, my_node)
        with pytest.raises(PlanNotApprovedError):
            wrapped({"key": "val"})
        assert not called
