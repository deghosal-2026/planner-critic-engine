"""Tests for the pytest-planner-critic plugin (#156).

The plugin provides fixtures and assertion helpers that make plan-gate
testing concise and readable.
"""

from __future__ import annotations

import pytest

from conftest import hard_dep, make_goal, make_plan, make_task
from planner_critic.gates.ordering import Gate as OrderingGate
from planner_critic.pytest_plugin import (
    GraphDiffFormatter,
    assert_gate_fails,
    assert_gate_passes,
    assert_no_circular_dependencies,
    assert_node_precedes,
    assert_plan_converges,
    format_dag_diff,
    pytest_assertrepr_compare,
)
from planner_critic.schema.plan import PlanVersion


class TestGraphDiffFormatter:
    """DAG diff rendering for assertion messages."""

    def test_format_dag_diff(self) -> None:
        """Two plans with different task orders produce a readable diff."""
        plan_a = make_plan(
            tasks=[make_task("A"), make_task("B"), make_task("C")],
            dependencies=[hard_dep("A", "B")],
        )
        plan_b = make_plan(
            tasks=[make_task("B"), make_task("A"), make_task("C")],
            dependencies=[hard_dep("A", "B")],
        )
        diff = format_dag_diff(plan_a, plan_b)
        assert isinstance(diff, str)
        assert len(diff) > 0

    def test_format_dag_diff_with_edge_diffs(self) -> None:
        """DAG diff shows missing and unexpected edges."""
        plan_a = make_plan(
            tasks=[make_task("A"), make_task("B")],
            dependencies=[hard_dep("A", "B")],
        )
        plan_b = make_plan(
            tasks=[make_task("A"), make_task("B")],
        )
        diff = format_dag_diff(plan_a, plan_b)
        assert "missing edge" in diff.lower() or "unexpected edge" in diff.lower()

    def test_format_dag_diff_identical(self) -> None:
        """Identical plans produce a short message."""
        plan = make_plan(
            tasks=[make_task("A"), make_task("B")],
            dependencies=[hard_dep("A", "B")],
        )
        diff = format_dag_diff(plan, plan)
        assert "identical" in diff.lower() or diff == ""


class TestAssertNodePrecedes:
    """Assert ordering constraints in a plan."""

    def test_pass_when_precedes(self) -> None:
        """A before B in the plan passes."""
        plan = make_plan(
            tasks=[make_task("A"), make_task("B")],
        )
        assert_node_precedes(plan, "A", "B")

    def test_fail_when_does_not_precede(self) -> None:
        """B before A fails."""
        plan = make_plan(
            tasks=[make_task("B"), make_task("A")],
        )
        with pytest.raises(AssertionError, match=r"expected.*before"):
            assert_node_precedes(plan, "A", "B")


class TestAssertNoCircularDependencies:
    """Assert the plan's dependency graph is a DAG."""

    def test_pass_on_acyclic(self) -> None:
        """A simple linear chain passes."""
        plan = make_plan(
            tasks=[make_task("A"), make_task("B")],
            dependencies=[hard_dep("A", "B")],
        )
        assert_no_circular_dependencies(plan)

    def test_fail_on_cycle(self) -> None:
        """A cycle raises an informative AssertionError."""
        plan = make_plan(
            tasks=[make_task("A"), make_task("B")],
            dependencies=[hard_dep("A", "B"), hard_dep("B", "A")],
        )
        with pytest.raises(AssertionError, match="cycle"):
            assert_no_circular_dependencies(plan)


class TestAssertGatePasses:
    """Assert a gate finds no violations."""

    def test_passes_on_clean_plan(self) -> None:
        """A medium-risk plan passes the verification gate."""
        plan = make_plan(tasks=[make_task("t1")])
        gate = OrderingGate()
        assert_gate_passes(gate, plan)

    def test_fails_on_violation(self) -> None:
        """An ordering violation fails."""
        plan = make_plan(
            tasks=[make_task("C"), make_task("A")],
            dependencies=[hard_dep("A", "C")],
        )
        gate = OrderingGate()
        with pytest.raises(AssertionError, match="unsafe_ordering"):
            assert_gate_passes(gate, plan)


