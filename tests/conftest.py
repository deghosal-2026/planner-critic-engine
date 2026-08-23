"""Shared fixtures: goal/plan builders and fake role implementations.

Fake roles let the loop run end-to-end with zero LLM and zero network — the
determinism CI contract depends on them being pure functions of their input.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

import pytest

from planner_critic.reason_codes import ReasonCode
from planner_critic.roles import CriticRole, PlannerRole
from planner_critic.schema.goal import Goal, ReplanPolicy, RiskTolerance
from planner_critic.schema.plan import (
    Branch,
    Dependency,
    DependencyKind,
    PlanVersion,
    Task,
)
from planner_critic.types import Finding, Severity


def make_goal(
    goal_id: str = "goal-1",
    tolerance: RiskTolerance = RiskTolerance.BALANCED,
    description: str = "Migrate service X to the new auth provider",
    replan_policy: ReplanPolicy | None = None,
) -> Goal:
    """Build a minimal valid goal with deterministic defaults."""
    goal = Goal(id=goal_id, description=description, risk_tolerance=tolerance)
    if replan_policy is not None:
        goal = goal.model_copy(update={"replan_policy": replan_policy})
    return goal


def make_task(
    task_id: str,
    *,
    action: str = "do",
    target: str | None = None,
    risk_class: str = "medium",
    blast_radius: str = "medium",
    verification: dict[str, object] | None = None,
    rollback: dict[str, object] | None = None,
    parallel_group: str | None = None,
    preconditions: list[dict[str, object]] | None = None,
) -> Task:
    """Build a task with explicit but convenient defaults."""
    return Task.model_validate(
        {
            "id": task_id,
            "description": f"task {task_id}",
            "action": action,
            "target": target if target is not None else task_id,
            "risk_class": risk_class,
            "blast_radius": blast_radius,
            "verification": verification,
            "rollback": rollback,
            "parallel_group": parallel_group,
            "preconditions": preconditions or [],
        }
    )


def make_plan(
    *,
    plan_id: str = "plan-1",
    goal_id: str = "goal-1",
    version: int = 1,
    parent: str | None = None,
    tasks: list[Task] | None = None,
    dependencies: list[Dependency] | None = None,
    branches: list[Branch] | None = None,
    created_at: datetime | None = None,
) -> PlanVersion:
    """Build a valid plan with a default single medium-risk task."""
    if tasks is None:
        tasks = [make_task("t1")]
    if dependencies is None:
        dependencies = []
    return PlanVersion(
        id=plan_id,
        goal_id=goal_id,
        version=version,
        parent_version=parent,
        tasks=tasks,
        dependencies=dependencies,
        branches=branches or [],
        created_at=created_at or datetime(2026, 1, 1, tzinfo=UTC),
    )


def hard_dep(from_task: str, to_task: str) -> Dependency:
    """Build a hard dependency edge."""
    return Dependency(from_task=from_task, to_task=to_task, kind=DependencyKind.HARD, reason="test")


def finding(
    task_id: str | None,
    reason_code: str,
    severity: Severity = Severity.BLOCKER,
) -> Finding:
    """Build a finding for a fake critic."""
    return Finding(
        id=f"f:{task_id or 'plan'}:{reason_code}",
        task_id=task_id,
        version=1,
        severity=severity,
        reason_code=cast("ReasonCode", reason_code),
        message=reason_code,
    )


# A scripted draft: either a fixed plan, or a function of (plan, findings).
Draft = PlanVersion | Callable[[PlanVersion, list[Finding]], PlanVersion]


class ScriptedPlanner(PlannerRole):
    """Planner that returns canned plans by revision; determinism-friendly.

    ``drafts`` maps each call index to the plan (or plan-revising callable)
    the planner should return. Used by both unit tests and the matrix runner.
    """

    def __init__(self, drafts: list[Draft]) -> None:
        """Store the scripted drafts.

        Args:
            drafts: Per-call plans. The last entry repeats for further calls.
        """
        if not drafts:
            raise ValueError("ScriptedPlanner needs at least one draft")
        self.drafts = drafts
        self.calls = 0

    def decompose(self, goal: Goal) -> PlanVersion:
        """Return the first scripted draft."""
        return self._resolve(0, make_plan(goal_id=goal.id), [])

    def revise(self, plan: PlanVersion, findings: list[Finding]) -> PlanVersion:
        """Return the next scripted draft in sequence."""
        self.calls += 1
        index = min(self.calls, len(self.drafts) - 1)
        return self._resolve(index, plan, findings)

    def _resolve(self, index: int, plan: PlanVersion, findings: list[Finding]) -> PlanVersion:
        """Resolve a draft entry to a concrete plan."""
        entry = self.drafts[index]
        if isinstance(entry, PlanVersion):
            return entry
        return entry(plan, findings)


class ScriptedCritic(CriticRole):
    """Critic that returns canned findings per revision index."""

    def __init__(self, findings_by_revision: list[list[Finding]]) -> None:
        """Store the scripted findings.

        Args:
            findings_by_revision: Per-revision finding lists. The last entry
                repeats beyond the script length.
        """
        if not findings_by_revision:
            raise ValueError("ScriptedCritic needs at least one finding list")
        self.findings_by_revision = findings_by_revision
        self.calls = 0

    def audit(self, plan: PlanVersion, findings: list[Finding]) -> list[Finding]:
        """Return the canned findings for the next revision."""
        self.calls += 1
        index = min(self.calls - 1, len(self.findings_by_revision) - 1)
        return list(self.findings_by_revision[index])


class EmptyCritic(CriticRole):
    """Critic that finds nothing; approval is immediate when gates pass."""

    def audit(self, plan: PlanVersion, findings: list[Finding]) -> list[Finding]:
        """Return the gate findings unchanged (no new findings)."""
        return list(findings)


@pytest.fixture
def empty_critic() -> EmptyCritic:
    """A critic that never adds findings."""
    return EmptyCritic()
