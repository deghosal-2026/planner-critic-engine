"""Explain engine tests (F-80, CUJ 15): loop-decision narrative correctness.

The explain engine takes plan history + escalation data and produces a
human-readable narrative. These tests verify:
1. Empty history -> no-history narrative
2. Single revision approved -> approved with revision 1
3. Escalated (revision cap) -> cap description with revision count
4. Escalated (blocker) -> blocker reason code in narrative
5. Multi-revision history -> all decisions present
6. Actionability -> narrative alone reveals outcome-changing factor
"""

from __future__ import annotations

from conftest import make_plan, make_task
from planner_critic.explain import explain
from planner_critic.store.base import InMemoryStore
from planner_critic.types import Escalation, Finding, Severity


def _finding(
    task_id: str | None,
    reason_code: str,
    severity: Severity = Severity.BLOCKER,
    version: int = 1,
) -> Finding:
    return Finding(
        id=f"f:{task_id or 'plan'}:{reason_code}",
        task_id=task_id,
        version=version,
        severity=severity,
        reason_code=reason_code,  # type: ignore[arg-type]
        message=reason_code,
    )


def _seed_single_approved() -> InMemoryStore:
    """A plan with one revision and no blockers — approved."""
    store = InMemoryStore()
    plan = make_plan(plan_id="plan-1", version=1)
    store.put_plan_version(plan)
    store.put_findings("plan-1", 1, [])
    return store


def _seed_revision_cap_escalation() -> InMemoryStore:
    """A plan that hit the revision cap after 3 revisions."""
    store = InMemoryStore()
    plan1 = make_plan(plan_id="plan-1", version=1, tasks=[make_task("t1")])
    plan2 = make_plan(
        plan_id="plan-1",
        version=2,
        parent="plan-1",
        tasks=[make_task("t1"), make_task("t2")],
    )
    plan3 = make_plan(
        plan_id="plan-1",
        version=3,
        parent="plan-1",
        tasks=[make_task("t1"), make_task("t2"), make_task("t3")],
    )
    store.put_plan_version(plan1)
    store.put_plan_version(plan2)
    store.put_plan_version(plan3)

    blocker = _finding("t1", "missing_rollback", version=1)
    store.put_findings("plan-1", 1, [blocker])
    store.put_findings("plan-1", 2, [blocker])
    store.put_findings("plan-1", 3, [blocker])

    escalation = Escalation(
        id="esc:plan-1",
        plan_id="plan-1",
        version=3,
        question="Plan for goal-1 did not converge (revision_cap_reached). Decide next step.",
    )
    store.put_escalation(escalation)
    return store


def _seed_blocker_escalation() -> InMemoryStore:
    """A plan escalated because of a specific blocker (missing_verification)."""
    store = InMemoryStore()
    plan = make_plan(
        plan_id="plan-1",
        version=1,
        tasks=[make_task("t1")],
    )
    store.put_plan_version(plan)

    blocker = _finding("t1", "missing_verification", version=1)
    store.put_findings("plan-1", 1, [blocker])

    escalation = Escalation(
        id="esc:plan-1",
        plan_id="plan-1",
        version=1,
        blocker_finding_id=blocker.id,
        question="Goal 'goal-1' cannot be approved: blockers remain. Decide: patch, override, abandon.",  # noqa: E501
    )
    store.put_escalation(escalation)
    return store


def _seed_multi_revision_approved() -> InMemoryStore:
    """A plan that went through 2 revisions and was approved on the 2nd."""
    store = InMemoryStore()
    plan1 = make_plan(
        plan_id="plan-1",
        version=1,
        tasks=[make_task("t1")],
    )
    plan2 = make_plan(
        plan_id="plan-1",
        version=2,
        parent="plan-1",
        tasks=[make_task("t1"), make_task("t2")],
    )
    store.put_plan_version(plan1)
    store.put_plan_version(plan2)

    blocker = _finding("t1", "missing_rollback", version=1)
    store.put_findings("plan-1", 1, [blocker])
    store.put_findings("plan-1", 2, [])
    return store


# --- Tests -------------------------------------------------------------------


def test_empty_history() -> None:
    """Empty history returns 'no history found'."""
    store = InMemoryStore()
    result = explain(store, "ghost-plan")
    assert "no history" in result.summary.lower()
    assert "no recorded revision history" in result.narrative.lower()
    assert result.decisions == []