class TestAssertGateFails:
    """Assert a gate finds specific violations."""

    def test_fails_with_expected_reason(self) -> None:
        """The assertion passes when the gate produces the expected code."""
        plan = make_plan(
            tasks=[make_task("C"), make_task("A")],
            dependencies=[hard_dep("A", "C")],
        )
        gate = OrderingGate()
        assert_gate_fails(gate, plan, "unsafe_ordering")

    def test_fails_without_reason_any_blocker(self) -> None:
        """Without a reason code, any blocker is sufficient."""
        plan = make_plan(
            tasks=[make_task("C"), make_task("A")],
            dependencies=[hard_dep("A", "C")],
        )
        gate = OrderingGate()
        assert_gate_fails(gate, plan)

    def test_raises_when_gate_passes(self) -> None:
        """Asserting a gate fails when it passes raises AssertionError."""
        plan = make_plan(tasks=[make_task("t1")])
        gate = OrderingGate()
        with pytest.raises(AssertionError, match=r"expected.*blocker"):
            assert_gate_fails(gate, plan)

    def test_raises_when_reason_code_mismatch(self) -> None:
        """A gate that fires with a different reason raises AssertionError."""
        plan = make_plan(
            tasks=[make_task("C"), make_task("A")],
            dependencies=[hard_dep("A", "C")],
        )
        gate = OrderingGate()
        with pytest.raises(AssertionError, match=r"reason_code.*among blocker"):
            assert_gate_fails(gate, plan, "missing_verification")


class TestAssertPlanConverges:
    """Assert a goal+plan combination converges to approval."""

    def test_pass_on_clean_plan(self) -> None:
        """A gate-clean plan with an empty critic approves at revision 1."""
        from conftest import EmptyCritic, ScriptedPlanner, make_goal

        plan = make_plan()
        goal = make_goal()
        planner = ScriptedPlanner([plan])
        critic = EmptyCritic()
        assert_plan_converges(goal, planner, critic)

    def test_fail_on_blocked_plan(self) -> None:
        """A plan that cannot converge raises AssertionError."""
        from conftest import EmptyCritic, ScriptedPlanner
        from planner_critic.loop import LoopConfig

        plan = make_plan(
            tasks=[make_task("C"), make_task("A")],
            dependencies=[hard_dep("A", "C")],
        )
        goal = make_goal()
        planner = ScriptedPlanner([plan])
        critic = EmptyCritic()
        cfg = LoopConfig(auto_repair=False, revision_cap=2)
        with pytest.raises(AssertionError, match=r"converge|approved"):
            assert_plan_converges(goal, planner, critic, loop_config=cfg)


class TestGraphDiffFormatterObject:
    """GraphDiffFormatter class and pytest_assertrepr_compare hook."""

    def test_formatter_str(self) -> None:
        """GraphDiffFormatter.__str__ returns a readable diff."""
        a = make_plan(tasks=[make_task("X"), make_task("Y")])
        b = make_plan(tasks=[make_task("Y"), make_task("X")])
        fmt = GraphDiffFormatter(a, b)
        out = str(fmt)
        assert isinstance(out, str)
        assert len(out) > 0

    def test_pytest_compare_identical(self) -> None:
        """pytest_assertrepr_compare returns diff showing identical for same plans."""
        plan = make_plan()
        result = pytest_assertrepr_compare(None, "==", plan, plan)
        assert result is not None
        assert any("identical" in line for line in result)

    def test_pytest_compare_different(self) -> None:
        """pytest_assertrepr_compare returns a diff for different plans."""
        a = make_plan(tasks=[make_task("X")])
        b = make_plan(tasks=[make_task("Y")])
        result = pytest_assertrepr_compare(None, "==", a, b)
        assert result is not None
        assert any("PlanVersion mismatch" in line for line in result)

    def test_pytest_compare_non_plan_ignored(self) -> None:
        """Non-PlanVersion comparisons return None."""
        result = pytest_assertrepr_compare(None, "==", 1, 2)
        assert result is None


class TestAssertNodePrecedesEdgeCases:
    """Edge cases for assert_node_precedes."""

    def test_unknown_task_raises(self) -> None:
        """A task id not in the plan raises AssertionError."""
        plan = make_plan(tasks=[make_task("A")])
        with pytest.raises(AssertionError, match="not found"):
            assert_node_precedes(plan, "A", "MISSING")


class TestPlanBuilder:
    """The plan_builder fixture produces valid plans."""

    def test_builder_basic_plan(self) -> None:
        """A plan_builder with one task produces a valid plan."""
        from planner_critic.pytest_plugin import _PlanBuilder

        builder = _PlanBuilder()
        plan = builder.with_task("backup", risk_class="medium").build()
        assert isinstance(plan, PlanVersion)
        assert len(plan.tasks) == 1
        assert plan.tasks[0].id == "backup"

    def test_builder_with_deps(self) -> None:
        """A plan with dependencies is built correctly."""
        from planner_critic.pytest_plugin import _PlanBuilder

        plan = (
            _PlanBuilder()
            .with_task("backup")
            .with_task("migrate")
            .with_dependency("backup", "migrate")
            .build()
        )
        assert len(plan.tasks) == 2
        assert len(plan.dependencies) == 1
        assert plan.dependencies[0].from_task == "backup"
        assert plan.dependencies[0].to_task == "migrate"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
