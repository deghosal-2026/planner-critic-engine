"""Escalation manager tests (F-30, F-34, DD-10): the human-in-the-loop gate.

Covers the :class:`EscalationManager`: a minimal, *precise* single question
per plan (one resolvable decision, DD-10), create/list/resolve lifecycle,
resolution recorded in the plan's history, and the patch-then-re-critique
flow so a resolved blocker never silently reaches an executor.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from conftest import EmptyCritic, finding, make_plan, make_task
from planner_critic.escalation import EscalationManager
from planner_critic.schema.plan import PlanVersion
from planner_critic.store.base import InMemoryStore
from planner_critic.types import Escalation, Finding, Severity


@pytest.fixture
def store() -> InMemoryStore:
    """A fresh in-memory store per test."""
    return InMemoryStore()


@pytest.fixture
def manager(store: InMemoryStore) -> EscalationManager:
    """An escalation manager over the in-memory store."""
    return EscalationManager(store)


def make_open_escalation(
    plan_id: str = "plan-1",
    version: int = 1,
    blocker: str | None = "f:blocker",
    question: str = "Can the plan proceed despite the missing verification?",
) -> Escalation:
    """Build an escalation that passes the manager's precision contract."""
    return Escalation(
        id=f"esc:{plan_id}:{version}",
        plan_id=plan_id,
        version=version,
        blocker_finding_id=blocker,
        question=question,
    )


class TestCreate:
    """create() persists a precise, single-question escalation."""

    def test_create_persists_open_escalation(
        self, store: InMemoryStore, manager: EscalationManager
    ) -> None:
        """A valid escalation is stored and retrievable by plan id."""
        store.put_plan_version(make_plan(plan_id="plan-1", version=1))
        esc = make_open_escalation()
        saved = manager.create(esc)
        assert saved.status == "open"
        stored = store.get_escalation("plan-1")
        assert stored is not None
        assert stored.id == esc.id
        assert stored.question == esc.question

    def test_create_validates_plan_exists(self, manager: EscalationManager) -> None:
        """Fail-closed: cannot escalate a plan the store has never seen."""
        esc = make_open_escalation()
        with pytest.raises(ValueError, match="unknown plan"):
            manager.create(esc)

    def test_create_validates_revision_exists(
        self, store: InMemoryStore, manager: EscalationManager
    ) -> None:
        """The escalation must point at a real revision of the plan."""
        store.put_plan_version(make_plan(plan_id="plan-1", version=2))
        esc = make_open_escalation(version=99)
        with pytest.raises(ValueError, match="revision"):
            manager.create(esc)

    def test_create_rejects_blank_question(
        self, store: InMemoryStore, manager: EscalationManager
    ) -> None:
        """A blank question is not a resolvable decision (DD-10)."""
        store.put_plan_version(make_plan(plan_id="plan-1", version=1))
        esc = make_open_escalation(question="   ")
        with pytest.raises(ValueError, match="question"):
            manager.create(esc)

    def test_create_rejects_second_open_escalation_same_plan(
        self, store: InMemoryStore, manager: EscalationManager
    ) -> None:
        """One precise question per plan — a second open one is refused."""
        store.put_plan_version(make_plan(plan_id="plan-1", version=1))
        manager.create(make_open_escalation(question="First question?"))
        with pytest.raises(ValueError, match="open escalation"):
            manager.create(make_open_escalation(question="Second question?"))


class TestList:
    """list() returns escalations, optionally filtered by status."""

    def test_list_returns_all(self, store: InMemoryStore, manager: EscalationManager) -> None:
        """Both escalations across plans are listed."""
        store.put_plan_version(make_plan(plan_id="plan-1", version=1))
        store.put_plan_version(make_plan(plan_id="plan-2", version=1))
        manager.create(make_open_escalation(plan_id="plan-1"))
        manager.create(make_open_escalation(plan_id="plan-2"))
        assert {e.plan_id for e in manager.list_escalations()} == {"plan-1", "plan-2"}

    def test_list_filters_by_status(self, store: InMemoryStore, manager: EscalationManager) -> None:
        """Status filtering only surfaces matching escalations."""
        store.put_plan_version(make_plan(plan_id="plan-1", version=1))
        store.put_plan_version(make_plan(plan_id="plan-2", version=1))
        manager.create(make_open_escalation(plan_id="plan-1"))
        esc2 = make_open_escalation(plan_id="plan-2")
        manager.create(esc2)
        manager.resolve(esc2.id, "denied", note="rejected by reviewer")

        assert [e.plan_id for e in manager.list_escalations(status="open")] == ["plan-1"]
        assert [e.plan_id for e in manager.list_escalations(status="denied")] == ["plan-2"]

    def test_list_empty_store(self, manager: EscalationManager) -> None:
        """An empty store lists nothing."""
        assert manager.list_escalations() == []


