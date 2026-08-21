"""``plancritic migrate`` C23 field-test coverage (#85).

C23 requires the migration path to be hermetic and lossless: ``migrate`` must
bring a fresh store to ``SCHEMA_VERSION``, and a plan write against the
migrated store must succeed with the schema version matching the code's
:data:`~planner_critic.store.versions.SCHEMA_VERSION`. These tests drive the
CLI (:func:`planner_critic.cli.migrate.run_migrate`) and the programmatic
migration registry against a real SQLite file.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from planner_critic.cli.migrate import run_migrate
from planner_critic.schema.plan import PlanVersion
from planner_critic.store.versions import (
    SCHEMA_VERSION,
    apply_migrations,
    revert_migrations,
)


def _plan(db_path: str) -> PlanVersion:
    """A minimal valid plan to store against a migrated store."""
    return PlanVersion.model_validate(
        {
            "id": "p-mig",
            "goal_id": "g1",
            "version": 1,
            "tasks": [
                {
                    "id": "t1",
                    "description": "task t1",
                    "action": "do",
                    "target": "t1",
                    "risk_class": "medium",
                    "preconditions": [],
                }
            ],
            "dependencies": [],
            "branches": [],
        }
    )


def test_migrate_brings_fresh_store_to_current_schema(tmp_path: Path) -> None:
    """``migrate`` on a fresh store reports schema at SCHEMA_VERSION (#85 C23)."""
    rc = run_migrate(["--path", str(tmp_path / "plans.db")])
    assert rc == 0
    with sqlite3.connect(tmp_path / "plans.db") as conn:
        current = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
    assert current == SCHEMA_VERSION


def test_migrate_store_accepts_plan_write(tmp_path: Path) -> None:
    """A plan write succeeds against a CLI-migrated store (#85 C23)."""
    store_path = str(tmp_path / "plans.db")
    assert run_migrate(["--path", store_path]) == 0

    from planner_critic.store.sqlite import SQLiteStore

    store = SQLiteStore(store_path)
    try:
        store.put_plan_version(_plan(store_path))
        plans = store.list_plans(goal_id="g1")
    finally:
        store.close()
    assert len(plans) == 1
    assert plans[0].id == "p-mig"


def test_migrate_revert_is_lossless_and_reappliable(tmp_path: Path) -> None:
    """Reverting then re-applying migrations stays reversible (#85 C23)."""
    store_path = str(tmp_path / "plans.db")
    conn = sqlite3.connect(store_path)
    try:
        reached = apply_migrations(conn)
        assert reached == SCHEMA_VERSION
        down = revert_migrations(conn, 0)
        assert down == 0
        up = apply_migrations(conn)
        assert up == SCHEMA_VERSION
    finally:
        conn.close()


def test_migrate_cli_revert_flag(tmp_path: Path, capsys) -> None:
    """``migrate --revert`` returns to an earlier schema and prints it."""
    store_path = str(tmp_path / "plans.db")
    assert run_migrate(["--path", store_path]) == 0
    rc = run_migrate(["--path", store_path, "--revert", "--to", "1"])
    assert rc == 0
    assert "reverted to schema v1" in capsys.readouterr().out
