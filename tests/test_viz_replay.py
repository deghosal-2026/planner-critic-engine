"""Trace replay tests (F-76): walk version history with --step and --format json."""

from __future__ import annotations

import json

from conftest import make_plan, make_task
from planner_critic.store.base import InMemoryStore
from planner_critic.types import Finding, Severity
from planner_critic.viz.replay import replay


def _seed_store() -> InMemoryStore:
    """A store with two revisions + findings for one plan."""
    store = InMemoryStore()
    v1 = make_plan(plan_id="plan-1", version=1, tasks=[make_task("t1")])
    v2 = make_plan(
        plan_id="plan-1",
        version=2,
        parent="plan-1",
        tasks=[make_task("t1"), make_task("t2")],
    )
    store.put_plan_version(v1)
    store.put_plan_version(v2)
    f1 = Finding(
        id="f1", task_id="t1", version=1,
        severity=Severity.BLOCKER, reason_code="missing_rollback", message="no rollback",
    )
    f2 = Finding(
        id="f2", task_id="t2", version=2,
        severity=Severity.WARNING, reason_code="llm_risk", message="risk",
    )
    store.put_findings("plan-1", 1, [f1])
    store.put_findings("plan-1", 2, [f2])
    return store


def test_replay_returns_all_steps() -> None:
    """Replay returns one step per revision, in version order."""
    store = _seed_store()
    result = replay(store, "plan-1")
    assert len(result.steps) == 2
    assert result.steps[0].version == 1
    assert result.steps[1].version == 2


def test_replay_step_carries_findings() -> None:
    """Each step includes the findings produced against that revision."""
    store = _seed_store()
    result = replay(store, "plan-1")
    assert len(result.steps[0].findings) == 1
    assert result.steps[0].findings[0].reason_code == "missing_rollback"
    assert len(result.steps[1].findings) == 1


def test_replay_step_limit() -> None:
    """--step N limits the number of steps returned."""
    store = _seed_store()
    result = replay(store, "plan-1", step=1)
    assert len(result.steps) == 1
    assert result.steps[0].version == 1


def test_replay_json_format() -> None:
    """JSON format produces valid JSON with the expected structure."""
    store = _seed_store()
    result = replay(store, "plan-1", fmt="json")
    text = result.to_json()
    data = json.loads(text)
    assert len(data["steps"]) == 2
    assert data["steps"][0]["version"] == 1


def test_replay_unknown_plan() -> None:
    """Replaying an unknown plan returns empty."""
    store = InMemoryStore()
    result = replay(store, "ghost")
    assert result.steps == []
