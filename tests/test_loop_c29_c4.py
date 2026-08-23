"""C29 / C4 loop budget and termination depth (#92)."""

from __future__ import annotations

from conftest import EmptyCritic, ScriptedCritic, ScriptedPlanner, make_goal, make_plan, make_task
from planner_critic.loop import LoopConfig, run_loop
from planner_critic.loop.budget import SpendState
from planner_critic.reason_codes import BUDGET_EXCEEDED, CONVERGED_STALLED, REGRESSION_THRASHING
from planner_critic.schema.goal import Budget, Constraints, Goal, RiskTolerance
from planner_critic.schema.plan import PlanVersion
from planner_critic.types import Finding, Severity


def _clean_plan() -> PlanVersion:
    return make_plan(
        tasks=[
            make_task(
                "t1", risk_class="low", verification={"what": "x", "how": "y", "expected": "z"}
            )
        ]
    )


def _dirty_plan() -> PlanVersion:
    return make_plan(tasks=[make_task("t1", risk_class="critical")])


def test_c29_max_calls_ceiling() -> None:
    goal = Goal(
        id="g-c29-calls",
        description="budget",
        constraints=Constraints(budget=Budget(max_calls=1, max_revisions=5)),
        risk_tolerance=RiskTolerance.STRICT,
    )
    state = SpendState()
    state.calls_used = 2
    result = run_loop(
        goal,
        ScriptedPlanner([_dirty_plan()]),
        EmptyCritic(),
        config=LoopConfig(mode="deterministic-first", revision_cap=5),
        spend=state,
    )
    assert result.status == "escalated"
    assert result.reason_code == BUDGET_EXCEEDED


def test_c29_max_tokens_ceiling() -> None:
    goal = Goal(
        id="g-c29-tokens",
        description="budget",
        constraints=Constraints(budget=Budget(max_tokens=100, max_revisions=5)),
        risk_tolerance=RiskTolerance.STRICT,
    )
    state = SpendState()
    state.tokens_used = 500
    result = run_loop(
        goal,
        ScriptedPlanner([_dirty_plan()]),
        EmptyCritic(),
        config=LoopConfig(mode="deterministic-first", revision_cap=5),
        spend=state,
    )
    assert result.status == "escalated"
    assert result.reason_code == BUDGET_EXCEEDED


def test_c4_regression_thrashing_produced() -> None:
    goal = make_goal(tolerance=RiskTolerance.STRICT)
    planner = ScriptedPlanner([_clean_plan()])
    critic = ScriptedCritic(
        [
            [
                Finding(
                    id="w1",
                    task_id="t1",
                    version=1,
                    severity=Severity.WARNING,
                    reason_code="llm_missing_steps",
                    message="check",
                )
            ],
            [
                Finding(
                    id="w1",
                    task_id="t1",
                    version=1,
                    severity=Severity.WARNING,
                    reason_code="llm_missing_steps",
                    message="check",
                ),
                Finding(
                    id="b1",
                    task_id="t1",
                    version=1,
                    severity=Severity.BLOCKER,
                    reason_code="missing_verification",
                    message="new blocker",
                ),
            ],
        ]
    )
    result = run_loop(goal, planner, critic, config=LoopConfig(revision_cap=3))
    assert result.status == "escalated"
    assert result.reason_code == REGRESSION_THRASHING


def test_c4_converged_stalled_across_goals() -> None:
    for i in range(5):
        goal = make_goal(goal_id=f"g-{i}", tolerance=RiskTolerance.STRICT)
        planner = ScriptedPlanner([_clean_plan()])
        critic = ScriptedCritic(
            [
                [
                    Finding(
                        id="b1",
                        task_id="t1",
                        version=1,
                        severity=Severity.BLOCKER,
                        reason_code="missing_rollback",
                        message="no rollback",
                    )
                ],
                [
                    Finding(
                        id="b1",
                        task_id="t1",
                        version=1,
                        severity=Severity.BLOCKER,
                        reason_code="missing_rollback",
                        message="no rollback",
                    )
                ],
            ]
        )
        result = run_loop(goal, planner, critic, config=LoopConfig(revision_cap=4))
        assert result.status == "escalated"
        assert result.reason_code == CONVERGED_STALLED
