"""SQLite-backed plan store (F-63, F-09): the production default.

Stores every plan revision, its critique findings, escalations, and execution
traces in a single SQLite database. Typed models are serialized to JSON
bodies; indexed columns (``goal_id``, ``plan_id``, ``version``, ``parent``)
make listing and latest-revision lookups fast. The schema mirrors the
:class:`~planner_critic.store.base.PlanStore` protocol exactly, so a run can
move between :class:`InMemoryStore` and :class:`SQLiteStore` unchanged.

Side-channel contract (§7.2): if the database is unreachable or the schema
mismatches, :class:`StoreUnavailable` is raised so the caller warns and
continues in memory. The store never silently drops a write.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, cast

from ..schema.plan import PlanVersion
from ..types import Escalation, ExecutionTrace, Finding
from .base import PlanDiff, PlanStore, StoreUnavailable, _compute_diff
from .versions import apply_migrations


class SQLiteStore(PlanStore):
    """A :class:`PlanStore` backed by a single SQLite database file.

    Args:
        path: Database file path (``:memory:`` for tests is supported).
    """

    def __init__(self, path: str | Path) -> None:
        """Open (or create) the database and ensure the schema exists.

        Args:
            path: SQLite database path.

        Raises:
            StoreUnavailable: if the database cannot be opened or migrated.
        """
        self._path = str(path)
        try:
            self._conn = sqlite3.connect(self._path)
            self._conn.row_factory = sqlite3.Row
            apply_migrations(self._conn)
        except sqlite3.Error as err:
            raise StoreUnavailable(f"cannot open store {self._path}: {err}") from err

    # -- PlanStore protocol ---------------------------------------------------
    def put_plan_version(self, plan: PlanVersion) -> None:
        """Persist a plan revision (immutable once written)."""
        row = {
            "plan_id": plan.id,
            "goal_id": plan.goal_id,
            "plan_schema_version": plan.plan_schema_version,
            "version": plan.version,
            "parent_version": plan.parent_version,
            "created_at": plan.created_at.isoformat(),
            "body": json.dumps(plan.to_dict()),
        }
        self._execute(
            """
            INSERT OR REPLACE INTO plan_versions (
                plan_id, goal_id, plan_schema_version, version, parent_version,
                created_at, body
            ) VALUES (
                :plan_id, :goal_id, :plan_schema_version, :version,
                :parent_version, :created_at, :body
            )
            """,
            row,
        )

    def put_findings(self, plan_id: str, version: int, findings: list[Finding]) -> None:
        """Persist the critique findings for one revision."""
        body = json.dumps([f.model_dump(mode="json") for f in findings])
        self._execute(
            "INSERT OR REPLACE INTO findings (plan_id, version, body) VALUES (?, ?, ?)",
            (plan_id, version, body),
        )

    def get_plan(self, plan_id: str, version: int | None = None) -> PlanVersion | None:
        """Fetch a revision; the latest when version is omitted."""
        if version is not None:
            row = self._fetchone(
                "SELECT body FROM plan_versions WHERE plan_id = ? AND version = ?",
                (plan_id, version),
            )
        else:
            row = self._fetchone(
                "SELECT body FROM plan_versions WHERE plan_id = ? "
                "ORDER BY version DESC LIMIT 1",
                (plan_id,),
            )
        if row is None:
            return None
        return PlanVersion.from_dict(json.loads(row["body"]))

    def list_plans(self, goal_id: str | None = None) -> list[PlanVersion]:
        """List stored revisions, newest first, optionally per goal."""
        if goal_id is None:
            rows = self._fetchall(
                "SELECT body FROM plan_versions ORDER BY plan_id, version DESC"
            )
        else:
            rows = self._fetchall(
                "SELECT body FROM plan_versions WHERE goal_id = ? "
                "ORDER BY plan_id, version DESC",
                (goal_id,),
            )
        return [PlanVersion.from_dict(json.loads(r["body"])) for r in rows]

    def diff(self, plan_id: str, version_a: int, version_b: int) -> PlanDiff | None:
        """Diff two revisions; None when either revision is unknown."""
        a = self.get_plan(plan_id, version_a)
        b = self.get_plan(plan_id, version_b)
        if a is None or b is None:
            return None
        return _compute_diff(a, b)

    def put_escalation(self, escalation: Escalation) -> None:
        """Persist an escalation by plan id."""
        self._execute(
            "INSERT OR REPLACE INTO escalations (plan_id, body) VALUES (?, ?)",
            (escalation.plan_id, json.dumps(escalation.model_dump(mode="json"))),
        )

    def get_escalation(self, plan_id: str) -> Escalation | None:
        """Fetch the escalation for a plan, if any."""
        row = self._fetchone(
            "SELECT body FROM escalations WHERE plan_id = ?", (plan_id,)
        )
        if row is None:
            return None
        return Escalation.model_validate(json.loads(row["body"]))

    def put_execution_trace(self, trace: ExecutionTrace) -> None:
        """Append one step to a plan's execution trace."""
        self._execute(
            "INSERT INTO execution_traces (plan_id, body) VALUES (?, ?)",
            (trace.plan_id, json.dumps(trace.model_dump(mode="json"))),
        )

    def get_execution_traces(self, plan_id: str) -> list[ExecutionTrace]:
        """Fetch a plan's recorded execution steps in insertion order."""
        rows = self._fetchall(
            "SELECT body FROM execution_traces WHERE plan_id = ? ORDER BY seq",
            (plan_id,),
        )
        return [ExecutionTrace.model_validate(json.loads(r["body"])) for r in rows]

    def link(self, plan_id: str, version: int, trace_id: str) -> None:
        """Record an approved-revision ↔ execution-trace link."""
        self._execute(
            "INSERT OR IGNORE INTO links (plan_id, version, trace_id) VALUES (?, ?, ?)",
            (plan_id, version, trace_id),
        )

    def close(self) -> None:
        """Close the underlying connection."""
        self._conn.close()

    # -- internals ------------------------------------------------------------
    def _execute(self, sql: str, params: tuple[Any, ...] | dict[str, Any]) -> None:
        """Run a write, translating DB failures into :class:`StoreUnavailable`."""
        try:
            with self._conn:
                self._conn.execute(sql, params)
        except sqlite3.Error as err:
            raise StoreUnavailable(f"store write failed: {err}") from err

    def _fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        """Run a read; a DB failure is a side-channel signal, not a crash."""
        try:
            row = self._conn.execute(sql, params).fetchone()
            return cast("sqlite3.Row | None", row)
        except sqlite3.Error as err:
            raise StoreUnavailable(f"store read failed: {err}") from err

    def _fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        """Run a read returning all rows."""
        try:
            return self._conn.execute(sql, params).fetchall()
        except sqlite3.Error as err:
            raise StoreUnavailable(f"store read failed: {err}") from err
