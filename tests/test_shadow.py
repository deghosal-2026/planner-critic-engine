"""Shadow mode tests (F-14, PRD §2.7c): observe-only loop + shadow recording."""

from __future__ import annotations

from conftest import (
    EmptyCritic,
    ScriptedCritic,
    ScriptedPlanner,
    finding,
    make_goal,
    make_plan,
    make_task,
)
from planner_critic.loop import LoopConfig
from planner_critic.schema.goal import RiskTolerance
from planner_critic.shadow import run_shadow
from planner_critic.store.sqlite import SQLiteStore
from planner_critic.types import Severity


def _clean_plan():
    """A gate-clean, approval-ready plan."""
    return make_plan(
        tasks=[
            make_task(
                "t1",
                risk_class="low",
                verification={"what": "x", "how": "y", "expected": "z"},
            )
        ]
    )


def _blocker():
    """A blocker finding for the strict-tolerance shadow escalation."""
    return finding("t1", "unsafe_ordering", severity=Severity.BLOCKER)


def test_shadow_marks_result_mode_shadow() -> None:
    """A shadow run returns a LoopResult stamped mode='shadow'."""
    goal = make_goal()
    result = run_shadow(goal, ScriptedPlanner([_clean_plan()]), EmptyCritic())
    assert result.mode == "shadow"
    assert result.is_approved


def test_shadow_does_not_gate_approval() -> None:
    """Shadow mode never applies gating — approval decision is only recorded."""
    goal = make_goal()
    result = run_shadow(
        goal,
        ScriptedPlanner([_clean_plan()]),
        EmptyCritic(),
        config=LoopConfig(mode="deterministic-first"),
    )
    assert result.is_approved  # observe mode: same decision, no enforcement


def test_shadow_records_escalation_to_store(tmp_path) -> None:
    """A shadow escalation is persisted and diffable via the store."""
    store = SQLiteStore(tmp_path / "store.db")
    goal = make_goal(tolerance=RiskTolerance.STRICT)
    blocker = _blocker()
    result = run_shadow(
        goal,
        ScriptedPlanner([_clean_plan()]),
        ScriptedCritic([[blocker]]),
        store=store,
    )
    assert result.status == "escalated"
    assert result.escalation is not None
    assert store.get_escalation(result.escalation.plan_id) == result.escalation
    store.close()


def test_shadow_records_approved_plan_to_store(tmp_path) -> None:
    """An approved shadow plan is persisted to the store."""
    store = SQLiteStore(tmp_path / "store.db")
    goal = make_goal()
    result = run_shadow(goal, ScriptedPlanner([_clean_plan()]), EmptyCritic(), store=store)
    assert result.is_approved
    assert result.plan is not None
    assert store.get_plan(result.plan.id) == result.plan
    store.close()
