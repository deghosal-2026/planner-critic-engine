"""CUJ 1 E2E test (M6 T7): "init → first approved plan" path.

Hermetic test that exercises the full Engine flow with scripted roles:
1. Create a temp directory with `.plancritic/` structure
2. Create a Goal JSON
3. Run ``plan`` via Engine with scripted roles
4. Verify the plan was approved or escalated
5. Run ``explain`` on the result
6. Run ``replay`` on the result
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from conftest import EmptyCritic, ScriptedPlanner, make_goal, make_plan, make_task
from planner_critic.engine import Engine
from planner_critic.explain import explain
from planner_critic.loop import LoopConfig
from planner_critic.store.base import InMemoryStore
from planner_critic.store.sqlite import SQLiteStore
from planner_critic.viz.replay import replay


@pytest.fixture
def temp_cuj1_dir() -> str:
    """Create a temporary directory simulating a project root."""
    tmpdir = tempfile.mkdtemp()
    plancritic_dir = os.path.join(tmpdir, ".plancritic")
    os.makedirs(plancritic_dir, exist_ok=True)
    config_path = os.path.join(plancritic_dir, "config.json")
    with open(config_path, "w") as f:
        json.dump({"store_path": os.path.join(plancritic_dir, "store.db")}, f)
    return tmpdir


def test_cuj1_init_to_first_approved_plan(temp_cuj1_dir: str) -> None:
    """Full CUJ 1 arc: init → plan → approve → explain → replay."""
    plancritic_dir = os.path.join(temp_cuj1_dir, ".plancritic")
    store_path = os.path.join(plancritic_dir, "store.db")

    # 1. Create a Goal.
    goal = make_goal(goal_id="cuj1-goal", description="Migrate auth provider")

    # 2. Run plan with scripted roles that produce an immediately approvable plan.
    planner = ScriptedPlanner([make_plan(plan_id="cuj1-plan", goal_id="cuj1-goal", tasks=[make_task("t1")])])
    engine = Engine(planner=planner, critic=EmptyCritic(), config=LoopConfig(revision_cap=3))
    result = engine.plan(goal)

    # 3. Verify the plan was approved.
    assert result.status == "approved", f"expected approved, got {result.status}"
    assert result.is_approved
    assert result.approved_plan is not None
    assert result.plan is not None

    # 4. Persist to the store.
    store = SQLiteStore(store_path)
    assert result.plan is not None
    store.put_plan_version(result.plan)
    store.put_findings(result.plan.id, result.plan.version, result.findings)
    store.close()

    # 5. Run explain on the result.
    store2 = SQLiteStore(store_path)
    explain_result = explain(store2, "cuj1-plan")
    assert explain_result.plan_id == "cuj1-plan"
    assert len(explain_result.decisions) >= 1
    last_decision = explain_result.decisions[-1]
    assert last_decision.action in ("approved", "escalated")

    # 6. Run replay on the result.
    replay_result = replay(store2, "cuj1-plan")
    assert replay_result.plan_id == "cuj1-plan"
    assert len(replay_result.steps) >= 1
    assert replay_result.steps[0].version == 1
    store2.close()

    # 7. Verify replay JSON serialization.
    replay_json = replay_result.to_json()
    parsed = json.loads(replay_json)
    assert parsed["plan_id"] == "cuj1-plan"
    assert len(parsed["steps"]) >= 1


def test_cuj1_with_in_memory_store() -> None:
    """CUJ 1 using InMemoryStore (no filesystem needed)."""
    store = InMemoryStore()
    goal = make_goal(goal_id="mem-goal", description="Simple task")
    planner = ScriptedPlanner([make_plan(plan_id="mem-plan", goal_id="mem-goal", tasks=[make_task("t1")])])
    engine = Engine(planner=planner, critic=EmptyCritic(), config=LoopConfig(revision_cap=3))
    result = engine.plan(goal)

    assert result.status == "approved"
    assert result.approved_plan is not None
    assert result.plan is not None

    store.put_plan_version(result.plan)
    store.put_findings(result.plan.id, result.plan.version, result.findings)

    explain_result = explain(store, "mem-plan")
    assert explain_result.plan_id == "mem-plan"
    assert len(explain_result.decisions) >= 1

    replay_result = replay(store, "mem-plan")
    assert len(replay_result.steps) >= 1


def test_cuj1_escalates_for_high_risk() -> None:
    """CUJ 1 with a blocker task that cannot pass → escalates."""
    store = InMemoryStore()
    goal = make_goal(goal_id="esc-goal", description="Hail mary task")
    planner = ScriptedPlanner(
        [make_plan(plan_id="esc-plan", goal_id="esc-goal", tasks=[make_task("t1", risk_class="critical")])]
    )
    engine = Engine(planner=planner, critic=EmptyCritic(), config=LoopConfig(revision_cap=1))
    result = engine.plan(goal)

    assert result.status == "escalated"
    assert result.escalation is not None
    assert result.plan is not None

    store.put_plan_version(result.plan)
    store.put_findings(result.plan.id, result.plan.version, result.findings)
    store.put_escalation(result.escalation)

    explain_result = explain(store, "esc-plan")
    assert len(explain_result.decisions) >= 1
    assert explain_result.decisions[-1].action == "escalated"

    replay_result = replay(store, "esc-plan")
    assert len(replay_result.steps) >= 1


def test_cuj1_init_directory_structure(temp_cuj1_dir: str) -> None:
    """Verify the .plancritic directory structure was created."""
    plancritic_dir = os.path.join(temp_cuj1_dir, ".plancritic")
    assert os.path.isdir(plancritic_dir)
    config_path = os.path.join(plancritic_dir, "config.json")
    assert os.path.isfile(config_path)
    with open(config_path) as f:
        config = json.load(f)
    assert "store_path" in config
