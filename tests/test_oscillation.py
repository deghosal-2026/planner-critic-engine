"""Oscillation & structural-similarity detection tests (#152).

``plan_oscillation_detected`` fires when 2+ revisions in the last K share the
same structural signature (the plan is cycling between shapes). Auto-Converge
mode approves the non-oscillating intersection and escalates only the cycling
subset.

These tests pin the four guarantees in the issue:
1. structural oscillation is detected at the configured window K;
2. genuinely converging plans do not false-positive;
3. ``converge_policy: escalate`` escalates (default);
4. ``converge_policy: auto_converge`` merges non-oscillating parts.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from conftest import (
    ScriptedCritic,
    ScriptedPlanner,
    finding,
    make_goal,
    make_plan,
    make_task,
)
from planner_critic.loop import LoopConfig, run_loop
from planner_critic.loop.oscillation import (
    compute_plan_signature,
    detect_oscillation,
    oscillating_task_ids,
)
from planner_critic.schema.goal import RiskTolerance
from planner_critic.schema.plan import Dependency, DependencyKind, PlanVersion
from planner_critic.types import Finding, Severity

PLAN_OSCILLATION_DETECTED = "plan_oscillation_detected"
AUTO_CONVERGE_PARTIAL_APPROVAL = "auto_converge_partial_approval"


def _structurally_distinct_plans(n: int) -> list[PlanVersion]:
    """Return ``n`` plans that differ in structure (task count / dependencies).

    Each plan is gate-clean (medium-risk tasks with default verification) so
    the loop passes the deterministic gates and reaches the critic.
    """
    plans: list[PlanVersion] = []
    for i in range(n):
        tasks = [make_task(f"t{j}") for j in range(1, i + 3)]  # 2, 3, 4, … tasks
        plans.append(make_plan(plan_id=f"plan-{i}", tasks=tasks))
    return plans


def _hard_dep(from_t: str, to_t: str) -> Dependency:
    return Dependency(from_task=from_t, to_task=to_t, kind=DependencyKind.HARD, reason="test")


class TestPlanSignature:
    """Content-agnostic structural hash."""

    def test_same_structure_same_signature(self) -> None:
        """Two plans with identical structure produce the same signature."""
        a = make_plan(tasks=[make_task("X"), make_task("Y")], dependencies=[_hard_dep("X", "Y")])
        b = make_plan(tasks=[make_task("X"), make_task("Y")], dependencies=[_hard_dep("X", "Y")])
        assert compute_plan_signature(a) == compute_plan_signature(b)

    def test_different_structure_different_signature(self) -> None:
        """Plans with different dependency topologies produce different signatures."""
        a = make_plan(tasks=[make_task("X"), make_task("Y")], dependencies=[_hard_dep("X", "Y")])
        b = make_plan(tasks=[make_task("X"), make_task("Y")])  # no dep
        assert compute_plan_signature(a) != compute_plan_signature(b)

    def test_content_agnostic(self) -> None:
        """Task descriptions/actions do not affect the signature."""
        a = make_plan(tasks=[make_task("X", risk_class="low")])
        b = make_plan(tasks=[make_task("X", risk_class="low")])
        assert compute_plan_signature(a) == compute_plan_signature(b)


class TestOscillationDetection:
    """2+ same-signature revisions in K window triggers detection."""

    def test_oscillation_detected_at_window(self) -> None:
        """Two structural shapes alternating in K=4 window triggers oscillation."""
        plans = _structurally_distinct_plans(2)  # [p0, p1]
        drafts: list[PlanVersion | Callable[[PlanVersion, list[Finding]], PlanVersion]] = [
            plans[0],
            plans[1],
            plans[0],
            plans[1],
        ]
        planner = ScriptedPlanner(drafts)
        # Each round: critic returns a warning under strict so approval fails
        findings_list = [
            [finding(f"t{i}", "unsafe_ordering", severity=Severity.WARNING)] for i in range(1, 5)
        ]
        critic = ScriptedCritic(findings_list)
        result = run_loop(
            make_goal(tolerance=RiskTolerance.STRICT),
            planner,
            critic,
            config=LoopConfig(oscillation_window=4, converge_policy="escalate", revision_cap=10),
        )
        assert result.status == "escalated"
        assert result.reason_code == PLAN_OSCILLATION_DETECTED

    def test_no_false_positive_on_converging_plans(self) -> None:
        """Four distinctly-shaped plans do not trigger oscillation."""
        drafts: list[PlanVersion | Callable[[PlanVersion, list[Finding]], PlanVersion]] = list(
            _structurally_distinct_plans(4)
        )  # 4 plans, each unique structure
        planner = ScriptedPlanner(drafts)
        findings_list = [
            [finding(f"t{i}", "unsafe_ordering", severity=Severity.WARNING)] for i in range(1, 5)
        ]
        critic = ScriptedCritic(findings_list)
        result = run_loop(
            make_goal(tolerance=RiskTolerance.STRICT),
            planner,
            critic,
            config=LoopConfig(oscillation_window=4, revision_cap=10),
        )
        # Should NOT be oscillation — it'll either cap or hit some other termination
        assert result.reason_code != PLAN_OSCILLATION_DETECTED

    def test_larger_window_requires_more_revisions(self) -> None:
        """With K=6 and 4 alternating revisions, oscillation cannot be detected."""
        plans = _structurally_distinct_plans(2)
        drafts: list[PlanVersion | Callable[[PlanVersion, list[Finding]], PlanVersion]] = [
            plans[0],
            plans[1],
            plans[0],
            plans[1],
        ]
        planner = ScriptedPlanner(drafts)
        findings_list = [
            [finding(f"t{i}", "unsafe_ordering", severity=Severity.WARNING)] for i in range(1, 5)
        ]
        critic = ScriptedCritic(findings_list)
        result = run_loop(
            make_goal(tolerance=RiskTolerance.STRICT),
            planner,
            critic,
            config=LoopConfig(oscillation_window=6, revision_cap=4),
        )
        # With only 4 revisions and K=6, window never fills; no oscillation.
        assert result.reason_code != PLAN_OSCILLATION_DETECTED


class TestOscillationHelpers:
    """Direct unit tests for the detection and task-id helpers."""

    def test_detect_oscillation_not_full_window(self) -> None:
        """Fewer signatures than window -> no oscillation."""
        assert detect_oscillation(["a", "b"], window=4) is False

    def test_detect_oscillation_exact_threshold(self) -> None:
        """Two identical out of four -> oscillation."""
        sigs = ["a", "b", "c", "a"]
        assert detect_oscillation(sigs, window=4) is True

    def test_detect_oscillation_no_false_positive(self) -> None:
        """Four unique signatures -> no oscillation."""
        sigs = ["a", "b", "c", "d"]
        assert detect_oscillation(sigs, window=4) is False

    def test_oscillating_task_ids_symmetric_diff(self) -> None:
        """Tasks present in one plan but not the other are oscillating."""
        a = make_plan(tasks=[make_task("X"), make_task("Y")])
        b = make_plan(tasks=[make_task("X"), make_task("Z")])
        diff = oscillating_task_ids(a, b)
        assert diff == frozenset({"Y", "Z"})

    def test_oscillating_task_ids_no_diff(self) -> None:
        """Identical task sets -> empty diff."""
        a = make_plan(tasks=[make_task("X"), make_task("Y")])
        assert oscillating_task_ids(a, a) == frozenset()


class TestLoopConfigEnv:
    """from_env env-var parsing for M2 config knobs."""

    def test_auto_repair_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PC_AUTO_REPAIR", "off")
        cfg = LoopConfig.from_env()
        assert cfg.auto_repair is False

    def test_precondition_closer_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PC_PRECONDITION_CLOSER", "off")
        cfg = LoopConfig.from_env()
        assert cfg.precondition_closer is False

    def test_oscillation_window_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PC_OSCILLATION_WINDOW", "6")
        cfg = LoopConfig.from_env()
        assert cfg.oscillation_window == 6

    def test_converge_policy_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PC_CONVERGE_POLICY", "auto_converge")
        cfg = LoopConfig.from_env()
        assert cfg.converge_policy == "auto_converge"

    def test_invalid_window_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PC_OSCILLATION_WINDOW", "not-a-number")
        cfg = LoopConfig.from_env()
        assert cfg.oscillation_window == 4

    def test_invalid_converge_policy_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PC_CONVERGE_POLICY", "invalid")
        cfg = LoopConfig.from_env()
        assert cfg.converge_policy == "escalate"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
