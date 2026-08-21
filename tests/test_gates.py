"""Deterministic gate tests (F-12, F-15).

Each gate must flag its seeded-flaw fixture, and the orchestrator must run
them all in a stable order. Gates operate on typed plans only; malformed
input is rejected by the schema layer, so gates focus on semantic flaws.
"""

from __future__ import annotations

from conftest import hard_dep, make_plan, make_task
from planner_critic.gates import run_deterministic_gates
from planner_critic.reason_codes import (
    DEPENDENCY_CYCLE,
    MISSING_ROLLBACK,
    MISSING_VERIFICATION,
    PLAN_SCHEMA_INVALID,
    UNSAFE_ORDERING,
    UNSAFE_PARALLELIZATION,
    UNVERIFIED_PRECONDITION,
)
from planner_critic.types import Severity


class TestSchemaValidGate:
    """Empty-task / blank-id / bad schema-version reveal structural flaws."""

    def test_empty_task_list_flagged(self) -> None:
        """A plan with no tasks is structurally invalid."""
        findings = run_deterministic_gates(make_plan(tasks=[]))
        codes = {f.reason_code for f in findings}
        assert PLAN_SCHEMA_INVALID in codes

    def test_blank_task_id_flagged(self) -> None:
        """A blank task id is a structural flaw."""
        findings = run_deterministic_gates(make_plan(tasks=[make_task("valid"), make_task(" ")]))
        assert PLAN_SCHEMA_INVALID in {f.reason_code for f in findings}


class TestDepCyclesGate:
    """A hard-dependency cycle is a blocker."""

    def test_cycle_flagged(self) -> None:
        """t1 -> t2 -> t1 is a cycle."""
        plan = make_plan(
            tasks=[make_task("t1"), make_task("t2")],
            dependencies=[hard_dep("t1", "t2"), hard_dep("t2", "t1")],
        )
        findings = run_deterministic_gates(plan)
        codes = {f.reason_code for f in findings}
        assert DEPENDENCY_CYCLE in codes
        cycle_finding = next(f for f in findings if f.reason_code == DEPENDENCY_CYCLE)
        assert cycle_finding.severity is Severity.BLOCKER

    def test_longer_cycle_flagged(self) -> None:
        """t1 -> t2 -> t3 -> t1 is flagged too."""
        plan = make_plan(
            tasks=[make_task("t1"), make_task("t2"), make_task("t3")],
            dependencies=[
                hard_dep("t1", "t2"),
                hard_dep("t2", "t3"),
                hard_dep("t3", "t1"),
            ],
        )
        assert DEPENDENCY_CYCLE in {f.reason_code for f in run_deterministic_gates(plan)}

    def test_dag_passes(self) -> None:
        """A plain DAG is not flagged."""
        plan = make_plan(
            tasks=[make_task("t1"), make_task("t2")],
            dependencies=[hard_dep("t1", "t2")],
        )
        assert DEPENDENCY_CYCLE not in {f.reason_code for f in run_deterministic_gates(plan)}


class TestOrderingGate:
    """A task ordered before its hard dependency is a blocker."""

    def test_reversed_order_flagged(self) -> None:
        """t2 runs before t1 but depends on it."""
        plan = make_plan(
            tasks=[make_task("t2"), make_task("t1")],
            dependencies=[hard_dep("t1", "t2")],
        )
        findings = run_deterministic_gates(plan)
        codes = {f.reason_code for f in findings}
        assert UNSAFE_ORDERING in codes
        bad = next(f for f in findings if f.reason_code == UNSAFE_ORDERING)
        assert bad.task_id == "t2"

    def test_correct_order_passes(self) -> None:
        """t1 before t2 with t1->t2 is fine."""
        plan = make_plan(
            tasks=[make_task("t1"), make_task("t2")],
            dependencies=[hard_dep("t1", "t2")],
        )
        assert UNSAFE_ORDERING not in {f.reason_code for f in run_deterministic_gates(plan)}

    def test_no_dependencies_passes(self) -> None:
        """No edges → no ordering findings."""
        plan = make_plan(tasks=[make_task("t1"), make_task("t2")])
        assert UNSAFE_ORDERING not in {f.reason_code for f in run_deterministic_gates(plan)}


