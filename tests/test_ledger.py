from __future__ import annotations

from planner_critic.ledger import PreconditionLedger
from planner_critic.schema.plan import PlanVersion, Precondition, RiskClass, Task


def _make_precondition(fact: str) -> Precondition:
    return Precondition(description=fact, fact=fact, established_by="env")


def _task(tid: str, preconditions: list[Precondition] | None = None) -> Task:
    return Task(
        id=tid,
        description=f"task {tid}",
        action="do",
        target=tid,
        risk_class=RiskClass.LOW,
        preconditions=preconditions or [],
    )


class TestPreconditionLedger:
    def test_new_entry_not_satisfied(self) -> None:
        ledger = PreconditionLedger()
        assert not ledger.is_satisfied("is_authenticated")

    def test_mark_satisfied(self) -> None:
        ledger = PreconditionLedger()
        ledger.mark_satisfied("is_authenticated", "task-1")
        assert ledger.is_satisfied("is_authenticated")
        entry = ledger.get_entry("is_authenticated")
        assert entry is not None
        assert entry.satisfied is True
        assert entry.satisfied_by == "task-1"

    def test_cross_revision_persistence(self) -> None:
        ledger = PreconditionLedger()
        ledger.mark_satisfied("snapshot_created", "task-1")
        ledger.mark_satisfied("db_healthy", "task-2")
        assert ledger.is_satisfied("snapshot_created")
        assert ledger.is_satisfied("db_healthy")
        assert not ledger.is_satisfied("lockfile_generated")

    def test_process_plan_redundant_re_injection(self) -> None:
        ledger = PreconditionLedger()
        ledger.mark_satisfied("db_healthy", "env_probe")
        plan = PlanVersion(
            id="plan-1",
            goal_id="goal-1",
            version=3,
            tasks=[_task("t1", [_make_precondition("db_healthy")])],
            dependencies=[],
        )
        ledger.process_plan(plan)
        diag = ledger.diagnostics()
        assert len(diag) == 1
        assert diag[0]["type"] == "precondition_redundantly_re_injected"
        assert diag[0]["task_id"] == "t1"

    def test_process_plan_unverified_precondition(self) -> None:
        ledger = PreconditionLedger()
        plan = PlanVersion(
            id="plan-1",
            goal_id="goal-1",
            version=1,
            tasks=[_task("t1", [_make_precondition("db_healthy")])],
            dependencies=[],
        )
        ledger.process_plan(plan)
        diag = ledger.diagnostics()
        assert len(diag) == 1
        assert diag[0]["type"] == "unverified"
        assert diag[0]["key"] == "db_healthy"

    def test_dropped_precondition_compaction(self) -> None:
        ledger = PreconditionLedger()
        ledger.mark_satisfied("cleanup_done", "task-2")
        plan = PlanVersion(
            id="plan-1",
            goal_id="goal-1",
            version=5,
            tasks=[_task("t1", [_make_precondition("auth_done")])],
            dependencies=[],
        )
        ledger.process_plan(plan)
        diag = ledger.diagnostics()
        types = [d["type"] for d in diag]
        assert "precondition_dropped_from_compaction" in types
        dropped = [d for d in diag if d["type"] == "precondition_dropped_from_compaction"]
        assert len(dropped) == 1
        assert dropped[0]["key"] == "cleanup_done"

    def test_process_plan_no_issues(self) -> None:
        ledger = PreconditionLedger()
        ledger.mark_satisfied("auth_done", "task-1")
        plan = PlanVersion(
            id="plan-1",
            goal_id="goal-1",
            version=2,
            tasks=[_task("t2", [_make_precondition("auth_done")])],
            dependencies=[],
        )
        ledger.process_plan(plan)
        assert len(ledger.diagnostics()) == 1
        assert ledger.diagnostics()[0]["type"] == "precondition_redundantly_re_injected"

    def test_clear_diagnostics(self) -> None:
        ledger = PreconditionLedger()
        ledger.mark_satisfied("x", "t1")
        plan = PlanVersion(
            id="plan-1",
            goal_id="goal-1",
            version=1,
            tasks=[_task("t2", [_make_precondition("x")])],
            dependencies=[],
        )
        ledger.process_plan(plan)
        assert len(ledger.diagnostics()) == 1
        ledger.clear_diagnostics()
        assert len(ledger.diagnostics()) == 0

    def test_to_dict(self) -> None:
        ledger = PreconditionLedger()
        ledger.mark_satisfied("is_authenticated", "task-1")
        d = ledger.to_dict()
        assert "is_authenticated" in d
        assert d["is_authenticated"]["satisfied"] is True
        assert d["is_authenticated"]["satisfied_by"] == "task-1"
