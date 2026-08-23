"""End-to-end loop tests with the real LLMCritic on fake providers (F-05, F-10).

The full arc — plan → gates → LLM critique → revise → approve/escalate — run
against a fake provider returning structured critique JSON. Unlike the
acceptance matrix (ScriptedCritic), these tests exercise the actual
:class:`LLMCritic` through the loop, in each critique mode, with zero network.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from conftest import (
    ScriptedPlanner,
    make_goal,
    make_plan,
    make_task,
)
from planner_critic.critique.critic import LLMCritic
from planner_critic.llm.base import Completion, Message, ToolSchema
from planner_critic.loop import LoopConfig, run_loop
from planner_critic.reason_codes import BUDGET_EXCEEDED, REVISION_CAP_REACHED
from planner_critic.schema.goal import Budget, Constraints, Goal, RiskTolerance
from planner_critic.schema.plan import PlanVersion


class FakeCriticProvider:
    """A fake provider returning a fixed critique payload."""

    name = "e2e-fake"
    base_url = "http://fake.local"
    model = "fake"

    def __init__(self, content: str) -> None:
        """Store the canned completion."""
        self.content = content
        self.calls = 0

    def complete(
        self,
        messages: Sequence[Message],
        tool_schemas: Sequence[ToolSchema] = (),
    ) -> Completion:
        """Return the canned completion and count calls."""
        self.calls += 1
        return Completion(content=self.content, finish_reason="stop")


def _clean_plan() -> PlanVersion:
    """A gate-clean, approval-ready plan."""
    return make_plan(
        tasks=[
            make_task(
                "t1",
                risk_class="low",
                verification={"what": "x", "how": "y", "expected": "z"},
            )
        ]
    )


def _dirty_plan() -> PlanVersion:
    """A gate-blocking plan: critical-risk task with no safety steps."""
    return make_plan(tasks=[make_task("t1", risk_class="critical")])


def _finding_json(family: str, severity: str, task_id: str, message: str) -> str:
    """A one-finding critique payload."""
    return json.dumps(
        {
            "findings": [
                {
                    "heuristic_family": family,
                    "severity": severity,
                    "task_id": task_id,
                    "message": message,
                }
            ]
        }
    )


def test_e2e_approve_with_real_llm_critic() -> None:
    """Full approve arc: gates pass, critic says clean, plan approved."""
    goal = make_goal()
    provider = FakeCriticProvider('{"findings": []}')
    critic = LLMCritic(goal=goal, provider=provider)
    result = run_loop(goal, ScriptedPlanner([_clean_plan()]), critic)
    assert result.is_approved
    assert result.approved_plan is not None
    assert provider.calls == 1


def test_e2e_critic_blocker_escalates() -> None:
    """A heuristic blocker from the LLM critic forces escalation."""
    goal = make_goal(tolerance=RiskTolerance.STRICT)
    provider = FakeCriticProvider(
        _finding_json("risk", "blocker", "t1", "deletes prod with no canary")
    )
    critic = LLMCritic(goal=goal, provider=provider)
    result = run_loop(
        goal,
        ScriptedPlanner([_clean_plan()] * 3),
        critic,
        config=LoopConfig(mode="llm-every-revision", revision_cap=3),
    )
    assert result.status == "escalated"
    assert not result.is_approved
    assert any(f.reason_code == "llm_risk" for f in result.findings)


def test_e2e_deterministic_first_gate_blocker_skips_llm() -> None:
    """A gate blocker in deterministic-first never spends the LLM."""
    goal = make_goal()
    provider = FakeCriticProvider('{"findings": []}')
    critic = LLMCritic(goal=goal, provider=provider)
    result = run_loop(
        goal,
        ScriptedPlanner([_dirty_plan()]),
        critic,
        config=LoopConfig(mode="deterministic-first"),
    )
    # gate blocker → revise path, LLM never invoked on the dead draft
    assert result.status in ("approved", "escalated")
    assert provider.calls == 0  # deterministic-first short-circuit


def test_e2e_heuristic_only_never_invokes_llm() -> None:
    """heuristic-only mode approves via gates alone, zero LLM calls."""
    goal = make_goal()
    provider = FakeCriticProvider('{"findings": []}')
    critic = LLMCritic(goal=goal, provider=provider)
    result = run_loop(
        goal,
        ScriptedPlanner([_clean_plan()]),
        critic,
        config=LoopConfig(mode="heuristic-only"),
    )
    assert result.is_approved
    assert provider.calls == 0


def test_e2e_tight_budget_escalates_before_approve() -> None:
    """A tight budget escalates before approving in LLM modes."""
    goal = Goal(
        id="g-budget-e2e",
        description="budget-bound goal",
        constraints=Constraints(budget=Budget(max_revisions=1)),
        risk_tolerance=RiskTolerance.STRICT,
    )
    provider = FakeCriticProvider(
        _finding_json("risk", "blocker", "t1", "deletes prod with no canary")
    )
    critic = LLMCritic(goal=goal, provider=provider)
    result = run_loop(
        goal,
        ScriptedPlanner([_clean_plan()]),
        critic,
        config=LoopConfig(mode="llm-every-revision", revision_cap=3),
    )
    assert result.status == "escalated"
    assert result.reason_code == BUDGET_EXCEEDED


def test_e2e_cap_escalates_with_pending_warnings() -> None:
    """Pending warnings under strict tolerance escalate at the revision cap."""
    goal = make_goal(tolerance=RiskTolerance.STRICT)

    class DistinctProvider(FakeCriticProvider):
        """Return a warning against a distinct task per call (avoid stall)."""

        def complete(
            self,
            messages: Sequence[Message],
            tool_schemas: Sequence[ToolSchema] = (),
        ) -> Completion:
            self.calls += 1
            return Completion(
                content=_finding_json(
                    "missing_steps", "warning", f"t{self.calls}", "no compat check"
                ),
                finish_reason="stop",
            )

    # Distinct plans per revision (different task ids) keep the structural
    # fingerprint changing, so the loop reaches cap instead of firing the
    # near-zero-diff stall detector.
    planner = ScriptedPlanner(
        [
            make_plan(plan_id="plan-cap-1", tasks=[make_task("ta")]),
            make_plan(plan_id="plan-cap-2", tasks=[make_task("tb")]),
            make_plan(plan_id="plan-cap-3", tasks=[make_task("tc")]),
        ]
    )

    critic = LLMCritic(goal=goal, provider=DistinctProvider("{}"))
    result = run_loop(
        goal,
        planner,
        critic,
        config=LoopConfig(mode="llm-every-revision", revision_cap=3),
    )
    assert result.status == "escalated"
    assert result.reason_code == REVISION_CAP_REACHED


def test_e2e_all_termination_paths_are_reachable() -> None:
    """Approved / cap-escalated / budget-escalated all terminate."""
    paths = 0
    # approve
    r1 = run_loop(
        make_goal(),
        ScriptedPlanner([_clean_plan()]),
        LLMCritic(make_goal(), FakeCriticProvider('{"findings": []}')),
    )
    if r1.is_approved:
        paths += 1
    # cap
    r2 = run_loop(
        make_goal(tolerance=RiskTolerance.STRICT),
        ScriptedPlanner([_clean_plan()] * 3),
        LLMCritic(
            make_goal(),
            FakeCriticProvider(_finding_json("risk", "blocker", "t1", "bad")),
        ),
        config=LoopConfig(mode="llm-every-revision", revision_cap=3),
    )
    if r2.status == "escalated":
        paths += 1
    # budget
    r3 = run_loop(
        Goal(
            id="g-budget-path",
            description="budget goal",
            constraints=Constraints(budget=Budget(max_revisions=1)),
            risk_tolerance=RiskTolerance.STRICT,
        ),
        ScriptedPlanner([_dirty_plan()] * 3),
        LLMCritic(make_goal(), FakeCriticProvider('{"findings": []}')),
        config=LoopConfig(mode="llm-every-revision"),
    )
    if r3.status == "escalated":
        paths += 1
    assert paths == 3
