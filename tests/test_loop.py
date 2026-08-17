"""Loop controller tests (F-05..F-08, F-13, F-74).

Covers the five termination paths (approve / revision cap / convergence /
regression / budget), both critic modes, fail-closed behavior, and loop
determinism on identical inputs. The cross-product acceptance matrix lives
in tests/test_loop_matrix.py.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
from planner_critic.loop.budget import SpendState
from planner_critic.loop.ttl import approval_expired
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

    def test_escalation_plan_is_last_audited_revision(self, empty_critic: EmptyCritic) -> None:
        """Surviving cap escalation must reference the audited revision+findings.

        Regression: the loop previously stamped one extra r{cap+1} revision
        that was never audited, while the escalation carried its (empty)
        prior findings. The escalated plan must be the last audited revision
        with the findings that blocked it.
        """
        goal = make_goal()
        planner = ScriptedPlanner([_dirty_plan()])
        result = run_loop(goal, planner, empty_critic, config=LoopConfig(revision_cap=2))
        assert result.status == "escalated"
        assert result.reason_code == REVISION_CAP_REACHED
        escalation = result.escalation
        assert escalation is not None
        assert escalation.version == 2, "escalation must point at revision 2, not 3"
        assert result.plan is not None
        assert escalation.plan_id == result.plan.id
        assert result.findings, "escalation must carry the blocking findings"
        assert any(f.severity is Severity.BLOCKER for f in result.findings)

    def test_plan_revision_gets_fresh_created_at(self, empty_critic: EmptyCritic) -> None:
        """Each revision carries its own timestamp, not the parent's.

        Regression: _plan_revision previously copied the parent's
        ``created_at`` onto the new revision, so every revision in a chain
        shared the root revision's timestamp.
        """
        goal = make_goal()
        planner = ScriptedPlanner([_dirty_plan(), _revise_to_clean])
        result = run_loop(goal, planner, empty_critic, config=LoopConfig(revision_cap=3))
        assert result.is_approved
        approved = result.approved_plan
        assert approved is not None
        parent_draft = planner.drafts[0]
        assert isinstance(parent_draft, PlanVersion)
        assert approved.plan.created_at is not None
        assert approved.plan.created_at != parent_draft.created_at


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

    def test_planner_returns_non_planversion_fails_closed(self) -> None:
        """A decompose that emits garbage must fail closed."""

        class GarbagePlanner:
            def decompose(self, goal: Goal) -> PlanVersion:
                return "not a plan"  # type: ignore[return-value]

        with pytest.raises(PlanningError) as exc_info:
            run_loop(make_goal(), GarbagePlanner(), EmptyCritic())  # type: ignore[arg-type]
        assert "non-PlanVersion" in str(exc_info.value)

    def test_planner_revise_raises_fails_closed(self) -> None:
        """A raise during revise fails the loop with PlanningError."""

        class BoomRevisePlanner:
            def decompose(self, goal: Goal) -> PlanVersion:
                return _dirty_plan()

            def revise(self, plan: PlanVersion, findings: list[Finding]) -> PlanVersion:
                raise RuntimeError("provider down during revise")

        with pytest.raises(PlanningError) as exc_info:
            run_loop(make_goal(), BoomRevisePlanner(), EmptyCritic())  # type: ignore[arg-type]
        assert "failed to revise" in str(exc_info.value)

    def test_planner_revises_to_garbage_fails_closed(self) -> None:
        """A revise that returns non-PlanVersion fails closed."""

        class GarbageRevisePlanner:
            def decompose(self, goal: Goal) -> PlanVersion:
                return _dirty_plan()

            def revise(self, plan: PlanVersion, findings: list[Finding]) -> PlanVersion:
                return object()  # type: ignore[return-value]

        with pytest.raises(PlanningError) as exc_info:
            run_loop(make_goal(), GarbageRevisePlanner(), EmptyCritic())  # type: ignore[arg-type]
        assert "non-PlanVersion" in str(exc_info.value)


class TestEscalationQuestion:
    """The escalated question matches the exit reason."""

    def test_question_without_blockers_names_reason(self) -> None:
        """A budget escalation with no blockers names the reason, not a blocker."""
        goal = Goal(
            id="g-question",
            description="strict goal with warnings",
            risk_tolerance=RiskTolerance.STRICT,
            constraints=Constraints(budget=Budget(max_revisions=1)),
        )
        critic = ScriptedCritic(
            [[finding("t1", "unsafe_ordering", severity=Severity.WARNING)]]
        )
        planner = ScriptedPlanner([_clean_plan()])
        result = run_loop(
            goal,
            planner,
            critic,
            config=LoopConfig(revision_cap=3),
        )
        assert result.status == "escalated"
        assert result.reason_code == BUDGET_EXCEEDED
        assert result.escalation is not None
        assert "budget_exceeded" in result.escalation.question

    def test_budget_checked_in_deterministic_first_blocker_path(
        self, empty_critic: EmptyCritic
    ) -> None:
        """A deterministic-first blocker loop still respects the budget."""
        goal = Goal(
            id="g-df-budget",
            description="cheap goal",
            constraints=Constraints(budget=Budget(max_revisions=1)),
        )
        planner = ScriptedPlanner([_dirty_plan()])
        result = run_loop(
            goal,
            planner,
            empty_critic,
            config=LoopConfig(revision_cap=5, mode="deterministic-first"),
        )
        assert result.status == "escalated"
        assert result.reason_code == BUDGET_EXCEEDED

    def test_cap_fallthrough_in_llm_every_revision(self) -> None:
        """LLM-every-revision with pending warnings escalates at the cap."""
        goal = make_goal(tolerance=RiskTolerance.STRICT)
        critic = ScriptedCritic(
            [
                [finding("t1", "unsafe_ordering", severity=Severity.WARNING)],
                [finding("t2", "unsafe_ordering", severity=Severity.WARNING)],
            ]
        )
        # Distinct task ids keep fingerprints apart so near-zero-diff does not
        # fire early; the strict tolerance keeps warnings pending until the
        # revision cap forces escalation.
        plan_a = make_plan(plan_id="plan-a", tasks=[make_task("tA")])
        plan_b = make_plan(plan_id="plan-b", tasks=[make_task("tB")])
        planner = ScriptedPlanner([plan_a, plan_b])
        result = run_loop(goal, planner, critic, config=LoopConfig(revision_cap=2))
        assert result.status == "escalated"
        assert result.reason_code == REVISION_CAP_REACHED
        assert result.findings


# --- Budget unit tests (SpendState) -----------------------------------------


def test_spend_state_already_exceeded_latches() -> None:
    """Once exceeded, check() returns True even if counters are within budget."""
    state = SpendState()
    state.exceeded = True
    assert state.check(Budget()) is True


def test_spend_state_max_calls_breach() -> None:
    """Exceeding max_calls sets exceeded and records the ceiling."""
    state = SpendState()
    state.calls_used = 5
    assert state.check(Budget(max_calls=3)) is True
    assert "max_calls" in state._hits


def test_spend_state_max_tokens_breach() -> None:
    """Exceeding max_tokens sets exceeded and records the ceiling."""
    state = SpendState()
    state.tokens_used = 1000
    assert state.check(Budget(max_tokens=500)) is True
    assert "max_tokens" in state._hits


def test_spend_state_record_llm_call_with_tokens() -> None:
    """record_llm_call increments both calls and tokens."""
    state = SpendState()
    state.record_llm_call(tokens=42)
    assert state.calls_used == 1
    assert state.tokens_used == 42


# --- TTL unit tests (approval_expired) --------------------------------------


def test_approval_expired_no_ttl_never_expires() -> None:
    """approval_ttl=None means the approval never expires."""
    assert approval_expired(datetime(2020, 1, 1, tzinfo=UTC), None) is False


def test_approval_expired_within_ttl() -> None:
    """An approval within its TTL window is not expired."""
    now = datetime(2026, 8, 16, 12, 0, 0, tzinfo=UTC)
    approved = now - timedelta(minutes=5)
    assert approval_expired(approved, timedelta(hours=1), now=now) is False


def test_approval_expired_beyond_ttl() -> None:
    """An approval past its TTL is expired."""
    now = datetime(2026, 8, 16, 12, 0, 0, tzinfo=UTC)
    approved = now - timedelta(hours=2)
    assert approval_expired(approved, timedelta(hours=1), now=now) is True