class TestResolve:
    """resolve() records the decision; resolution lands in plan history."""

    def test_resolve_approved_records_resolution(
        self, store: InMemoryStore, manager: EscalationManager
    ) -> None:
        """Approval persists status, note, and a resolved_at timestamp."""
        store.put_plan_version(make_plan(plan_id="plan-1", version=1))
        esc = manager.create(make_open_escalation())
        resolved = manager.resolve(esc.id, "approved", note="human says go")
        assert resolved.status == "approved"
        assert resolved.resolution == "human says go"
        assert resolved.resolved_at is not None

        persisted = store.get_escalation("plan-1")
        assert persisted is not None
        assert persisted.status == "approved"
        assert persisted.resolution == "human says go"

    def test_resolve_denied(self, store: InMemoryStore, manager: EscalationManager) -> None:
        """Denial records a distinct status and timestamps resolution."""
        store.put_plan_version(make_plan(plan_id="plan-1", version=1))
        esc = manager.create(make_open_escalation())
        resolved = manager.resolve(esc.id, "denied", note="no")
        assert resolved.status == "denied"
        assert resolved.resolution == "no"
        assert resolved.resolved_at is not None

    def test_resolve_unknown_id(self, manager: EscalationManager) -> None:
        """Resolving an escalation that does not exist fails loudly."""
        with pytest.raises(ValueError, match="unknown escalation"):
            manager.resolve("esc:missing", "approved")

    def test_resolve_twice_raises(self, store: InMemoryStore, manager: EscalationManager) -> None:
        """A closed escalation cannot be resolved again."""
        store.put_plan_version(make_plan(plan_id="plan-1", version=1))
        esc = manager.create(make_open_escalation())
        manager.resolve(esc.id, "approved")
        with pytest.raises(ValueError, match="already resolved"):
            manager.resolve(esc.id, "approved")


class TestPatchAndRecritique:
    """A direct plan patch is stored as a new revision and re-critiqued."""

    def test_patch_persists_new_revision_and_recritiques(
        self, store: InMemoryStore, manager: EscalationManager
    ) -> None:
        """Patching writes version+1, re-runs gates + critic, stores findings."""
        plan = make_plan(plan_id="plan-1", version=1)
        store.put_plan_version(plan)

        patched = make_plan(
            plan_id="plan-1",
            version=2,
            parent="plan-1",
            tasks=[make_task("t1", verification={"what": "w", "how": "h", "expected": "e"})],
        )

        manager.create(make_open_escalation())
        manager.patch_and_recritique("plan-1", patched, critic=EmptyCritic())

        stored = store.get_plan("plan-1", version=2)
        assert stored is not None
        assert stored.version == 2
        assert stored.parent_version == "plan-1"
        latest = store.get_plan("plan-1")
        assert latest is not None
        assert latest.version == 2
        assert store._findings[("plan-1", 2)] is not None

    def test_patch_requires_clean_findings(
        self, store: InMemoryStore, manager: EscalationManager
    ) -> None:
        """A patch that still trips a deterministic gate is refused fail-closed."""
        blocker = finding("t1", "missing_rollback", severity=Severity.BLOCKER)

        class BlockingCritic(EmptyCritic):
            """Critic that keeps flagging the missing rollback."""

            def audit(self, plan: PlanVersion, findings: list[Finding]) -> list[Finding]:
                return [*list(findings), blocker]

        plan = make_plan(plan_id="plan-1", version=1)
        store.put_plan_version(plan)

        patched = make_plan(
            plan_id="plan-1",
            version=2,
            parent="plan-1",
            tasks=[make_task("t1", risk_class="critical", rollback=None)],
        )
        manager.create(make_open_escalation())
        with pytest.raises(ValueError, match="not clean"):
            manager.patch_and_recritique("plan-1", patched, critic=BlockingCritic())


def test_resolved_at_is_utc(store: InMemoryStore, manager: EscalationManager) -> None:
    """resolution timestamps are timezone-aware UTC."""
    store.put_plan_version(make_plan(plan_id="plan-1", version=1))
    esc = manager.create(make_open_escalation())
    resolved = manager.resolve(esc.id, "approved")
    assert resolved.resolved_at is not None
    assert resolved.resolved_at.tzinfo is UTC
    assert resolved.resolved_at <= datetime.now(UTC)
