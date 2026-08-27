"""Schema tests: Goal + PlanVersion construction, validation, round-trip.

Covers F-01 (Goal), F-02 + F-15 (PlanVersion with parallel/branch/dependency
semantics), immutability-once-stored, and JSON round-trip via
``to_dict``/``from_dict``.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from conftest import hard_dep, make_goal, make_plan, make_task
from planner_critic.schema.goal import Budget, Goal, ReplanPolicy, RiskTolerance
from planner_critic.schema.plan import (
    Branch,
    BranchKind,
    DependencyKind,
    PlanVersion,
    RiskClass,
    VerificationStep,
)


class TestGoalSchema:
    """Goal model construction and validation."""

    def test_minimal_goal_defaults(self) -> None:
        """A goal needs only id + description; the rest has sane defaults."""
        goal = Goal(id="g1", description="ship feature")
        assert goal.risk_tolerance is RiskTolerance.BALANCED
        assert goal.replan_policy is ReplanPolicy.PATCH
        assert goal.approval_ttl is None
        assert goal.constraints.budget == Budget()
        assert goal.metadata == {}

    def test_bad_enum_raises(self) -> None:
        """Unknown enum values must fail type validation."""
        with pytest.raises(ValidationError):
            Goal.model_validate({"id": "g1", "description": "x", "risk_tolerance": "whatever"})

    def test_blank_description_rejected(self) -> None:
        """A whitespace-only description plans nothing and must be rejected."""
        with pytest.raises(ValidationError):
            Goal(id="g1", description="   ")

    def test_strict_tolerance_accepted(self) -> None:
        """strict is a valid tolerance."""
        goal = Goal(id="g1", description="x", risk_tolerance=RiskTolerance.STRICT)
        assert goal.risk_tolerance is RiskTolerance.STRICT

    def test_budget_bounds_negative_rejected(self) -> None:
        """Negative spend ceilings fail validation."""
        with pytest.raises(ValidationError):
            Budget(max_tokens=-1)

    def test_goal_frozen(self) -> None:
        """A goal is immutable after construction."""
        goal = make_goal()
        with pytest.raises(ValidationError):
            goal.description = "mutated"


class TestPlanSchema:
    """PlanVersion construction, graph invariants, round-trip."""

    def test_plan_defaults(self) -> None:
        """A plan version carries schema version, version, and immutability."""
        plan = make_plan()
        assert plan.plan_schema_version == "0.1.0"
        assert plan.version == 1
        assert plan.parent_version is None
        assert len(plan.tasks) == 1

    def test_duplicate_task_ids_rejected(self) -> None:
        """Two tasks may not share an id."""
        with pytest.raises(ValidationError):
            make_plan(tasks=[make_task("t1"), make_task("t1")])

    def test_dependency_unknown_task_rejected(self) -> None:
        """Dependencies must reference existing tasks."""
        with pytest.raises(ValidationError):
            make_plan(dependencies=[hard_dep("t1", "ghost")])

    def test_self_dependency_rejected(self) -> None:
        """A task cannot depend on itself."""
        with pytest.raises(ValidationError):
            make_plan(dependencies=[hard_dep("t1", "t1")])

    def test_branch_unknown_task_rejected(self) -> None:
        """Branch members must exist as tasks."""
        with pytest.raises(ValidationError):
            make_plan(branches=[Branch(id="b1", kind=BranchKind.FAN_OUT, tasks=["ghost"])])

    def test_hard_dependency_inside_parallel_group_rejected(self) -> None:
        """Parallel-group members cannot have a hard edge between them."""
        with pytest.raises(ValidationError):
            make_plan(
                tasks=[
                    make_task("t1", parallel_group="g1"),
                    make_task("t2", parallel_group="g1"),
                ],
                dependencies=[hard_dep("t1", "t2")],
            )

    def test_soft_dependency_inside_parallel_group_allowed(self) -> None:
        """A *soft* dependency inside a parallel group is advisory, not a cycle."""
        soft = hard_dep("t1", "t2").model_copy(update={"kind": DependencyKind.SOFT})
        plan = make_plan(
            tasks=[
                make_task("t1", parallel_group="g1"),
                make_task("t2", parallel_group="g1"),
            ],
            dependencies=[soft],
        )
        assert len(plan.tasks) == 2

    def test_join_mode_validation(self) -> None:
        """Unknown join mode fails validation."""
        with pytest.raises(ValidationError):
            make_plan(
                branches=[
                    Branch(
                        id="b1",
                        kind=BranchKind.FAN_IN,
                        tasks=["t1"],
                        join="nope",  # type: ignore[arg-type]
                    )
                ]
            )

    def test_json_round_trip(self) -> None:
        """to_dict/from_dict must preserve the plan losslessly."""
        plan = make_plan(
            tasks=[
                make_task(
                    "t2",
                    risk_class="high",
                    blast_radius="high",
                    verification={"what": "x", "how": "y", "expected": "z"},
                ),
                make_task("t1", risk_class="low"),
            ],
            dependencies=[hard_dep("t1", "t2")],
            branches=[Branch(id="b1", kind=BranchKind.FAN_OUT, tasks=["t1", "t2"])],
        )
        restored = PlanVersion.from_dict(plan.to_dict())
        assert restored == plan
        assert restored.tasks[0].risk_class is RiskClass.HIGH

    def test_plan_immutable_once_stored(self) -> None:
        """A PlanVersion cannot be mutated after construction."""
        plan = make_plan()
        with pytest.raises(ValidationError):
            plan.version = 99

    def test_created_at_required_and_preserved(self) -> None:
        """created_at survives round-trip (is not silently reset)."""
        plan = make_plan()
        restored = PlanVersion.from_dict(plan.to_dict())
        assert restored.created_at == plan.created_at
        assert restored.created_at.tzinfo is not None


class TestTaskSchema:
    """Task field semantics."""

    def test_verification_step_fields(self) -> None:
        """Verification carries what/how/expected."""
        step = VerificationStep(what="reachable", how="curl", expected="200")
        assert step.expected == "200"

    def test_high_and_low_risk_class(self) -> None:
        """RiskClass.is_high_risk is True only for high/critical."""
        assert RiskClass.HIGH.is_high_risk
        assert RiskClass.CRITICAL.is_high_risk
        assert not RiskClass.LOW.is_high_risk
        assert not RiskClass.MEDIUM.is_high_risk

    def test_parallel_group_storage(self) -> None:
        """parallel_group is preserved on the task."""
        task = make_task("t1", parallel_group="pg")
        assert task.parallel_group == "pg"
        assert make_task("t2").parallel_group is None


class TestRollbackStepLenientCoercion:
    """``restores_state`` leniently accepts LLM-produced strings (L-1)."""

    def test_string_coerced_to_single_element_list(self) -> None:
        """A bare string is wrapped into ``[str]`` so LLM plans validate."""
        from planner_critic.schema.plan import RollbackStep

        rb = RollbackStep.model_validate(
            {"trigger": "fail", "action": "revert", "restores_state": "restore db"}
        )
        assert rb.restores_state == ["restore db"]

    def test_list_passthrough(self) -> None:
        """A proper list is unchanged."""
        from planner_critic.schema.plan import RollbackStep

        rb = RollbackStep(trigger="fail", action="revert", restores_state=["a", "b"])
        assert rb.restores_state == ["a", "b"]

    def test_none_unchanged(self) -> None:
        """``None`` (legacy prose rollback) stays ``None``."""
        from planner_critic.schema.plan import RollbackStep

        rb = RollbackStep(trigger="fail", action="revert")
        assert rb.restores_state is None
