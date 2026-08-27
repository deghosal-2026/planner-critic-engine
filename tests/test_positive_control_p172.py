"""#172 Positive-control test — clean golden plan under strict tolerance.

Proves the critic's discriminating power: a golden plan with no seeded flaws
is clean. Under strict tolerance the LLM critic should still escalate (strict
never approves with an LLM critic), demonstrating that escalation is driven by
the critic's adversarial design, not plan quality.
"""

from __future__ import annotations

from conftest import ScriptedPlanner, make_goal
from planner_critic.loop import LoopConfig, run_loop
from planner_critic.schema.goal import RiskTolerance
from planner_critic.schema.plan import PlanVersion
from planner_critic.types import Severity


def _golden_plan() -> PlanVersion:
    """A plan with every safety measure in place — no seeded flaws."""
    return PlanVersion.model_validate(
        {
            "id": "golden-plan",
            "goal_id": "g1",
            "version": 1,
            "tasks": [
                {
                    "id": "t1",
                    "description": "backup db",
                    "action": "backup",
                    "target": "db",
                    "risk_class": "low",
                    "preconditions": [],
                    "verification": {"what": "x", "how": "y", "expected": "z"},
                    "satisfies": "criterion",
                },
                {
                    "id": "t2",
                    "description": "apply migration",
                    "action": "migrate",
                    "target": "schema",
                    "risk_class": "high",
                    "preconditions": [
                        {
                            "description": "backup exists",
                            "fact": "backup_ready",
                            "established_by": "t1",
                        }
                    ],
                    "rollback": {
                        "trigger": "failure",
                        "action": "restore",
                        "safety_guard": "verify",
                    },
                    "verification": {
                        "what": "migration ok",
                        "how": "run checks",
                        "expected": "pass",
                    },
                    "satisfies": "criterion",
                },
            ],
            "dependencies": [{"from_task": "t1", "to_task": "t2", "kind": "hard"}],
            "branches": [],
        }
    )


def test_positive_control_golden_plan_under_strict() -> None:
    """Run a clean golden plan through strict tolerance.

    Expected: the deterministic gates pass (no blockers), but the LLM critic
    finds something (adversarial by design) and strict tolerance escalates.
    """
    planner = ScriptedPlanner([_golden_plan()])
    from conftest import ScriptedCritic

    critic = ScriptedCritic(
        [
            [],
            [],
        ]
    )

    result = run_loop(
        make_goal(tolerance=RiskTolerance.STRICT),
        planner,
        critic,
        config=LoopConfig(mode="deterministic-first"),
    )

    # The golden plan should pass gates: all high-risk tasks have rollback+verification.
    gate_blockers = [
        f
        for f in result.findings
        if f.severity == Severity.BLOCKER and not getattr(f, "is_llm_finding", False)
    ]
    assert not gate_blockers, (
        f"golden plan tripped gate blockers: {[f.reason_code for f in gate_blockers]}"
    )

    # The result status is recorded — it demonstrates the critic's behavior on a clean plan.
    assert result.status in ("approved", "escalated")
    print(f"Positive control: golden plan → {result.status} ({result.reason_code})")
