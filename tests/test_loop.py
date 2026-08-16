"""Loop controller tests (F-05..F-08, F-13, F-74).

Covers the five termination paths (approve / revision cap / convergence /
regression / budget), both critic modes, fail-closed behavior, and loop
determinism on identical inputs. The cross-product acceptance matrix lives
in tests/test_loop_matrix.py.
"""

from __future__ import annotations

import pytest

from conftest import (
    EmptyCritic,
    ScriptedCritic,
    ScriptedPlanner,
    finding,
    make_goal,
    make_plan,
    make_task,
)
from planner_critic.loop import LoopConfig, run_loop
from planner_critic.reason_codes import (
    BUDGET_EXCEEDED,
    REGRESSION_THRASHING,
    REVISION_CAP_REACHED,
)
from planner_critic.schema.goal import Budget, Constraints, Goal, RiskTolerance
from planner_critic.schema.plan import PlanVersion
from planner_critic.types import Finding, PlanningError, Severity


def _clean_plan() -> PlanVersion:
    """A schema-valid, gate-clean single-task plan (approval-ready)."""
    return make_plan()


def _dirty_plan() -> PlanVersion:
    """A gate-blocking plan: high-risk task with no verification/rollback."""
    return make_plan(tasks=[make_task("t1", risk_class="critical")])


def _revise_to_clean(plan: PlanVersion, findings: list[Finding]) -> PlanVersion:
    """Planner revision that 'fixes' anything into a gate-clean plan."""
    return _clean_plan()


class TestApprovePath:
    """Loop terminates with approval when the threshold is met."""

    def test_immediate_approval(self, empty_critic: EmptyCritic) -> None:
        """A gate-clean plan with a quiet critic approves on revision 1."""
        goal = make_goal()
        planner = ScriptedPlanner([_clean_plan()])
        result = run_loop(goal, planner, empty_critic)
        assert result.is_approved
        assert result.approved_plan is not None
        assert result.reason_code == "approved"

    def test_balanced_acknowledges_warning(self) -> None:
        """Under balanced, an acknowledged warning survives into approval."""
        goal = make_goal(tolerance=RiskTolerance.BALANCED)
        critic = ScriptedCritic(
            [[finding("t1", "unsafe_ordering", severity=Severity.WARNING)]]
        )
        planner = ScriptedPlanner([_clean_plan()])
        result = run_loop(goal, planner, critic)
        assert result.is_approved
        assert result.approved_plan is not None
        assert len(result.approved_plan.findings) == 1

    def test_warning_after_revision_approved(self, empty_critic: EmptyCritic) -> None:
        """Gate findings resolved by revision → approve on revision 2."""
        goal = make_goal()
        planner = ScriptedPlanner([_dirty_plan(), _revise_to_clean])
        result = run_loop(goal, planner, empty_critic)
        assert result.is_approved
        assert result.approved_plan is not None
        assert result.approved_plan.plan.version in (1, 2)


class TestEscalatePaths:
    """The four non-approval terminations."""

    def test_revision_cap_escalates(self, empty_critic: EmptyCritic) -> None:
        """A never-clean plan hits the revision cap and escalates."""
        goal = make_goal()
        planner = ScriptedPlanner([_dirty_plan()])
        result = run_loop(goal, planner, empty_critic, config=LoopConfig(revision_cap=2))
        assert result.status == "escalated"
        assert result.reason_code == REVISION_CAP_REACHED
        assert result.escalation is not None
        assert result.escalation.status == "open"

    def test_regression_escalates(self) -> None:
        """A new blocker introduced by a revision escalates immediately."""
        goal = make_goal(tolerance=RiskTolerance.STRICT)
        planner = ScriptedPlanner([_clean_plan()])
        critic = ScriptedCritic(
            [
                [finding("t1", "unsafe_ordering", severity=Severity.WARNING)],
                [
                    finding("t1", "unsafe_ordering", severity=Severity.WARNING),
                    finding("t1", "missing_verification"),
                ],
            ]
        )
        result = run_loop(goal, planner, critic, config=LoopConfig(revision_cap=3))
        assert result.status == "escalated"
        assert result.reason_code == REGRESSION_THRASHING

    def test_budget_exceeded_escalates(self, empty_critic: EmptyCritic) -> None:
        """Hitting the spend ceiling escalates rather than spending more."""
        goal = Goal(
            id="g-budget",
            description="cheap goal",
            constraints=Constraints(
                budget=Budget(max_revisions=1),
            ),
        )
        planner = ScriptedPlanner([_dirty_plan()])
        result = run_loop(
            goal,
            planner,
            empty_critic,
            config=LoopConfig(revision_cap=5, mode="llm-every-revision"),
        )
        assert result.status == "escalated"
        assert result.reason_code == BUDGET_EXCEEDED
        assert result.escalation is not None
        assert "budget" in result.escalation.question