class TestVerificationGate:
    """High-blast-radius tasks need a verification step."""

    def test_high_risk_without_verification_flagged(self) -> None:
        """A critical task with no verification is a blocker."""
        plan = make_plan(tasks=[make_task("t1", risk_class="critical")])
        findings = run_deterministic_gates(plan)
        codes = {f.reason_code for f in findings}
        assert MISSING_VERIFICATION in codes
        bad = next(f for f in findings if f.reason_code == MISSING_VERIFICATION)
        assert bad.task_id == "t1"
        assert bad.severity is Severity.BLOCKER

    def test_high_blast_radius_flagged(self) -> None:
        """blast_radius=critical without verification is flagged."""
        plan = make_plan(tasks=[make_task("t1", blast_radius="critical")])
        assert MISSING_VERIFICATION in {f.reason_code for f in run_deterministic_gates(plan)}

    def test_verification_present_passes(self) -> None:
        """High-risk with verification passes the gate."""
        plan = make_plan(
            tasks=[
                make_task(
                    "t1",
                    risk_class="critical",
                    verification={"what": "x", "how": "y", "expected": "z"},
                )
            ]
        )
        assert MISSING_VERIFICATION not in {f.reason_code for f in run_deterministic_gates(plan)}

    def test_medium_risk_skipped(self) -> None:
        """Medium-risk tasks are not required to carry verification."""
        plan = make_plan(tasks=[make_task("t1")])
        assert MISSING_VERIFICATION not in {f.reason_code for f in run_deterministic_gates(plan)}


class TestRollbackGate:
    """High-blast-radius tasks need a rollback step."""

    def test_high_risk_without_rollback_flagged(self) -> None:
        """A critical task with no rollback is a blocker."""
        plan = make_plan(tasks=[make_task("t1", risk_class="high")])
        findings = run_deterministic_gates(plan)
        assert MISSING_ROLLBACK in {f.reason_code for f in findings}
        bad = next(f for f in findings if f.reason_code == MISSING_ROLLBACK)
        assert bad.task_id == "t1"

    def test_rollback_present_passes(self) -> None:
        """High-risk with rollback passes."""
        plan = make_plan(
            tasks=[
                make_task(
                    "t1",
                    risk_class="high",
                    rollback={"trigger": "fail", "action": "undo", "safety_guard": "g"},
                )
            ]
        )
        assert MISSING_ROLLBACK not in {f.reason_code for f in run_deterministic_gates(plan)}


