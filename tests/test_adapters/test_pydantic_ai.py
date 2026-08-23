"""Tests for the PydanticAI adapter (pydantic_ai.py)."""

import pytest

from conftest import EmptyCritic, ScriptedCritic, ScriptedPlanner, make_goal, make_plan
from planner_critic.adapters._audit import AuditTrail
from planner_critic.adapters.pydantic_ai import ApprovalGuard, PlanNotApprovedError
from planner_critic.engine import Engine
from planner_critic.loop import LoopConfig
from planner_critic.schema.goal import RiskTolerance
from planner_critic.types import Finding, Severity


class TestApprovalGuard:
    def test_guard_approves_plan(self, empty_critic: EmptyCritic) -> None:
        planner = ScriptedPlanner([make_plan()])
        engine = Engine(planner, empty_critic, LoopConfig(mode="deterministic-first"))
        guard = ApprovalGuard(engine, make_goal())

        result = guard.guard()

        assert result.is_approved
        assert result.approved_plan is not None

    def test_guard_raises_when_not_approved(self) -> None:
        planner = ScriptedPlanner([make_plan()])
        blocker = Finding(
            id="f:1",
            task_id="t1",
            version=1,
            severity=Severity.BLOCKER,
            reason_code="unsafe_ordering",
            message="blocker",
        )
        critic = ScriptedCritic([[blocker]])
        engine = Engine(planner, critic, LoopConfig(mode="deterministic-first"))
        guard = ApprovalGuard(engine, make_goal(tolerance=RiskTolerance.STRICT))

        with pytest.raises(PlanNotApprovedError):
            guard.guard()

    def test_guard_caches_result(self, empty_critic: EmptyCritic) -> None:
        planner = ScriptedPlanner([make_plan()])
        engine = Engine(planner, empty_critic, LoopConfig(mode="deterministic-first"))
        guard = ApprovalGuard(engine, make_goal())

        result1 = guard.guard()
        result2 = guard.guard()
        assert result1 is result2

    def test_guard_with_audit(self, empty_critic: EmptyCritic) -> None:
        planner = ScriptedPlanner([make_plan()])
        engine = Engine(planner, empty_critic, LoopConfig(mode="deterministic-first"))
        audit = AuditTrail()
        guard = ApprovalGuard(engine, make_goal(), audit=audit)

        guard.guard()

        events = audit.get_events()
        assert len(events) == 2
        assert events[0].event == "plan_requested"
        assert events[1].event == "plan_approved"

    def test_guard_ctx_parameter(self, empty_critic: EmptyCritic) -> None:
        planner = ScriptedPlanner([make_plan()])
        engine = Engine(planner, empty_critic, LoopConfig(mode="deterministic-first"))
        guard = ApprovalGuard(engine, make_goal())

        result = guard.guard(ctx="some_context")
        assert result.is_approved
