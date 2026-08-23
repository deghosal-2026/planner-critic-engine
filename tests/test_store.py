"""Store protocol tests (F-09): the in-memory store and the side-channel.

Covers the PlanStore ABC contract against :class:`InMemoryStore`: versioned
plan CRUD, latest-revision resolution, structural diff, escalation and
execution-trace persistence, and approved-plan↔trace linking. The
side-channel contract (store down → warn + continue in memory) is asserted by
checking ``warn_and_continue`` logs and that a store implementation can be
swapped without changing the protocol.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import pytest

from conftest import hard_dep, make_plan, make_task
from planner_critic.store.base import InMemoryStore, PlanDiff, PlanStore, StoreUnavailable
from planner_critic.store.replan_trace import ReplanLink
from planner_critic.store.sqlite import SQLiteStore
from planner_critic.store.versions import (
    SCHEMA_VERSION,
    apply_migrations,
    current_schema_version,
    revert_migrations,
)
from planner_critic.types import Escalation, ExecutionTrace, Finding, Severity


@pytest.fixture
def store() -> InMemoryStore:
    """A fresh in-memory store per test."""
    return InMemoryStore()


def test_put_and_get_plan_round_trip(store: InMemoryStore) -> None:
    """A stored revision comes back losslessly."""
    plan = make_plan(plan_id="plan-1", version=1)
    store.put_plan_version(plan)
    assert store.get_plan("plan-1", version=1) == plan


def test_get_latest_version_when_version_omitted(store: InMemoryStore) -> None:
    """get_plan without a version returns the newest stored revision."""
    store.put_plan_version(make_plan(plan_id="plan-1", version=1))
    store.put_plan_version(make_plan(plan_id="plan-1", version=2, parent="plan-1"))
    latest = store.get_plan("plan-1")
    assert latest is not None
    assert latest.version == 2


def test_get_plan_returns_none_for_unknown(store: InMemoryStore) -> None:
    """An unknown plan id returns None, not an exception."""
    assert store.get_plan("nope") is None
    assert store.get_plan("nope", version=3) is None


def test_list_plans_newest_first(store: InMemoryStore) -> None:
    """list_plans orders newest-first and filters by goal."""
    store.put_plan_version(make_plan(plan_id="plan-a", version=1, goal_id="goal-1"))
    store.put_plan_version(make_plan(plan_id="plan-a", version=2, goal_id="goal-1"))
    store.put_plan_version(make_plan(plan_id="plan-b", version=1, goal_id="goal-2"))

    assert [p.version for p in store.list_plans(goal_id="goal-1")] == [2, 1]
    assert [p.version for p in store.list_plans(goal_id="goal-2")] == [1]
    assert len(store.list_plans()) == 3


def test_list_plans_ordering_matches_across_implementations() -> None:
    """In-memory and SQLite agree on (plan_id asc, version desc) ordering."""
    in_mem = InMemoryStore()
    sqlite = SQLiteStore(":memory:")
    for store in (in_mem, sqlite):
        store.put_plan_version(make_plan(plan_id="b", version=1))
        store.put_plan_version(make_plan(plan_id="a", version=2))
        store.put_plan_version(make_plan(plan_id="a", version=1))

    expected = [("a", 2), ("a", 1), ("b", 1)]
    assert [(p.id, p.version) for p in in_mem.list_plans()] == expected
    assert [(p.id, p.version) for p in sqlite.list_plans()] == expected


def test_diff_detects_added_removed_changed(store: InMemoryStore) -> None:
    """diff surfaces added/removed/changed tasks and dependency edges."""
    v1 = make_plan(
        plan_id="plan-1",
        version=1,
        tasks=[make_task("t1"), make_task("t2")],
        dependencies=[hard_dep("t1", "t2")],
    )
    v2 = make_plan(
        plan_id="plan-1",
        version=2,
        parent="plan-1",
        tasks=[
            make_task("t1"),
            make_task("t2", verification={"what": "x", "how": "y", "expected": "z"}),
            make_task("t3"),
        ],
        dependencies=[hard_dep("t1", "t2"), hard_dep("t2", "t3")],
    )
    store.put_plan_version(v1)
    store.put_plan_version(v2)

    diff = store.diff("plan-1", 1, 2)
    assert isinstance(diff, PlanDiff)
    assert diff.added_task_ids == ["t3"]
    assert diff.removed_task_ids == []
    assert diff.changed_task_ids == ["t2"]
    assert [d.to_task for d in diff.added_dependencies] == ["t3"]
    assert diff.removed_dependencies == []


def test_diff_unknown_plan_returns_none(store: InMemoryStore) -> None:
    """diff against an unknown plan or revision returns None."""
    assert store.diff("ghost", 1, 2) is None
    store.put_plan_version(make_plan(plan_id="plan-1", version=1))
    assert store.diff("plan-1", 1, 9) is None


def test_diff_identical_revisions_is_empty(store: InMemoryStore) -> None:
    """Structurally identical revisions produce an empty diff."""
    plan = make_plan(plan_id="plan-1", version=1)
    store.put_plan_version(plan)
    store.put_plan_version(plan.model_copy(update={"version": 2}))
    diff = store.diff("plan-1", 1, 2)
    assert diff is not None
    assert diff.is_empty


def test_escalation_put_and_get(store: InMemoryStore) -> None:
    """Escalations persist and are retrievable by plan id."""
    esc = Escalation(id="esc-1", plan_id="plan-1", version=2, question="proceed?")
    store.put_escalation(esc)
    assert store.get_escalation("plan-1") == esc
    assert store.get_escalation("other") is None


def test_execution_trace_put_and_get_in_order(store: InMemoryStore) -> None:
    """Execution steps persist in insertion order."""
    t1 = ExecutionTrace(id="tr-1", plan_id="plan-1", task_id="t1", outcome="ok")
    t2 = ExecutionTrace(id="tr-2", plan_id="plan-1", task_id="t2", outcome="failed")
    store.put_execution_trace(t1)
    store.put_execution_trace(t2)
    assert store.get_execution_traces("plan-1") == [t1, t2]
    assert store.get_execution_traces("nope") == []


def test_link_approved_plan_to_trace(store: InMemoryStore) -> None:
    """link records an approved-revision↔trace association for forensics."""
    store.put_plan_version(make_plan(plan_id="plan-1", version=2))
    store.link("plan-1", 2, "tr-9")
    assert store._links == {("plan-1", 2, "tr-9")}


def test_put_findings_round_trip(store: InMemoryStore) -> None:
    """Findings persist under their (plan_id, version) key."""
    finding = Finding(
        id="f1",
        task_id="t1",
        version=1,
        severity=Severity.BLOCKER,
        reason_code="plan_schema_invalid",
        message="boom",
    )
    store.put_findings("plan-1", 1, [finding])
    assert store._findings[("plan-1", 1)] == [finding]


def test_warn_and_continue_logs_side_channel(caplog: pytest.LogCaptureFixture) -> None:
    """The side-channel contract emits a warning, never a crash."""
    store = InMemoryStore()
    with caplog.at_level(logging.WARNING):
        store.warn_and_continue(RuntimeError("disk full"))
    assert any("continuing in memory" in r.message for r in caplog.records)


def test_store_unavailable_is_catchable() -> None:
    """StoreUnavailable is the fail-closed signal for side-channel fallback."""
    with pytest.raises(StoreUnavailable):
        raise StoreUnavailable()


# --- SQLite store -----------------------------------------------------------


@pytest.fixture
def sqlite_store(tmp_path: Path) -> SQLiteStore:
    """A SQLite store on a temp-file database."""
    return SQLiteStore(tmp_path / "store.db")


def test_sqlite_plan_round_trip(sqlite_store: SQLiteStore) -> None:
    """A plan stored then re-read from SQLite is lossless."""
    plan = make_plan(plan_id="plan-1", version=2, parent="plan-1")
    sqlite_store.put_plan_version(plan)
    assert sqlite_store.get_plan("plan-1", version=2) == plan
    assert sqlite_store.get_plan("plan-1") == plan


def test_sqlite_latest_and_listing(sqlite_store: SQLiteStore) -> None:
    """Latest-version lookup and per-goal listing match the protocol."""
    sqlite_store.put_plan_version(make_plan(plan_id="plan-a", version=1, goal_id="g1"))
    sqlite_store.put_plan_version(make_plan(plan_id="plan-a", version=2, goal_id="g1"))
    sqlite_store.put_plan_version(make_plan(plan_id="plan-b", version=1, goal_id="g2"))

    latest = sqlite_store.get_plan("plan-a")
    assert latest is not None
    assert latest.version == 2
    assert [p.version for p in sqlite_store.list_plans(goal_id="g1")] == [2, 1]
    assert [p.version for p in sqlite_store.list_plans(goal_id="g2")] == [1]
    assert len(sqlite_store.list_plans()) == 3


def test_sqlite_diff(sqlite_store: SQLiteStore) -> None:
    """Structural diff works against SQLite-stored revisions."""
    v1 = make_plan(
        plan_id="plan-1",
        version=1,
        tasks=[make_task("t1"), make_task("t2")],
        dependencies=[hard_dep("t1", "t2")],
    )
    v2 = make_plan(
        plan_id="plan-1",
        version=2,
        parent="plan-1",
        tasks=[make_task("t1"), make_task("t2"), make_task("t3")],
        dependencies=[hard_dep("t1", "t2"), hard_dep("t2", "t3")],
    )
    sqlite_store.put_plan_version(v1)
    sqlite_store.put_plan_version(v2)

    diff = sqlite_store.diff("plan-1", 1, 2)
    assert isinstance(diff, PlanDiff)
    assert diff.added_task_ids == ["t3"]
    assert sqlite_store.diff("plan-1", 1, 9) is None


def test_sqlite_escalation_and_traces(sqlite_store: SQLiteStore) -> None:
    """Escalation and execution traces persist through SQLite."""
    esc = Escalation(id="esc-1", plan_id="plan-1", version=1, question="ok?")
    sqlite_store.put_escalation(esc)
    assert sqlite_store.get_escalation("plan-1") == esc

    sqlite_store.put_execution_trace(
        ExecutionTrace(id="tr-1", plan_id="plan-1", task_id="t1", outcome="ok")
    )
    sqlite_store.put_execution_trace(
        ExecutionTrace(id="tr-2", plan_id="plan-1", task_id="t2", outcome="failed")
    )
    traces = sqlite_store.get_execution_traces("plan-1")
    assert [t.id for t in traces] == ["tr-1", "tr-2"]


def test_sqlite_link(sqlite_store: SQLiteStore) -> None:
    """Approved-plan↔trace links persist."""
    sqlite_store.put_plan_version(make_plan(plan_id="plan-1", version=2))
    sqlite_store.link("plan-1", 2, "tr-9")
    row = sqlite_store._fetchone(
        "SELECT 1 FROM links WHERE plan_id = ? AND version = ? AND trace_id = ?",
        ("plan-1", 2, "tr-9"),
    )
    assert row is not None


def test_sqlite_persists_across_reopen(tmp_path: Path) -> None:
    """Data survives closing and reopening the database file."""
    path = tmp_path / "store.db"
    store = SQLiteStore(path)
    store.put_plan_version(make_plan(plan_id="plan-1", version=1))
    store.put_findings("plan-1", 1, [])
    store.put_escalation(Escalation(id="esc-1", plan_id="plan-1", version=1, question="q"))
    store.put_execution_trace(
        ExecutionTrace(id="tr-1", plan_id="plan-1", task_id="t1", outcome="ok")
    )
    store.close()

    reopened = SQLiteStore(path)
    assert reopened.get_plan("plan-1") == make_plan(plan_id="plan-1", version=1)
    assert reopened.get_escalation("plan-1") is not None
    assert len(reopened.get_execution_traces("plan-1")) == 1


def test_sqlite_unavailable_on_bad_path() -> None:
    """An unopenable database surfaces StoreUnavailable (side-channel)."""
    with pytest.raises(StoreUnavailable):
        SQLiteStore("/nonexistent-dir/store.db")


# --- Cross-implementation protocol conformance ------------------------------


PROTOCOL_STORES = [InMemoryStore, lambda: SQLiteStore(":memory:")]


@pytest.mark.parametrize("factory", PROTOCOL_STORES, ids=["in-memory", "sqlite"])
def test_protocol_conformance_latest_and_diff(factory: Callable[[], PlanStore]) -> None:
    """Every PlanStore implementation honors the same protocol surface."""
    store = factory()
    store.put_plan_version(make_plan(plan_id="p", version=1, tasks=[make_task("t1")]))
    store.put_plan_version(
        make_plan(
            plan_id="p",
            version=2,
            parent="p",
            tasks=[make_task("t1"), make_task("t2")],
        )
    )
    latest = store.get_plan("p")
    assert latest is not None
    assert latest.version == 2
    diff = store.diff("p", 1, 2)
    assert isinstance(diff, PlanDiff)
    assert diff.added_task_ids == ["t2"]

    esc = Escalation(id="e", plan_id="p", version=2, question="ok?")
    store.put_escalation(esc)
    assert store.get_escalation("p") == esc
    store.put_execution_trace(ExecutionTrace(id="t", plan_id="p", task_id="t1", outcome="ok"))
    assert len(store.get_execution_traces("p")) == 1
    store.link("p", 2, "t")
    if isinstance(store, InMemoryStore):
        assert store._links == {("p", 2, "t")}
    elif isinstance(store, SQLiteStore):
        assert store._fetchone("SELECT 1 FROM links LIMIT 1") is not None

    # replan link conformance
    store.put_replan_link(
        ReplanLink(plan_id="p", version=2, parent_plan_id="p", parent_version=1, policy="patch")
    )
    assert store.get_replan_link("p", 2) is not None
    children = store.get_child_replan_links("p", 1)
    assert len(children) == 1
    assert children[0].version == 2


# --- Schema versioning + migrate (F-27) -------------------------------------


def test_fresh_db_is_migrated_to_latest(tmp_path: Path) -> None:
    """Opening a store migrates a fresh DB to the latest schema version."""
    store = SQLiteStore(tmp_path / "store.db")
    assert current_schema_version(store._conn) == SCHEMA_VERSION
    store.close()


def test_reopen_is_idempotent(tmp_path: Path) -> None:
    """Reopening an already-migrated DB applies nothing new."""
    path = tmp_path / "store.db"
    first = SQLiteStore(path)
    first.close()
    second = SQLiteStore(path)
    assert current_schema_version(second._conn) == SCHEMA_VERSION
    second.close()


def test_revert_then_remigrate(tmp_path: Path) -> None:
    """Reversible: revert drops the ledger, remigrate restores it."""

    path = tmp_path / "store.db"
    store = SQLiteStore(path)
    conn = store._conn

    reverted = revert_migrations(conn, 0)
    assert reverted == 0
    assert current_schema_version(conn) == 0
    # tables are gone after full revert
    tables = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    assert "plan_versions" not in tables

    remigrated = apply_migrations(conn)
    assert remigrated == SCHEMA_VERSION
    store.close()


def test_revert_to_zero_is_destructive_and_remigrate_restores_schema(tmp_path: Path) -> None:
    """Reverting to v0 drops data (documented down); remigrate restores schema."""
    path = tmp_path / "store.db"
    store = SQLiteStore(path)
    plan = make_plan(plan_id="plan-1", version=1)
    store.put_plan_version(plan)
    conn = store._conn

    revert_migrations(conn, 0)
    with pytest.raises(StoreUnavailable):
        store.get_plan("plan-1")  # table is gone → side-channel signal

    apply_migrations(conn)
    assert store.get_plan("plan-1") is None  # schema back, data intentionally gone
    store.close()


def test_migrate_up_preserves_old_data(tmp_path: Path) -> None:
    """Migrating up keeps previously stored data readable (F-27, PRD 08)."""
    path = tmp_path / "store.db"
    store = SQLiteStore(path)
    plan = make_plan(plan_id="plan-1", version=1)
    store.put_plan_version(plan)
    conn = store._conn
    assert current_schema_version(conn) == SCHEMA_VERSION

    apply_migrations(conn)  # idempotent no-op at latest
    assert store.get_plan("plan-1") == plan
    store.close()


def test_apply_migrations_refuses_target_below_current(tmp_path: Path) -> None:
    """Migrating up to a version below the current one is refused."""
    import pytest as pt

    store = SQLiteStore(tmp_path / "store.db")
    with pt.raises(StoreUnavailable):
        apply_migrations(store._conn, 0)
    store.close()


def test_migrate_cli_up_and_revert(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``plancritic migrate`` prints schema version and reverts on demand."""
    from planner_critic.cli.migrate import run_migrate

    db = tmp_path / "plans.db"
    assert run_migrate(["--path", str(db)]) == 0
    out = capsys.readouterr().out
    assert f"schema at v{SCHEMA_VERSION}" in out

    assert run_migrate(["--path", str(db), "--revert"]) == 0
    out = capsys.readouterr().out
    assert "reverted to schema v0" in out


