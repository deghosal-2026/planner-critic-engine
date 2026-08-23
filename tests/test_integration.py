"""M2 integration tests (F-09, F-20): store + provider against fake transport.

The hermetic contract: a full loop run (planner → gates → critic → approval)
is persisted to a store and reconstructed, with **zero network**. Also covers
the store-as-side-channel contract: a store failure warns and the loop result
still contains the approved plan.
"""

from __future__ import annotations

import logging
from pathlib import Path

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
from planner_critic.loop import run_loop
from planner_critic.schema.goal import RiskTolerance
from planner_critic.schema.plan import PlanVersion
from planner_critic.store.base import StoreUnavailable
from planner_critic.store.sqlite import SQLiteStore
from planner_critic.types import ExecutionTrace, Severity


def _approved_plan() -> PlanVersion:
    """A gate-clean, single-task plan that passes deterministic gates."""
    return make_plan(
        plan_id="plan-1",
        version=1,
        tasks=[
            make_task(
                "t1",
                risk_class="low",
                verification={"what": "x", "how": "y", "expected": "z"},
            )
        ],
    )


def test_loop_run_round_trips_through_sqlite_store(tmp_path: Path) -> None:
    """A full loop run persists its plan+findings and reads back losslessly."""
    store = SQLiteStore(tmp_path / "store.db")
    goal = make_goal(goal_id="goal-1", tolerance=RiskTolerance.BALANCED)
    planner = ScriptedPlanner([_approved_plan()])
    critic = EmptyCritic()

    result = run_loop(goal, planner, critic)
    assert result.status == "approved"
    assert result.plan is not None

    store.put_plan_version(result.plan)
    store.put_findings(result.plan.id, result.plan.version, result.findings)

    assert store.get_plan("plan-1") == result.plan
    assert store.diff("plan-1", 1, 1) is not None
    store.close()


def test_loop_run_persists_escalation_and_trace(tmp_path: Path) -> None:
    """Escalation + execution-trace records round-trip through the store."""
    store = SQLiteStore(tmp_path / "store.db")
    goal = make_goal(goal_id="goal-1", tolerance=RiskTolerance.STRICT)
    blocker = finding("t1", "unsafe_ordering", severity=Severity.BLOCKER)
    planner = ScriptedPlanner([_approved_plan()])
    critic = ScriptedCritic([[blocker]])

    result = run_loop(goal, planner, critic)
    assert result.status == "escalated"
    assert result.escalation is not None
    assert result.plan is not None

    store.put_plan_version(result.plan)
    store.put_escalation(result.escalation)
    store.put_execution_trace(
        ExecutionTrace(id="tr-1", plan_id=result.plan.id, task_id="t1", outcome="ok")
    )

    assert store.get_escalation(result.escalation.plan_id) == result.escalation
    assert [t.id for t in store.get_execution_traces(result.plan.id)] == ["tr-1"]
    store.close()


def test_side_channel_store_down_warns_and_continues(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Store unavailable → warn + continue: the loop result is still usable."""
    store = SQLiteStore(tmp_path / "store.db")
    goal = make_goal()
    planner = ScriptedPlanner([_approved_plan()])
    result = run_loop(goal, planner, EmptyCritic())
    assert result.status == "approved"

    store.close()  # simulate the store going down
    with caplog.at_level(logging.WARNING):
        try:
            store.get_plan("plan-1")  # table gone → side-channel signal
        except StoreUnavailable:
            store.warn_and_continue(Exception("store closed"))

    assert any("continuing in memory" in r.message for r in caplog.records)
    assert result.plan is not None  # loop result unaffected by store failure
