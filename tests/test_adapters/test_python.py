"""Tests for the raw Python adapter (python.py).

Uses fake roles from conftest.py so tests are hermetic.
"""

from conftest import EmptyCritic, ScriptedCritic, ScriptedPlanner, make_goal, make_plan
from planner_critic.adapters._audit import AuditTrail
from planner_critic.adapters.python import PlannerCriticPlan, plan
from planner_critic.engine import Engine
from planner_critic.loop import LoopConfig
from planner_critic.schema.goal import RiskTolerance
from planner_critic.types import Finding, Severity


class TestPlanFunction:
    def test_approved_plan(self, empty_critic: EmptyCritic) -> None:
        planner = ScriptedPlanner([make_plan()])
        engine = Engine(planner, empty_critic, LoopConfig(mode="deterministic-first"))
        goal = make_goal()

        result = plan(engine, goal)

        assert result.is_approved
        assert result.approved_plan is not None
        assert result.approved_plan.plan.id == "plan-1"

    def test_escalated_plan(self) -> None:
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
        goal = make_goal(tolerance=RiskTolerance.STRICT)

        result = plan(engine, goal)

        assert not result.is_approved
        assert result.approved_plan is None
        assert result.escalation is not None

    def test_with_audit_trail(self, empty_critic: EmptyCritic) -> None:
        planner = ScriptedPlanner([make_plan()])
        engine = Engine(planner, empty_critic, LoopConfig(mode="deterministic-first"))
        goal = make_goal()
        audit = AuditTrail()

        result = plan(engine, goal, audit=audit)

        assert result.is_approved
        events = audit.get_events()
        assert len(events) == 2
        assert events[0].event == "plan_requested"
        assert events[1].event == "plan_approved"


class TestPlannerCriticPlan:
    def test_plan_method(self, empty_critic: EmptyCritic) -> None:
        planner = ScriptedPlanner([make_plan()])
        engine = Engine(planner, empty_critic, LoopConfig(mode="deterministic-first"))
        wrapper = PlannerCriticPlan(engine)

        result = wrapper.plan(make_goal())

        assert result.is_approved

    def test_with_audit(self, empty_critic: EmptyCritic) -> None:
        planner = ScriptedPlanner([make_plan()])
        engine = Engine(planner, empty_critic, LoopConfig(mode="deterministic-first"))
        audit = AuditTrail()
        wrapper = PlannerCriticPlan(engine, audit=audit)

        wrapper.plan(make_goal())

        events = audit.get_events()
        assert len(events) == 2
