from __future__ import annotations

import time

from conftest import EmptyCritic, ScriptedPlanner, make_goal, make_plan, make_task
from planner_critic.ledger import PreconditionLedger
from planner_critic.loop import LoopConfig, run_loop
from planner_critic.run_budget import RunBudget
from planner_critic.schema.goal import RiskTolerance
from planner_critic.schema.plan import PlanVersion


def _safe_plan() -> PlanVersion:
    return make_plan(tasks=[make_task("t1", risk_class="low")])


class TestM6Wiring:
    def test_loop_with_run_budget_not_exceeded(self) -> None:
        planner = ScriptedPlanner([_safe_plan()])
        critic = EmptyCritic()
        goal = make_goal(tolerance=RiskTolerance.BALANCED)
        budget = RunBudget(run_max_budget_usd=100.0)
        result = run_loop(
            goal=goal, planner=planner, critic=critic,
            config=LoopConfig(mode="deterministic-first", revision_cap=2),
            run_budget=budget,
        )
        assert result.status == "approved"

    def test_loop_with_precondition_ledger(self) -> None:
        ledger = PreconditionLedger()
        ledger.mark_satisfied("db_healthy", "env_probe")
        planner = ScriptedPlanner([_safe_plan()])
        critic = EmptyCritic()
        goal = make_goal(tolerance=RiskTolerance.BALANCED)
        result = run_loop(
            goal=goal, planner=planner, critic=critic,
            config=LoopConfig(mode="deterministic-first", revision_cap=1),
            precondition_ledger=ledger,
        )
        assert result.status == "approved"

    def test_loop_with_both(self) -> None:
        ledger = PreconditionLedger()
        planner = ScriptedPlanner([_safe_plan()])
        critic = EmptyCritic()
        goal = make_goal(tolerance=RiskTolerance.BALANCED)
        budget = RunBudget(run_max_depth=5)
        result = run_loop(
            goal=goal, planner=planner, critic=critic,
            config=LoopConfig(mode="deterministic-first", revision_cap=2),
            run_budget=budget, precondition_ledger=ledger,
        )
        assert result.status == "approved"

    def test_loop_run_budget_timeout(self) -> None:
        planner = ScriptedPlanner([_safe_plan(), _safe_plan()])
        critic = EmptyCritic()
        goal = make_goal(tolerance=RiskTolerance.STRICT)
        budget = RunBudget(run_max_time=0.001)
        time.sleep(0.005)
        result = run_loop(
            goal=goal, planner=planner, critic=critic,
            config=LoopConfig(mode="deterministic-first", revision_cap=2),
            run_budget=budget,
        )
        assert result.status == "escalated"
        assert result.reason_code == "run_timeout"