def test_migrate_cli_failure_returns_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A bad store path fails the command without a traceback."""
    from planner_critic.cli.migrate import run_migrate

    assert run_migrate(["--path", str(tmp_path / "no" / "dir" / "db.db")]) == 1
    assert "migrate failed" in capsys.readouterr().out


def test_revert_target_above_current_is_refused(tmp_path: Path) -> None:
    """Reverting to a version above current is refused (StoreUnavailable)."""
    store = SQLiteStore(tmp_path / "store.db")
    with pytest.raises(StoreUnavailable):
        revert_migrations(store._conn, SCHEMA_VERSION + 1)
    store.close()


def test_apply_migration_failure_raises_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing migration surfaces StoreUnavailable and rolls back."""

    from planner_critic.store import versions as versions_mod
    from planner_critic.store.versions import Migration

    bad = Migration(
        version=SCHEMA_VERSION + 1,
        name="bad",
        up="CREATE TABLE nope_bad (); THIS IS NOT SQL",
        down="DROP TABLE nope_bad",
    )
    monkeypatch.setattr(versions_mod, "MIGRATIONS", (*versions_mod.MIGRATIONS, bad))

    store = SQLiteStore(tmp_path / "store.db")
    with pytest.raises(StoreUnavailable):
        apply_migrations(store._conn, SCHEMA_VERSION + 1)
    store.close()


def test_revert_migration_failure_raises_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing revert surfaces StoreUnavailable."""

    from planner_critic.store import versions as versions_mod
    from planner_critic.store.versions import Migration

    bad = Migration(
        version=SCHEMA_VERSION + 1,
        name="bad",
        up="CREATE TABLE nope_bad (id INTEGER)",
        down="THIS IS NOT SQL",
    )
    monkeypatch.setattr(versions_mod, "MIGRATIONS", (*versions_mod.MIGRATIONS, bad))

    store = SQLiteStore(tmp_path / "store.db")
    apply_migrations(store._conn, SCHEMA_VERSION + 1)
    with pytest.raises(StoreUnavailable):
        revert_migrations(store._conn, 0)
    store.close()
