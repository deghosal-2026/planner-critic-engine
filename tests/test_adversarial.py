"""Injection-safety tests (F-04, F-12, §2.4): the gate beats the model.

An adversarial goal tries to suppress a deterministic gate blocker. The
property under test: a blocker from a deterministic gate can NEVER be
overridden by the LLM critic — the critic may be biased, but its "all clear"
output cannot clear a gate blocker. The gate is code, not model output.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from conftest import (
    ScriptedCritic,
    ScriptedPlanner,
    make_plan,
    make_task,
)
from planner_critic.loop import LoopConfig, run_loop
from planner_critic.schema.goal import Goal, RiskTolerance
from planner_critic.schema.plan import PlanVersion

FIXTURE = Path(__file__).parent / "fixtures" / "adversarial_goal.yaml"


def _fixture() -> dict:
    """Load the adversarial-goal fixture."""
    with FIXTURE.open() as fh:
        return yaml.safe_load(fh)


def _adversarial_goal() -> Goal:
    """Build the adversarial Goal from the fixture."""
    spec = _fixture()["adversarial_goal"]
    return Goal(
        id=spec["id"],
        description=spec["description"],
        risk_tolerance=RiskTolerance(spec["tolerance"]),
    )


def _gate_blocked_plan() -> PlanVersion:
    """The fixture's critical-risk plan with no safety steps (gate blocker)."""
    task_spec = _fixture()["plan"]["tasks"][0]
    return make_plan(
        plan_id=_fixture()["plan"]["plan_id"],
        tasks=[make_task(task_spec["id"], risk_class=task_spec["risk_class"])],
    )


def test_gate_blocker_survives_all_clear_critic() -> None:
    """A critic claiming 'no problems' cannot clear a deterministic blocker."""
    goal = _adversarial_goal()
    # The critic is adversarial: it returns NO findings (attempts to approve).
    result = run_loop(
        goal,
        ScriptedPlanner([_gate_blocked_plan()] * 3),
        ScriptedCritic([[], [], []]),
        config=LoopConfig(mode="llm-every-revision", revision_cap=3),
    )
    # Injection-safety: even with an all-clear LLM critic, the gate blocker
    # forces escalation — the plan can never be approved.
    assert result.status == "escalated"
    assert not result.is_approved
    # The gate blockers are still present in the findings.
    assert any(f.reason_code == "missing_verification" for f in result.findings)
    assert any(f.reason_code == "missing_rollback" for f in result.findings)


def test_gate_blocker_holds_in_deterministic_first() -> None:
    """In deterministic-first, the gate short-circuits before the LLM at all."""
    goal = _adversarial_goal()
    result = run_loop(
        goal,
        ScriptedPlanner([_gate_blocked_plan()] * 3),
        ScriptedCritic([[], [], []]),
        config=LoopConfig(mode="deterministic-first", revision_cap=3),
    )
    assert result.status == "escalated"
    assert not result.is_approved


def test_adversarial_critic_adding_blocker_still_escalates() -> None:
    """Even when the critic does NOT try to suppress, escalation holds."""
    goal = _adversarial_goal()
    result = run_loop(
        goal,
        ScriptedPlanner([_gate_blocked_plan()] * 3),
        ScriptedCritic([[], [], []]),
        config=LoopConfig(mode="heuristic-only", revision_cap=3),
    )
    # heuristic-only: gates are the only layer, and they still block.
    assert result.status == "escalated"
    assert not result.is_approved
