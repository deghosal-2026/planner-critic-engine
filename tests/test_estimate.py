"""Deterministic complexity/cost estimate tests (F-17, §2.7d)."""

from __future__ import annotations

from conftest import make_plan, make_task
from planner_critic.estimate import (
    EstimateConfig,
    estimate_complexity,
    within_budget,
)
from planner_critic.schema.goal import Budget


def test_estimate_counts_steps_branches_and_irreversible() -> None:
    """Counts steps, parallel branches, and high-risk (irreversible) ops."""
    plan = make_plan(
        tasks=[
            make_task("t1", risk_class="critical"),
            make_task("t2", risk_class="low"),
            make_task("t3", risk_class="medium", parallel_group="g1"),
            make_task("t4", risk_class="high", parallel_group="g1"),
        ]
    )
    est = estimate_complexity(plan)
    assert est.step_count == 4
    assert est.parallel_branch_count == 1
    assert est.irreversible_op_count == 2  # critical + high


def test_estimate_is_deterministic() -> None:
    """The same plan produces the same estimate (determinism contract)."""
    plan = make_plan(tasks=[make_task("t1"), make_task("t2")])
    assert estimate_complexity(plan) == estimate_complexity(plan)


def test_estimate_llm_calls_scales_with_revision_cap() -> None:
    """Worst-case calls grow with the revision cap (2 calls/loop)."""
    plan = make_plan(tasks=[make_task("t1")])
    cap2 = estimate_complexity(plan, EstimateConfig(revision_cap=2))
    cap4 = estimate_complexity(plan, EstimateConfig(revision_cap=4))
    assert cap2.est_llm_calls == 4  # decompose + audit + revise + audit
    assert cap4.est_llm_calls == 8  # 2 calls x 4 revisions
    assert cap4.est_llm_calls > cap2.est_llm_calls


def test_estimate_token_cost_is_finite_and_positive() -> None:
    """The token-cost line is a finite positive dollar figure."""
    plan = make_plan(tasks=[make_task("t1")])
    est = estimate_complexity(plan)
    assert est.est_token_cost > 0
    assert est.est_token_cost < 0.01  # local-model placeholder is cheap


def test_estimate_zero_cost_to_compute() -> None:
    """Estimation never touches a provider (pure function of the plan)."""
    from planner_critic.types import PlanComplexity

    plan = make_plan(tasks=[make_task("t1")])
    assert isinstance(estimate_complexity(plan), PlanComplexity)


def test_within_budget_respects_calls_ceiling() -> None:
    """A max_calls ceiling below the estimate rejects the plan."""
    plan = make_plan(tasks=[make_task("t1")])
    est = estimate_complexity(plan)  # default cap 3 → 6 calls
    assert est.est_llm_calls == 6
    assert within_budget(Budget(max_calls=5), est) is False
    assert within_budget(Budget(max_calls=6), est) is True


def test_within_budget_respects_tokens_ceiling() -> None:
    """A max_tokens ceiling below the estimate rejects the plan."""
    plan = make_plan(tasks=[make_task("t1")])
    est = estimate_complexity(plan)
    assert within_budget(Budget(max_tokens=100), est) is False
    assert within_budget(Budget(max_tokens=10_000), est) is True


def test_within_budget_none_is_unbounded() -> None:
    """No budget means everything fits."""
    plan = make_plan(tasks=[make_task("t1")])
    assert within_budget(None, estimate_complexity(plan)) is True
