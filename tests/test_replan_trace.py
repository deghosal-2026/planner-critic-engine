"""Replan trace tests (F-53): sub-plan linkage + partial execution preservation.

Every replan (patch or restart) records a :class:`ReplanLink` that binds the
new revision to its parent, preserving the type and any partial execution
state. The store methods ``put_replan_link`` / ``get_replan_link`` /
``get_child_replan_links`` let the full lineage be reconstructed:
original → partial → replan → completion.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import make_plan
from planner_critic.store.base import InMemoryStore
from planner_critic.store.replan_trace import ReplanLink
from planner_critic.store.sqlite import SQLiteStore

# --- In-memory store tests --------------------------------------------------


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


def test_put_and_get_replan_link(store: InMemoryStore) -> None:
    """A replan link round-trips through the store."""
    store.put_plan_version(make_plan(plan_id="plan-1", version=1))
    store.put_plan_version(make_plan(plan_id="plan-1", version=2, parent="plan-1"))

    link = ReplanLink(
        plan_id="plan-1",
        version=2,
        parent_plan_id="plan-1",
        parent_version=1,
        policy="patch",
    )
    store.put_replan_link(link)
    got = store.get_replan_link("plan-1", 2)
    assert got is not None
    assert got.policy == "patch"
    assert got.parent_version == 1


def test_get_replan_link_returns_none_for_unknown(store: InMemoryStore) -> None:
    """An unlinked revision returns None."""
    assert store.get_replan_link("plan-1", 99) is None


def test_get_child_replan_links(store: InMemoryStore) -> None:
    """A parent can have multiple children (cascading replans)."""
    store.put_plan_version(make_plan(plan_id="plan-1", version=1))
    for v in (2, 3):
        store.put_plan_version(make_plan(plan_id="plan-1", version=v, parent="plan-1"))
        store.put_replan_link(
            ReplanLink(
                plan_id="plan-1",
                version=v,
                parent_plan_id="plan-1",
                parent_version=1,
                policy="patch",
            )
        )

    children = store.get_child_replan_links("plan-1", 1)
    assert len(children) == 2
    assert [c.version for c in children] == [2, 3]


def test_replan_link_with_partial_execution(store: InMemoryStore) -> None:
    """Partial execution state is preserved in the link."""
    store.put_plan_version(make_plan(plan_id="plan-1", version=1))
    store.put_plan_version(make_plan(plan_id="plan-1", version=2, parent="plan-1"))

    link = ReplanLink(
        plan_id="plan-1",
        version=2,
        parent_plan_id="plan-1",
        parent_version=1,
        policy="patch",
        partial_execution='{"completed": ["t1"], "failed": ["t2"]}',
    )
    store.put_replan_link(link)
    got = store.get_replan_link("plan-1", 2)
    assert got is not None
    assert got.partial_execution == '{"completed": ["t1"], "failed": ["t2"]}'


def test_full_lineage_reconstructable(store: InMemoryStore) -> None:
    """Walk the replan chain: original → partial → replan → completion."""
    store.put_plan_version(make_plan(plan_id="plan-1", version=1))  # original
    store.put_plan_version(make_plan(plan_id="plan-1", version=2, parent="plan-1"))  # partial fail
    store.put_plan_version(make_plan(plan_id="plan-1", version=3, parent="plan-1"))  # replan
    store.put_plan_version(make_plan(plan_id="plan-1", version=4, parent="plan-1"))  # completion

    store.put_replan_link(
        ReplanLink(
            plan_id="plan-1",
            version=2,
            parent_plan_id="plan-1",
            parent_version=1,
            policy="patch",
        )
    )
    store.put_replan_link(
        ReplanLink(
            plan_id="plan-1",
            version=3,
            parent_plan_id="plan-1",
            parent_version=1,
            policy="patch",
        )
    )

    root = store.get_plan("plan-1", 1)
    assert root is not None and root.version == 1

    failed = store.get_plan("plan-1", 2)
    assert failed is not None
    assert store.get_replan_link("plan-1", 2) is not None

    replanned = store.get_plan("plan-1", 3)
    assert replanned is not None
    assert store.get_replan_link("plan-1", 3) is not None

    children = store.get_child_replan_links("plan-1", 1)
    assert len(children) == 2
    assert children[0].parent_version == 1
    assert children[1].parent_version == 1


# --- SQLite store tests -----------------------------------------------------


@pytest.fixture
def sqlite_store(tmp_path: Path) -> SQLiteStore:
    return SQLiteStore(tmp_path / "store.db")


def test_sqlite_replan_link_round_trip(sqlite_store: SQLiteStore) -> None:
    """SQLite persists and returns replan links."""
    sqlite_store.put_plan_version(make_plan(plan_id="plan-1", version=1))
    sqlite_store.put_plan_version(make_plan(plan_id="plan-1", version=2, parent="plan-1"))

    link = ReplanLink(
        plan_id="plan-1",
        version=2,
        parent_plan_id="plan-1",
        parent_version=1,
        policy="restart",
    )
    sqlite_store.put_replan_link(link)
    got = sqlite_store.get_replan_link("plan-1", 2)
    assert got is not None
    assert got.policy == "restart"

    children = sqlite_store.get_child_replan_links("plan-1", 1)
    assert len(children) == 1
    assert children[0].version == 2


def test_sqlite_replan_link_persists_across_reopen(tmp_path: Path) -> None:
    """Replan link data survives store close + reopen."""
    path = tmp_path / "store.db"
    store = SQLiteStore(path)
    store.put_plan_version(make_plan(plan_id="plan-1", version=1))
    store.put_plan_version(make_plan(plan_id="plan-1", version=2, parent="plan-1"))
    store.put_replan_link(
        ReplanLink(
            plan_id="plan-1",
            version=2,
            parent_plan_id="plan-1",
            parent_version=1,
            policy="patch",
        )
    )
    store.close()

    reopened = SQLiteStore(path)
    got = reopened.get_replan_link("plan-1", 2)
    reopened.close()
    assert got is not None
    assert got.parent_version == 1