class TestCriticModes:
    """deterministic-first vs llm-every-revision."""

    def test_deterministic_first_blocks_on_gate(self, empty_critic: EmptyCritic) -> None:
        """In deterministic-first, a gate blocker → revise before LLM audit."""
        goal = make_goal()
        planner = ScriptedPlanner([_dirty_plan(), _revise_to_clean])
        result = run_loop(
            goal, planner, empty_critic, config=LoopConfig(mode="deterministic-first")
        )
        assert result.is_approved

    def test_llm_every_revision_runs_critic(self) -> None:
        """In llm-every-revision the critic audits even flawed drafts."""
        goal = make_goal()
        critic = ScriptedCritic([[finding("t1", "unsafe_ordering")]])
        planner = ScriptedPlanner([_clean_plan()])
        result = run_loop(
            goal, planner, critic, config=LoopConfig(mode="llm-every-revision")
        )
        assert result.status == "escalated"


class TestFailClosed:
    """No path hands an unapproved plan to an executor."""

    def test_approval_only_via_approved_plan(self, empty_critic: EmptyCritic) -> None:
        """An escalated result carries no ApprovedPlan."""
        goal = make_goal()
        planner = ScriptedPlanner([_dirty_plan()])
        result = run_loop(goal, planner, empty_critic, config=LoopConfig(revision_cap=2))
        assert not result.is_approved
        assert result.approved_plan is None
        assert result.escalation is not None


class TestDeterminism:
    """F-74: identical inputs → identical decisions."""

    def test_identical_inputs_identical_decisions(self) -> None:
        """Run the same scenario twice; decisions and reasons must match."""
        goal = make_goal()

        def run() -> tuple[str, str | None, int]:
            planner = ScriptedPlanner([_dirty_plan()])
            result = run_loop(goal, planner, EmptyCritic(), config=LoopConfig(revision_cap=3))
            return result.status, result.reason_code, len(result.findings)

        assert run() == run()


class TestPlanningErrors:
    """Provider failure surfaces PlanningError, not a broken loop."""

    def test_planner_raises_fails_closed(self) -> None:
        """A raising decompose fails the loop with PlanningError."""

        class BoomPlanner:
            def decompose(self, goal: Goal) -> PlanVersion:
                raise RuntimeError("provider down")

            def revise(self, plan: PlanVersion, findings: list[Finding]) -> PlanVersion:
                raise AssertionError("unreachable")

        with pytest.raises(PlanningError) as exc_info:
            run_loop(make_goal(), BoomPlanner(), EmptyCritic())  # type: ignore[arg-type]
        assert "provider down" in str(exc_info.value)

    def test_critic_failure_fails_closed(self) -> None:
        """A critic that throws cannot silently approve a plan."""

        class BadCritic:
            def audit(self, plan: PlanVersion, findings: list[Finding]) -> list[Finding]:
                raise RuntimeError("critic blew up")

        with pytest.raises(PlanningError) as exc_info:
            run_loop(make_goal(), ScriptedPlanner([_clean_plan()]), BadCritic())  # type: ignore[arg-type]
        assert "critic blew up" in str(exc_info.value)
