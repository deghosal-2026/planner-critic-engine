"""Inverse Rollback DAG Synthesizer tests (#160).

The synthesizer builds a rollback DAG from a forward plan at approval time
by reversing every forward edge, using a domain-pack action-inversion
registry. Supports partial rollback on failure at step N.
"""

from __future__ import annotations

import pytest

from conftest import hard_dep, make_plan
from planner_critic.rollback_synth import (
    InverseRollbackSynthesizer,
    Reversibility,
    action_inversion_registry,
    rollback_dag_valid,
)
from planner_critic.schema.plan import PlanVersion, Task
from planner_critic.types import Severity


def _task(tid: str, action: str = "do", **kw: object) -> Task:
    return Task.model_validate(
        {"id": tid, "description": f"task {tid}", "action": action, "target": tid, **kw}
    )


class TestActionInversionRegistry:
    def test_default_registry_has_entries(self) -> None:
        reg = action_inversion_registry()
        assert isinstance(reg, dict)
        assert "create" in reg
        assert "delete" in reg
        assert "enable" in reg
        assert "disable" in reg

    def test_registry_reversibility_enum(self) -> None:
        reg = action_inversion_registry()
        assert reg["create"] == Reversibility.SNAPSHOT_RESTORE
        assert reg["delete"] == Reversibility.DETERMINISTIC

    def test_custom_registry_merges(self) -> None:
        reg = action_inversion_registry({"custom_op": Reversibility.SNAPSHOT_RESTORE})
        assert "custom_op" in reg
        assert "create" in reg


class TestRollbackDagValidity:
    def test_acyclic_plan_passes(self) -> None:
        plan = make_plan(
            tasks=[_task("a", "create"), _task("b", "delete")],
            dependencies=[hard_dep("a", "b")],
        )
        assert rollback_dag_valid(plan) is True

    def test_cycle_plan_fails(self) -> None:
        plan = make_plan(
            tasks=[_task("a"), _task("b")],
            dependencies=[hard_dep("a", "b"), hard_dep("b", "a")],
        )
        assert rollback_dag_valid(plan) is False


class TestTraceFindings:
    """Verify the trace findings emitted by the synthesizer."""

    def test_build_rollback_emits_dag_generated(self) -> None:
        plan = make_plan(tasks=[_task("x", "create")])
        synth = InverseRollbackSynthesizer()
        synth.build_rollback(plan)
        codes = {f.reason_code for f in synth.trace}
        assert "rollback_dag_generated" in codes

    def test_partial_rollback_emits_execution_triggered(self) -> None:
        plan = make_plan(
            tasks=[_task("a", "create"), _task("b", "create")],
            dependencies=[hard_dep("a", "b")],
        )
        synth = InverseRollbackSynthesizer()
        synth.build_partial_rollback(plan, failed_step="b")
        codes = {f.reason_code for f in synth.trace}
        assert "rollback_execution_triggered" in codes

    def test_non_reversible_emits_skipped(self) -> None:
        plan = make_plan(tasks=[_task("pub", "publish")])
        synth = InverseRollbackSynthesizer()
        synth.build_rollback(plan)
        codes = {f.reason_code for f in synth.trace}
        assert "rollback_non_reversible_step_skipped" in codes

    def test_unknown_action_emits_missing_mapping(self) -> None:
        plan = make_plan(tasks=[_task("custom", "custom_op")])
        synth = InverseRollbackSynthesizer()
        synth.build_rollback(plan)
        codes = {f.reason_code for f in synth.trace}
        assert "rollback_non_reversible_step_skipped" in codes

    def test_trace_findings_are_info_severity(self) -> None:
        plan = make_plan(tasks=[_task("x", "create")])
        synth = InverseRollbackSynthesizer()
        synth.build_rollback(plan)
        for f in synth.trace:
            assert f.severity is Severity.INFO


class TestInverseRollbackSynthesizer:
    def test_builds_rollback_plan(self) -> None:
        plan = make_plan(
            tasks=[_task("create_db", "create"), _task("create_table", "create")],
            dependencies=[hard_dep("create_db", "create_table")],
        )
        synth = InverseRollbackSynthesizer()
        rollback = synth.build_rollback(plan)
        assert isinstance(rollback, PlanVersion)
        rollback_ids = [t.id for t in rollback.tasks]
        assert rollback_ids[0] == "rollback:create_table"
        assert rollback_ids[-1] == "rollback:create_db"

    def test_rollback_actions_are_inverted(self) -> None:
        plan = make_plan(tasks=[_task("s3", "create", target="bucket")])
        synth = InverseRollbackSynthesizer()
        rollback = synth.build_rollback(plan)
        assert rollback.tasks[0].action == "restore_snapshot"

    def test_non_reversible_becomes_noop(self) -> None:
        plan = make_plan(tasks=[_task("irreversible", "publish", target="release")])
        synth = InverseRollbackSynthesizer()
        rollback = synth.build_rollback(plan)
        assert rollback.tasks[0].action == "sys.noop"

    def test_partial_rollback_filters_completed(self) -> None:
        plan = make_plan(
            tasks=[_task("a", "create"), _task("b", "create"), _task("c", "create")],
            dependencies=[hard_dep("a", "b"), hard_dep("b", "c")],
        )
        synth = InverseRollbackSynthesizer()
        rollback = synth.build_partial_rollback(plan, failed_step="b")
        rollback_ids = {t.id for t in rollback.tasks}
        assert "rollback:a" in rollback_ids
        assert "rollback:b" not in rollback_ids
        assert "rollback:c" not in rollback_ids

    def test_partial_rollback_reverse_order(self) -> None:
        plan = make_plan(
            tasks=[_task("a", "create"), _task("b", "create"), _task("c", "create")],
            dependencies=[hard_dep("a", "b"), hard_dep("b", "c")],
        )
        synth = InverseRollbackSynthesizer()
        rollback = synth.build_partial_rollback(plan, failed_step="c")
        ids = [t.id for t in rollback.tasks]
        assert ids[0] == "rollback:b"
        assert ids[1] == "rollback:a"

    def test_no_dependencies_rollback_reverses_list(self) -> None:
        plan = make_plan(tasks=[_task("x", "create"), _task("y", "create")])
        synth = InverseRollbackSynthesizer()
        rollback = synth.build_rollback(plan)
        ids = [t.id for t in rollback.tasks]
        assert ids == ["rollback:y", "rollback:x"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