class TestPreconditionsGate:
    """Preconditions must reference established facts."""

    def test_unreferenced_precondition_flagged(self) -> None:
        """A precondition with no source is unverifiable."""
        plan = make_plan(
            tasks=[make_task("t1", preconditions=[{"description": "p", "fact": "some fact"}])]
        )
        assert UNVERIFIED_PRECONDITION in {f.reason_code for f in run_deterministic_gates(plan)}

    def test_established_by_task_passes(self) -> None:
        """A precondition referencing an earlier task id is grounded."""
        plan = make_plan(
            tasks=[
                make_task("t1"),
                make_task(
                    "t2",
                    preconditions=[
                        {"description": "p", "fact": "t1 output", "established_by": "t1"}
                    ],
                ),
            ]
        )
        assert UNVERIFIED_PRECONDITION not in {f.reason_code for f in run_deterministic_gates(plan)}

    def test_probe_grounded_precondition_passes(self) -> None:
        """A probe-grounded precondition is verifiable by definition."""
        plan = make_plan(
            tasks=[
                make_task(
                    "t1",
                    preconditions=[
                        {
                            "description": "p",
                            "fact": "db up",
                            "probe": {"kind": "db_query", "query": "select 1", "expected": "1"},
                        }
                    ],
                )
            ]
        )
        assert UNVERIFIED_PRECONDITION not in {f.reason_code for f in run_deterministic_gates(plan)}

    def test_forward_reference_precondition_flagged(self) -> None:
        """A precondition may not reference a *later* task (not yet established).

        Regression: _established_facts previously treated every task id as
        grounded regardless of ordering, so a precondition pointing at a task
        that runs *after* it slipped through.
        """
        plan = make_plan(
            tasks=[
                make_task(
                    "t1",
                    preconditions=[
                        {"description": "p", "fact": "later output", "established_by": "t2"}
                    ],
                ),
                make_task("t2"),
            ]
        )
        assert UNVERIFIED_PRECONDITION in {f.reason_code for f in run_deterministic_gates(plan)}

    def test_self_reference_precondition_flagged(self) -> None:
        """A task cannot ground its own precondition."""
        plan = make_plan(
            tasks=[
                make_task(
                    "t1",
                    preconditions=[{"description": "p", "fact": "own", "established_by": "t1"}],
                )
            ]
        )
        assert UNVERIFIED_PRECONDITION in {f.reason_code for f in run_deterministic_gates(plan)}


class TestParallelSafetyGate:
    """Two high-blast tasks racing in one parallel group are unsafe."""

    def test_two_high_blast_flagged(self) -> None:
        """Two critical tasks in the same group is a concurrency hazard."""
        plan = make_plan(
            tasks=[
                make_task("t1", risk_class="high", parallel_group="g"),
                make_task("t2", risk_class="high", parallel_group="g"),
            ]
        )
        findings = run_deterministic_gates(plan)
        assert UNSAFE_PARALLELIZATION in {f.reason_code for f in findings}

    def test_single_high_blast_in_group_passes(self) -> None:
        """One high-blast task per group is fine."""
        plan = make_plan(
            tasks=[
                make_task("t1", risk_class="high", parallel_group="g"),
                make_task("t2", risk_class="low", parallel_group="g"),
            ]
        )
        assert UNSAFE_PARALLELIZATION not in {f.reason_code for f in run_deterministic_gates(plan)}


class TestOrchestrator:
    """run_deterministic_gates runs every gate in a stable order."""

    def test_clean_plan_has_no_findings(self) -> None:
        """A fully-validated low-risk plan passes every gate."""
        plan = make_plan(tasks=[make_task("t1"), make_task("t2")])
        assert run_deterministic_gates(plan) == []

    def test_deterministic_equal_plans_equal_findings(self) -> None:
        """Identical plan → identical findings (F-74 CI assertion)."""
        plan = make_plan(
            tasks=[
                make_task("t1", risk_class="high", parallel_group="g"),
                make_task("t2", risk_class="high", parallel_group="g"),
                make_task("t3", preconditions=[{"description": "unmet", "fact": "nope"}]),
            ]
        )
        plan2 = plan.model_copy(deep=True)
        assert [f.reason_code for f in run_deterministic_gates(plan)] == [
            f.reason_code for f in run_deterministic_gates(plan2)
        ]

    def test_all_gates_run(self) -> None:
        """The orchestrator returns findings from every gate when all flaws are seeded."""
        plan = make_plan(
            tasks=[
                make_task("t1", risk_class="high", parallel_group="g"),
                make_task("t2", risk_class="high", parallel_group="g"),
                make_task("t3", preconditions=[{"description": "unmet", "fact": "nope"}]),
            ]
        )
        findings = run_deterministic_gates(plan)
        codes = {f.reason_code for f in findings}
        assert MISSING_VERIFICATION in codes
        assert MISSING_ROLLBACK in codes
        assert UNSAFE_PARALLELIZATION in codes
        assert UNVERIFIED_PRECONDITION in codes
