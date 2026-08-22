"""Topological sequence auto-repair tests (#130).

The deterministic auto-repair pass runs after the deterministic gates and
before the LLM critic: a plan whose only gate blockers are ordering-only
violations (a task listed before its hard dependency, with an acyclic graph)
gets re-ordered via topological sort rather than spending an LLM revision.

These tests pin the four guarantees in the issue:
1. ordering-only violations are repaired in-place (revision 1, no revise);
2. dependency cycles are never auto-repaired (fall through);
3. unsafe parallelization is never auto-repaired (fall through);
4. mixed blockers (ordering + a non-ordering family) are never auto-repaired;
5. ``auto_repair: off`` routes ordering violations to the critic as before.
"""

from __future__ import annotations

import pytest

from conftest import (
    EmptyCritic,
    ScriptedPlanner,
    hard_dep,
    make_goal,
    make_plan,
    make_task,
)
from planner_critic.loop import LoopConfig, run_loop
from planner_critic.schema.plan import PlanVersion
from planner_critic.types import Severity

AUTO_REPAIRED_ORDERING = "auto_repaired_ordering"


def _ordering_violation_plan() -> PlanVersion:
    """Three medium-risk tasks listed C, B, A with a hard dependency A -> C.

    ``ordering_sane`` flags task C as ordered before its hard dependency A.
    The graph is a DAG and no other gate fires (all medium risk), so this is
    a pure ordering-only violation.
    """
    return make_plan(
        tasks=[make_task("C"), make_task("B"), make_task("A")],
        dependencies=[hard_dep("A", "C")],
    )


class TestAutoRepairFires:
    """Ordering-only violations are repaired deterministically (no revision)."""

    def test_ordering_violation_repaired_at_revision_1(self, empty_critic: EmptyCritic) -> None:
        """A task listed before its hard dependency is re-ordered and approved."""
        goal = make_goal()
        planner = ScriptedPlanner([_ordering_violation_plan()])
        result = run_loop(goal, planner, empty_critic, config=LoopConfig())
        assert result.is_approved
        assert result.approved_plan is not None
        assert result.spend is not None
        assert result.spend.revisions_used == 1, "auto-repair must not spend a revision"

    def test_repaired_plan_satisfies_ordering(self, empty_critic: EmptyCritic) -> None:
        """After repair the hard dependency A -> C is honored in the plan order."""
        goal = make_goal()
        planner = ScriptedPlanner([_ordering_violation_plan()])
        result = run_loop(goal, planner, empty_critic, config=LoopConfig())
        assert result.approved_plan is not None
        order = [t.id for t in result.approved_plan.plan.tasks]
        assert order.index("A") < order.index("C")

    def test_info_finding_recorded_in_trace(self, empty_critic: EmptyCritic) -> None:
        """The repair is recorded as an info finding in the result trace."""
        goal = make_goal()
        planner = ScriptedPlanner([_ordering_violation_plan()])
        result = run_loop(goal, planner, empty_critic, config=LoopConfig())
        repairs = [f for f in result.findings if f.reason_code == AUTO_REPAIRED_ORDERING]
        assert repairs, "the trace must record the auto-repair"
        assert repairs[0].severity is Severity.INFO


class TestAutoRepairDoesNotFire:
    """Non-ordering-only violations always fall through to the critic."""

    def test_dependency_cycle_not_auto_repaired(self, empty_critic: EmptyCritic) -> None:
        """A dependency cycle is not a sort problem; auto-repair must not fire."""
        plan = make_plan(
            tasks=[make_task("A"), make_task("B")],
            dependencies=[hard_dep("A", "B"), hard_dep("B", "A")],
        )
        goal = make_goal()
        planner = ScriptedPlanner([plan])
        result = run_loop(goal, planner, empty_critic, config=LoopConfig(revision_cap=2))
        assert not result.is_approved
        assert not any(f.reason_code == AUTO_REPAIRED_ORDERING for f in result.findings)

    def test_unsafe_parallelization_not_auto_repaired(self, empty_critic: EmptyCritic) -> None:
        """Two high-blast tasks in one parallel group are not a sort problem."""
        plan = make_plan(
            tasks=[
                make_task("P1", risk_class="critical", parallel_group="g1"),
                make_task("P2", risk_class="critical", parallel_group="g1"),
            ],
        )
        goal = make_goal()
        planner = ScriptedPlanner([plan])
        result = run_loop(goal, planner, empty_critic, config=LoopConfig(revision_cap=2))
        assert not result.is_approved
        assert not any(f.reason_code == AUTO_REPAIRED_ORDERING for f in result.findings)

    def test_mixed_blocker_not_auto_repaired(self, empty_critic: EmptyCritic) -> None:
        """Ordering + missing-verification is not ordering-only; no auto-repair."""
        plan = make_plan(
            tasks=[make_task("C", risk_class="critical"), make_task("A")],
            dependencies=[hard_dep("A", "C")],
        )
        goal = make_goal()
        planner = ScriptedPlanner([plan])
        result = run_loop(goal, planner, empty_critic, config=LoopConfig(revision_cap=2))
        assert not result.is_approved
        assert not any(f.reason_code == AUTO_REPAIRED_ORDERING for f in result.findings)


class TestAutoRepairConfig:
    """``auto_repair: off`` restores the pre-M2 escalate/revise behavior."""

    def test_auto_repair_off_disables_pass(self, empty_critic: EmptyCritic) -> None:
        """With auto_repair off the ordering violation escalates (never repaired)."""
        goal = make_goal()
        planner = ScriptedPlanner([_ordering_violation_plan()])
        result = run_loop(
            goal,
            planner,
            empty_critic,
            config=LoopConfig(auto_repair=False, revision_cap=2),
        )
        assert not result.is_approved
        assert not any(f.reason_code == AUTO_REPAIRED_ORDERING for f in result.findings)

    def test_auto_repair_off_ordering_finding_survives(self, empty_critic: EmptyCritic) -> None:
        """Off-path still surfaces the original unsafe_ordering blocker."""
        goal = make_goal()
        planner = ScriptedPlanner([_ordering_violation_plan()])
        result = run_loop(
            goal,
            planner,
            empty_critic,
            config=LoopConfig(auto_repair=False, revision_cap=2),
        )
        assert any(f.reason_code == "unsafe_ordering" for f in result.findings)


class TestDeterminism:
    """Auto-repair is deterministic on identical inputs (F-74)."""

    def test_identical_inputs_identical_decisions(self) -> None:
        """Two runs of the same violating plan produce the same order + decision."""
        goal = make_goal()

        def run() -> tuple[str, tuple[str, ...]]:
            planner = ScriptedPlanner([_ordering_violation_plan()])
            result = run_loop(goal, planner, EmptyCritic(), config=LoopConfig())
            assert result.approved_plan is not None
            order = tuple(t.id for t in result.approved_plan.plan.tasks)
            return result.status, order

        assert run() == run()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
