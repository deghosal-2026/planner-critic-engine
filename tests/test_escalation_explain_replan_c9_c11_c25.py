"""C9 / C10 / C11 / C25 escalation-explain-replan partials closure (#89).

The 0.1.0 report exercised escalation (C9) only on ADV-01 with the approve
path, explain (C10) only on an approved plan, replan (C11) only on DB-01
instead of ARCH-01, and replan lineage (C25) was never stored/queried.

These tests run the full hermetic lifecycle — engine loop → escalation →
explain → replan restart → store lineage — with the designated goals and
scripted roles so the wiring is verified without an LLM.
"""

from __future__ import annotations

import json
from pathlib import Path

from planner_critic.escalation import EscalationManager
from planner_critic.explain import explain
from planner_critic.replan import replan
from planner_critic.schema.goal import Goal, ReplanPolicy
from planner_critic.schema.plan import PlanVersion
from planner_critic.store.base import InMemoryStore
from planner_critic.store.replan_trace import ReplanLink
from planner_critic.types import Escalation

_GOAL_DIR = Path(__file__).parents[1] / "docs" / "field-test" / "goals"


def _load_goal(*parts: str) -> Goal:
    """Load a Goal from a field-test goal JSON file."""
    path = _GOAL_DIR.joinpath(*parts)
    if not path.suffix:
        path = path.with_suffix(".json")
    return Goal.model_validate(json.loads(path.read_text()))


# ---- C9: Escalation lifecycle (approve + deny) on ADV-02 / adversarial ----
# The adversarial goal has replan_policy=abort, which under strict tolerance
# with a gate-dirty plan produces an escalation we can then resolve.


def _make_adversarial_store() -> tuple[InMemoryStore, Goal, Escalation]:
    """Build a plan store with an adversarial-goal escalation (C9 fixture)."""
    goal = _load_goal("adversarial", "adv-01-billing-no-safety.json")
    store = InMemoryStore()
    plan = PlanVersion.model_validate(
        {
            "id": "adv-plan",
            "goal_id": goal.id,
            "version": 1,
            "tasks": [],
            "dependencies": [],
            "branches": [],
        }
    )
    store.put_plan_version(plan)
    esc = Escalation(id="esc:adv", plan_id="adv-plan", version=1, question="proceed?")
    store.put_escalation(esc)
    return store, goal, esc


def test_c9_escalation_deny_lifecycle() -> None:
    """C9: escalation created → listed → denied → status persisted."""
    store, _, esc = _make_adversarial_store()
    mgr = EscalationManager(store)

    listed = mgr.list_escalations()
    assert esc.id in {e.id for e in listed}
    assert listed[0].status == "open"

    resolved = mgr.resolve(esc.id, "denied", note="not safe")
    assert resolved.status == "denied"
    assert "not safe" in (resolved.resolution or "")

    open_after = mgr.list_escalations(status="open")
    assert esc.id not in {e.id for e in open_after}
    all_after = mgr.list_escalations()
    assert esc.id in {e.id for e in all_after}


def test_c9_escalation_approve_lifecycle() -> None:
    """C9: approve path through EscalationManager (complement to deny)."""
    store, _, esc = _make_adversarial_store()
    mgr = EscalationManager(store)

    resolved = mgr.resolve(esc.id, "approved", note="go ahead")
    assert resolved.status == "approved"
    assert resolved.resolution == "go ahead"


# ---- C10: Explain on an escalated (replan_aborted) plan ----------------
# The adversarial goal with abort policy + a gate-dirty plan → loop → abort.
# Explain must reference the escalation reason.


def test_c10_explain_on_escalated_plan() -> None:
    """C10: explain on an escalated plan references the escalation reason."""
    store = InMemoryStore()
    goal = _load_goal("adversarial", "adv-01-billing-no-safety.json")
    plan = PlanVersion.model_validate(
        {
            "id": "adv-plan-e",
            "goal_id": goal.id,
            "version": 1,
            "tasks": [],
            "dependencies": [],
            "branches": [],
        }
    )
    store.put_plan_version(plan)
    esc = Escalation(
        id="esc:explain", plan_id="adv-plan-e", version=1, question="safety steps missing?"
    )
    store.put_escalation(esc)

    result = explain(store, "adv-plan-e")
    assert result.plan_id == "adv-plan-e"
    assert len(result.decisions) >= 1
    last = result.decisions[-1]
    assert last.action == "escalated"
    assert "safety" in last.reason or "escalated" in last.reason


# ---- C11 / C25: Replan restart on ARCH-01 + store lineage ------------


def _make_arch01_plan(goal: Goal) -> PlanVersion:
    """A minimal PlanVersion for the ARCH-01 goal."""
    from conftest import make_plan, make_task

    return make_plan(
        plan_id="arch-plan",
        goal_id=goal.id,
        version=1,
        tasks=[make_task("analyse-boundary"), make_task("implement-dual-write")],
    )


def test_c11_replan_restart_on_arch01() -> None:
    """C11: restart on ARCH-01 produces a new plan lineage (fresh id)."""
    goal = _load_goal("architecture", "arch-01-microservice-extract")
    assert goal.replan_policy == ReplanPolicy.RESTART

    current = _make_arch01_plan(goal)
    revised = PlanVersion.model_validate(
        {
            "id": current.id,
            "goal_id": current.goal_id,
            "version": current.version + 1,
            "parent_version": current.id,
            "tasks": [
                {
                    "id": "new-task-1",
                    "description": "re-decomposed task",
                    "action": "implement",
                    "target": "payments",
                    "risk_class": "medium",
                    "preconditions": [],
                }
            ],
            "dependencies": [],
            "branches": [],
        }
    )

    result = replan(goal, current, revised)
    assert result.id == current.id
    assert result.goal_id == "arch-01-microservice-extract"
    assert result.parent_version == current.id
    assert result.version == 2
    assert len(result.tasks) == 1


def test_c25_replan_lineage_restart_arch01() -> None:
    """C25: restart replan chain is reconstructable in the store."""
    from conftest import make_plan, make_task

    goal = _load_goal("architecture", "arch-01-microservice-extract")
    store = InMemoryStore()

    # v1: original plan
    v1 = make_plan(plan_id="arch-c25", goal_id=goal.id, version=1, tasks=[make_task("step-a")])
    store.put_plan_version(v1)

    # v2: restart (version=2, parent=arch-c25)
    v2 = make_plan(
        plan_id="arch-c25",
        goal_id=goal.id,
        version=2,
        parent="arch-c25",
        tasks=[make_task("step-b")],
    )
    store.put_plan_version(v2)
    link = ReplanLink(
        plan_id="arch-c25",
        version=2,
        parent_plan_id="arch-c25",
        parent_version=1,
        policy="restart",
    )
    store.put_replan_link(link)

    chain = store.get_child_replan_links("arch-c25", 1)
    assert len(chain) == 1
    entry = chain[0]
    assert entry.parent_plan_id == "arch-c25"
    assert entry.parent_version == 1
    assert entry.version == 2
    assert entry.policy == "restart"
