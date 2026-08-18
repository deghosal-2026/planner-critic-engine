"""Replan semantics tests (F-16, PRD §2.7b): patch / restart / abort.

Each policy determines how a mid-execution failure leads to a new plan
revision: ``patch`` revises remaining steps, ``restart`` re-decomposes from
scratch (keeping lineage), and ``abort`` halts. The replan function is a
pure stamping function: it wraps a revised PlanVersion with the correct
version metadata so the lineage is always reconstructable.
"""

from __future__ import annotations

import pytest

from conftest import make_goal, make_plan, make_task
from planner_critic.replan import ReplanAbort, replan
from planner_critic.schema.goal import ReplanPolicy


def test_patch_policy_stamps_next_version() -> None:
    """patch: version incremented, parent linked to the current plan."""
    current = make_plan(plan_id="plan-1", version=1, tasks=[make_task("t1"), make_task("t2")])
    goal = make_goal(replan_policy=ReplanPolicy.PATCH)

    revised = make_plan(plan_id="plan-1", version=2, parent="plan-1", tasks=[make_task("t2")])
    result = replan(goal, current, revised)

    assert result.version == current.version + 1
    assert result.parent_version == current.id
    assert result.id == current.id
    assert result.tasks == revised.tasks


def test_restart_policy_stamps_next_version() -> None:
    """restart: version incremented, parent linked (full lineage preserved)."""
    current = make_plan(plan_id="plan-1", version=1)
    goal = make_goal(replan_policy=ReplanPolicy.RESTART)

    revised = make_plan(plan_id="plan-1", version=2, parent="plan-1", tasks=[make_task("t1")])
    result = replan(goal, current, revised)

    assert result.version == current.version + 1
    assert result.parent_version == current.id


def test_abort_policy_raises() -> None:
    """abort: planning halts with a PlanningError."""
    current = make_plan(plan_id="plan-1", version=1)
    goal = make_goal(replan_policy=ReplanPolicy.ABORT)

    with pytest.raises(ReplanAbort, match="abort"):
        replan(goal, current, make_plan())


def test_default_policy_is_patch() -> None:
    """A goal without explicit replan_policy defaults to patch."""
    current = make_plan(plan_id="plan-1", version=1)
    goal = make_goal()  # defaults to ReplanPolicy.PATCH

    result = replan(goal, current, make_plan(plan_id="plan-1", version=2, parent="plan-1"))
    assert result.version == 2
    assert result.parent_version == current.id


def test_lineage_reconstructable() -> None:
    """The version chain from root to replan is traversable."""
    goal = make_goal()

    root = make_plan(plan_id="plan-1", version=1)
    v2 = make_plan(plan_id="plan-1", version=2, parent="plan-1")
    v3 = make_plan(plan_id="plan-1", version=3, parent="plan-1")

    r2 = replan(goal, root, v2)
    r3 = replan(goal, r2, v3)

    assert r3.parent_version == r2.id
    assert r2.parent_version == root.id
    assert r3.version == 3
    assert r2.version == 2
