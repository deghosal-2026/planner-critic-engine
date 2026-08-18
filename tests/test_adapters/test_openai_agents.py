"""Tests for the OpenAI Agents SDK adapter (openai_agents.py)."""

import pytest

from planner_critic.adapters._audit import AuditTrail
from planner_critic.adapters.openai_agents import PlanGuardrail, PlanNotApprovedError
from planner_critic.engine import Engine
from planner_critic.loop import LoopConfig
from planner_critic.schema.goal import RiskTolerance
from planner_critic.types import Finding, Severity

from conftest import EmptyCritic, ScriptedCritic, ScriptedPlanner, make_goal, make_plan


class TestPlanGuardrail:
    def test_check_approves_plan(self, empty_critic):
        planner = ScriptedPlanner([make_plan()])
        engine = Engine(planner, empty_critic, LoopConfig(mode="deterministic-first"))
        guardrail = PlanGuardrail(engine, make_goal())

        result = guardrail.check()

        assert result.is_approved
        assert result.approved_plan is not None

    def test_check_raises_when_not_approved(self):
        planner = ScriptedPlanner([make_plan()])
        blocker = Finding(
            id="f:1", task_id="t1", version=1, severity=Severity.BLOCKER,
            reason_code="unsafe_ordering", message="blocker"
        )
        critic = ScriptedCritic([[blocker]])
        engine = Engine(planner, critic, LoopConfig(mode="deterministic-first"))
        guardrail = PlanGuardrail(engine, make_goal(tolerance=RiskTolerance.STRICT))

        with pytest.raises(PlanNotApprovedError):
            guardrail.check()

    def test_result_property_before_check(self):
        planner = ScriptedPlanner([make_plan()])
        engine = Engine(planner, EmptyCritic(), LoopConfig(mode="deterministic-first"))
        guardrail = PlanGuardrail(engine, make_goal())

        assert guardrail.result is None

    def test_result_property_after_check(self, empty_critic):
        planner = ScriptedPlanner([make_plan()])
        engine = Engine(planner, empty_critic, LoopConfig(mode="deterministic-first"))
        guardrail = PlanGuardrail(engine, make_goal())

        result = guardrail.check()
        assert guardrail.result is result

    def test_check_caches_result(self, empty_critic):
        planner = ScriptedPlanner([make_plan()])
        engine = Engine(planner, empty_critic, LoopConfig(mode="deterministic-first"))
        guardrail = PlanGuardrail(engine, make_goal())

        result1 = guardrail.check()
        result2 = guardrail.check()
        assert result1 is result2

    def test_with_audit(self, empty_critic):
        planner = ScriptedPlanner([make_plan()])
        engine = Engine(planner, empty_critic, LoopConfig(mode="deterministic-first"))
        audit = AuditTrail()
        guardrail = PlanGuardrail(engine, make_goal(), audit=audit)

        guardrail.check()

        events = audit.get_events()
        assert len(events) == 2
        assert events[0].event == "plan_requested"
        assert events[1].event == "plan_approved"