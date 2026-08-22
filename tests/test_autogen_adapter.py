from __future__ import annotations

import pytest

from planner_critic.adapters.autogen import (
    AutoGenAdapter,
    PlanNotApprovedError,
    PreconditionDriftError,
)
from planner_critic.adapters._audit import AuditTrail
from planner_critic.engine import Engine
from planner_critic.loop import LoopConfig
from planner_critic.schema.goal import Goal, RiskTolerance
from conftest import ScriptedCritic, ScriptedPlanner, make_plan, make_task


class TestAutoGenAdapter:
    def test_gate_plan_approved(self) -> None:
        planner = ScriptedPlanner([make_plan(tasks=[make_task("t1")])])
        critic = ScriptedCritic([[]])
        engine = Engine(planner, critic, config=LoopConfig(mode="deterministic-first"))
        adapter = AutoGenAdapter(engine)

        result = adapter.gate_plan(Goal(id="test", description="test", risk_tolerance=RiskTolerance.BALANCED))
        assert result.is_approved

    def test_gate_plan_not_approved(self) -> None:
        planner = ScriptedPlanner([make_plan(tasks=[make_task("t1", risk_class="critical")])])
        critic = ScriptedCritic([[]])
        engine = Engine(planner, critic, config=LoopConfig(mode="deterministic-first"))
        adapter = AutoGenAdapter(engine)

        with pytest.raises(PlanNotApprovedError):
            adapter.gate_plan(Goal(id="test", description="test", risk_tolerance=RiskTolerance.STRICT))

    def test_execute_step_without_approval(self) -> None:
        planner = ScriptedPlanner([make_plan(tasks=[make_task("t1")])])
        critic = ScriptedCritic([[]])
        engine = Engine(planner, critic, config=LoopConfig(mode="deterministic-first"))
        adapter = AutoGenAdapter(engine)

        with pytest.raises(PlanNotApprovedError):
            adapter.execute_step("t1", {})

    def test_execute_step_found(self) -> None:
        planner = ScriptedPlanner([make_plan(tasks=[make_task("t1")])])
        critic = ScriptedCritic([[]])
        engine = Engine(planner, critic, config=LoopConfig(mode="deterministic-first"))
        adapter = AutoGenAdapter(engine)
        adapter.gate_plan(Goal(id="test", description="test", risk_tolerance=RiskTolerance.BALANCED))

        result = adapter.execute_step("t1", {"agent": "turn"})
        assert result == {"agent": "turn"}
        assert adapter.current_step == 1

    def test_execute_step_not_found(self) -> None:
        planner = ScriptedPlanner([make_plan(tasks=[make_task("t1")])])
        critic = ScriptedCritic([[]])
        engine = Engine(planner, critic, config=LoopConfig(mode="deterministic-first"))
        adapter = AutoGenAdapter(engine)
        adapter.gate_plan(Goal(id="test", description="test", risk_tolerance=RiskTolerance.BALANCED))

        with pytest.raises(ValueError, match="not found"):
            adapter.execute_step("nonexistent", {})

    def test_escalation_message_approved(self) -> None:
        planner = ScriptedPlanner([make_plan(tasks=[make_task("t1")])])
        critic = ScriptedCritic([[]])
        engine = Engine(planner, critic, config=LoopConfig(mode="deterministic-first"))
        adapter = AutoGenAdapter(engine)
        adapter.gate_plan(Goal(id="test", description="test", risk_tolerance=RiskTolerance.BALANCED))

        assert adapter.escalation_message() is None

    def test_audit_trail_recorded(self) -> None:
        audit = AuditTrail()
        planner = ScriptedPlanner([make_plan(tasks=[make_task("t1")])])
        critic = ScriptedCritic([[]])
        engine = Engine(planner, critic, config=LoopConfig(mode="deterministic-first"))
        adapter = AutoGenAdapter(engine, audit=audit)

        adapter.gate_plan(Goal(id="test", description="test", risk_tolerance=RiskTolerance.BALANCED))
        events = audit.get_events()
        assert len(events) == 2
        assert events[0].event == "plan_requested"
        assert events[1].event == "plan_approved"

    def test_precondition_drift_on_step(self) -> None:
        from planner_critic.schema.plan import Precondition
        t1 = make_task("t1", preconditions=[{"description": "db ready", "fact": "db_healthy", "established_by": "env"}])
        planner = ScriptedPlanner([make_plan(tasks=[t1])])
        critic = ScriptedCritic([[]])
        engine = Engine(planner, critic, config=LoopConfig(mode="deterministic-first"))
        adapter = AutoGenAdapter(engine)
        adapter.gate_plan(Goal(id="test", description="test", risk_tolerance=RiskTolerance.BALANCED))

        adapter.current_step = 0
        adapter.execute_step("t1", {})