"""End-to-end M4 integration test (issue #39).

Full arc: escalate → human patches → re-critique → approve → execute → failure
→ tag → missed-critique. Hermetic: fake providers only, zero network.
"""

from __future__ import annotations

import pytest

from conftest import (
    EmptyCritic,
    ScriptedPlanner,
    make_goal,
    make_plan,
    make_task,
)
from planner_critic.approval import ApprovalGate, resolve_threshold
from planner_critic.engine import Engine
from planner_critic.escalation import EscalationManager
from planner_critic.execution import ExecutionRecorder
from planner_critic.forensics import analyze_failure
from planner_critic.loop import LoopConfig
from planner_critic.replan import replan
from planner_critic.schema.goal import ReplanPolicy, RiskTolerance
from planner_critic.store.base import InMemoryStore
from planner_critic.types import Finding, Severity


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


def test_full_m4_arc(store: InMemoryStore) -> None:
    """The complete escalate → patch → execute → forensics arc."""

    # 1. Plan a goal with a blocker that never converges → escalation.
    planner = ScriptedPlanner(
        [make_plan(tasks=[make_task("t1", risk_class="critical", rollback=None)])]
    )
    engine = Engine(planner=planner, critic=EmptyCritic(), config=LoopConfig(revision_cap=1))
    result = engine.plan(make_goal())
    assert result.status == "escalated"
    assert result.escalation is not None

    # Persist the plan + escalation in the store.
    assert result.plan is not None
    store.put_plan_version(result.plan)
    store.put_findings(result.plan.id, result.plan.version, result.findings)
    manager = EscalationManager(store)
    saved_esc = manager.create(result.escalation)
    assert saved_esc.status == "open"

    # 2. Human patches the plan (adds rollback) and approves.
    patched = make_plan(
        plan_id=result.plan.id,
        version=2,
        parent=result.plan.id,
        tasks=[
            make_task(
                "t1",
                risk_class="critical",
                verification={"what": "w", "how": "h", "expected": "e"},
                rollback={"trigger": "fail", "action": "undo", "safety_guard": "ok"},
            )
        ],
    )
    findings = manager.patch_and_recritique(result.plan.id, patched, critic=EmptyCritic())
    assert not any(f.severity is Severity.BLOCKER for f in findings)

    resolved = manager.resolve(saved_esc.id, "approved", note="human patched the rollback")
    assert resolved.status == "approved"

    # 3. Approve the patched plan.
    _, outcome = resolve_threshold(findings, RiskTolerance.BALANCED)
    gate = ApprovalGate(RiskTolerance.BALANCED)
    approved = gate.approve(patched, outcome)

    # 4. Execute: the task fails (planning failure — a missed critique).
    recorder = ExecutionRecorder(store)
    missed_finding = Finding(
        id="f:missed:risk",
        task_id="t1",
        version=2,
        severity=Severity.WARNING,
        reason_code="llm_weak_rollback",
        message="rollback was insufficient",
    )
    trace = recorder.record(approved, task_id="t1", outcome="failed", linked_finding=missed_finding)
    assert trace.failure_class == "planning"

    # 5. Forensics: analyze the missed critique and suggest a deterministic check.
    record = analyze_failure(trace, missed_finding)
    assert record.suggested_gate == "missing_rollback"
    record.persist(store)

    loaded = type(record).load(store, "plan-1")
    assert loaded is not None
    assert loaded.task_id == "t1"

    # 6. Replan with PATCH policy → next revision stamped.
    goal = make_goal(replan_policy=ReplanPolicy.PATCH)
    revised = make_plan(
        plan_id=result.plan.id,
        version=3,
        parent=result.plan.id,
        tasks=[
            make_task(
                "t1",
                risk_class="critical",
                rollback={"trigger": "f", "action": "u", "safety_guard": "s"},
            )
        ],
    )
    new_revision = replan(goal, patched, revised)
    assert new_revision.version == 3
    assert new_revision.parent_version == patched.id

    # 7. Verify lineage is reconstructable.
    versions = [p.version for p in store.list_plans() if p.id == result.plan.id]
    assert 1 in versions
    assert 2 in versions


def test_replan_abort_stops_planning(store: InMemoryStore) -> None:
    """The abort policy halts immediately — no plan revision is created."""
    plan = make_plan(plan_id="plan-1", version=1)
    goal = make_goal(replan_policy=ReplanPolicy.ABORT)
    from planner_critic.replan import ReplanAbort

    with pytest.raises(ReplanAbort):
        replan(goal, plan, make_plan())
