"""Tests for the LangGraph adapter (langgraph.py)."""

import pytest

from planner_critic.adapters._audit import AuditTrail
from planner_critic.adapters.langgraph import (
    ApprovalHook,
    PlanNotApprovedError,
    with_approval_hook,
)
from planner_critic.approval import ApprovalGate, resolve_threshold
from planner_critic.schema.goal import RiskTolerance

from conftest import make_plan


def _make_approved_plan():
    gate = ApprovalGate(RiskTolerance.BALANCED)
    satisfied, outcome = resolve_threshold([], RiskTolerance.BALANCED)
    return gate.approve(make_plan(), outcome)


class TestApprovalHook:
    def test_check_without_approved_plan_raises(self):
        hook = ApprovalHook()
        with pytest.raises(PlanNotApprovedError):
            hook.check()

    def test_check_with_approved_plan_succeeds(self):
        approved = _make_approved_plan()
        hook = ApprovalHook(approved)
        result = hook.check()
        assert result is approved

    def test_approved_plan_property(self):
        approved = _make_approved_plan()
        hook = ApprovalHook(approved)
        assert hook.approved_plan is approved

    def test_approved_plan_property_none(self):
        hook = ApprovalHook()
        assert hook.approved_plan is None

    def test_check_records_audit(self):
        approved = _make_approved_plan()
        audit = AuditTrail()
        hook = ApprovalHook(approved, audit=audit)

        hook.check()

        last = audit.last_event()
        assert last is not None
        assert last.adapter == "langgraph"
        assert last.event == "re_gate_check"


class TestWithApprovalHook:
    def test_decorated_fn_runs_when_approved(self):
        approved = _make_approved_plan()
        hook = ApprovalHook(approved)
        called = False

        def my_node(state):
            nonlocal called
            called = True
            return state

        wrapped = with_approval_hook(hook, my_node)
        result = wrapped({"key": "val"})
        assert called
        assert result == {"key": "val"}

    def test_decorated_fn_raises_when_not_approved(self):
        hook = ApprovalHook()
        called = False

        def my_node(state):
            nonlocal called
            called = True
            return state

        wrapped = with_approval_hook(hook, my_node)
        with pytest.raises(PlanNotApprovedError):
            wrapped({"key": "val"})
        assert not called