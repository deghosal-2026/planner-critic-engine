"""Engine facade + approval gate tests (F-08, F-73 fail-closed, DD-02)."""

from __future__ import annotations

import pytest

from conftest import (
    EmptyCritic,
    ScriptedPlanner,
    finding,
    make_goal,
    make_plan,
    make_task,
)
from planner_critic.approval import ApprovalGate, resolve_threshold
from planner_critic.engine import Engine
from planner_critic.loop import LoopConfig
from planner_critic.schema.goal import RiskTolerance
from planner_critic.types import ApprovedPlan, PlanningError, Severity


class TestApprovalGate:
    """Threshold resolution and fail-closed ApprovedPlan construction."""

    def test_resolve_strict_zero_warnings(self) -> None:
        """strict: warnings are pending; blockers always disqualify."""
        ok, outcome = resolve_threshold([], RiskTolerance.STRICT)
        assert ok
        assert outcome.satisfied

    def test_resolve_strict_warning_pending(self) -> None:
        """strict: a warning is pending, so the threshold is not met."""
        ok, outcome = resolve_threshold(
            [finding("t1", "unsafe_ordering", severity=Severity.WARNING)],
            RiskTolerance.STRICT,
        )
        assert not ok
        assert not outcome.satisfied
        assert len(outcome.pending_warnings) == 1

    def test_resolve_balanced_acknowledges(self) -> None:
        """balanced: warnings are acknowledged (not disqualifying)."""
        ok, outcome = resolve_threshold(
            [finding("t1", "unsafe_ordering", severity=Severity.WARNING)],
            RiskTolerance.BALANCED,
        )
        assert ok
        assert len(outcome.acknowledged) == 1
        assert outcome.pending_warnings == ()

    def test_blocker_always_disqualifies(self) -> None:
        """A blocker fails both postures; injection-safety is preserved."""
        blocker = finding("t1", "dependency_cycle")
        for tolerance in (RiskTolerance.STRICT, RiskTolerance.BALANCED):
            ok, outcome = resolve_threshold([blocker], tolerance)
            assert not ok
            assert len(outcome.blockers) == 1

    def test_approve_builds_approved_plan(self) -> None:
        """A threshold-passing outcome yields an ApprovedPlan."""
        gate = ApprovalGate(RiskTolerance.BALANCED)
        plan = make_plan()
        ok, outcome = resolve_threshold([], RiskTolerance.BALANCED)
        assert ok
        approved = gate.approve(plan, outcome)
        assert isinstance(approved, ApprovedPlan)
        assert approved.plan == plan

    def test_approve_raises_on_blocker(self) -> None:
        """Fail-closed: approve() refuses to construct from blockers."""
        gate = ApprovalGate(RiskTolerance.BALANCED)
        blocker = finding("t1", "missing_verification")
        ok, outcome = resolve_threshold([blocker], RiskTolerance.BALANCED)
        assert not ok
        with pytest.raises(PlanningError):
            gate.approve(make_plan(), outcome)

    def test_approve_raises_on_strict_pending(self) -> None:
        """strict + pending warning cannot be approved."""
        gate = ApprovalGate(RiskTolerance.STRICT)
        warning = finding("t1", "unsafe_ordering", severity=Severity.WARNING)
        ok, outcome = resolve_threshold([warning], RiskTolerance.STRICT)
        assert not ok
        with pytest.raises(PlanningError):
            gate.approve(make_plan(), outcome)


class TestEngineFacade:
    """Engine(roles, config).plan(goal) delegates to run_loop."""

    def test_engine_approves(self) -> None:
        """A clean scenario through the facade approves."""
        engine = Engine(
            planner=ScriptedPlanner([make_plan()]),
            critic=EmptyCritic(),
        )
        result = engine.plan(make_goal())
        assert result.is_approved

    def test_engine_escalates_on_cap(self) -> None:
        """A never-clean scenario through the facade escalates."""
        engine = Engine(
            planner=ScriptedPlanner([make_plan(tasks=[make_task("t1", risk_class="critical")])]),
            critic=EmptyCritic(),
            config=LoopConfig(revision_cap=2),
        )
        result = engine.plan(make_goal())
        assert result.status == "escalated"