def test_single_revision_approved() -> None:
    """Single revision with no blockers -> approved on revision 1."""
    store = _seed_single_approved()
    result = explain(store, "plan-1")
    assert result.summary == "Approved on revision 1"
    assert result.decisions[0].action == "approved"
    assert result.decisions[0].version == 1
    assert "approved" in result.narrative.lower()


def test_escalated_revision_cap() -> None:
    """Escalated due to revision cap — narrative mentions the cap and count."""
    store = _seed_revision_cap_escalation()
    result = explain(store, "plan-1")
    assert result.summary.startswith("Escalated:")
    assert len(result.decisions) == 3
    assert result.decisions[-1].action == "escalated"
    assert "revision" in result.narrative.lower()
    assert "3" in result.narrative


def test_escalated_blocker() -> None:
    """Escalated with a blocker — narrative includes the reason code description."""
    store = _seed_blocker_escalation()
    result = explain(store, "plan-1")
    assert result.decisions[-1].action == "escalated"
    assert "missing_verification" in result.narrative
    assert "high-blast-radius" in result.narrative or "verification" in result.narrative


def test_multi_revision_history() -> None:
    """Multi-revision history contains all decisions in order."""
    store = _seed_multi_revision_approved()
    result = explain(store, "plan-1")
    assert len(result.decisions) == 2
    assert result.decisions[0].action == "revised"
    assert result.decisions[0].version == 1
    assert result.decisions[1].action == "approved"
    assert result.decisions[1].version == 2
    assert result.summary == "Approved on revision 2"


def test_actionability() -> None:
    """The narrative alone reveals the outcome-changing factor."""
    store = _seed_blocker_escalation()
    result = explain(store, "plan-1")
    assert "missing_verification" in result.narrative or "rollback" in result.narrative


def test_approved_with_blockers() -> None:
    """Approved with blockers — _approval_reason blocker path (line 110)."""
    store = InMemoryStore()
    plan = make_plan(plan_id="plan-1", version=1)
    store.put_plan_version(plan)
    blocker = _finding("t1", "missing_rollback", severity=Severity.BLOCKER, version=1)
    store.put_findings("plan-1", 1, [blocker])
    result = explain(store, "plan-1")
    assert "Approved with 1 unresolved" in result.decisions[0].reason
    assert sum(1 for f in result.decisions[0].key_findings) > 0


def test_revised_warnings_only() -> None:
    """Non-last revision with only warnings — _revision_reason warning path (lines 123-126)."""
    store = InMemoryStore()
    plan1 = make_plan(plan_id="plan-1", version=1, tasks=[make_task("t1")])
    plan2 = make_plan(
        plan_id="plan-1", version=2, parent="plan-1", tasks=[make_task("t1"), make_task("t2")]
    )
    store.put_plan_version(plan1)
    store.put_plan_version(plan2)
    warning = _finding("t1", "missing_rollback", severity=Severity.WARNING, version=1)
    store.put_findings("plan-1", 1, [warning])
    store.put_findings("plan-1", 2, [])
    result = explain(store, "plan-1")
    assert result.decisions[0].action == "revised"
    assert "warnings" in result.decisions[0].reason


def test_plan_level_finding() -> None:
    """Finding with no task_id — plan-level format (line 142)."""
    store = InMemoryStore()
    plan = make_plan(plan_id="plan-1", version=1)
    store.put_plan_version(plan)
    plan_finding = Finding(
        id="f:plan:dependency_cycle",
        task_id=None,
        version=1,
        severity=Severity.BLOCKER,
        reason_code="dependency_cycle",
        message="Dependency graph contains a cycle",
    )
    store.put_findings("plan-1", 1, [plan_finding])
    result = explain(store, "plan-1")
    assert any("Plan-level" in kf for kf in result.decisions[0].key_findings)


def test_build_summary_empty_decisions() -> None:
    """_build_summary with empty decisions — 'No loop decisions recorded' (line 149)."""
    from planner_critic.explain import _build_summary

    summary = _build_summary([], None)
    assert summary == "No loop decisions recorded"


def test_build_summary_in_progress() -> None:
    """_build_summary with 'revised' last action — in-progress path (line 155)."""
    from planner_critic.explain import ExplainDecision, _build_summary

    decisions = [
        ExplainDecision(
            version=1,
            action="revised",
            reason="revised for refinement",
            key_findings=[],
        ),
    ]
    summary = _build_summary(decisions, None)
    assert "In progress" in summary
    assert "revised on revision 1" in summary.lower()
