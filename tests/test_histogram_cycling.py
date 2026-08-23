"""Family-histogram cycling detection tests (#217).

The stall-signal matrix: F-06 catches identical text, #152 catches structural
cycling, #183 benchmarks stasis (frozen histogram). This module pins the
missing quadrant — the blocker-family histogram *cycles* (A→B→A→B): every
consecutive comparison sees change, no structural signature repeats, yet the
planner is reshuffling between two defective shapes.

Orthogonality contract pinned here: a pure-LLM cycler trips
``family_histogram_cycling`` while regression (F-07), convergence (F-06),
and structural oscillation (#152) all stay silent on the same trace.
"""

from __future__ import annotations

from planner_critic.loop.histogram import (
    compute_family_histogram,
    detect_histogram_cycling,
)
from planner_critic.reason_codes import (
    FAMILY_HISTOGRAM_CYCLING,
)
from planner_critic.types import Finding, HeuristicFamily, Severity


def _llm_blocker(family: HeuristicFamily, task_id: str = "t1") -> Finding:
    """Blocker finding in an LLM heuristic family."""
    return Finding(
        id=f"f:{task_id}:{family.value}",
        task_id=task_id,
        version=1,
        severity=Severity.BLOCKER,
        reason_code="llm_weak_rollback" if family is HeuristicFamily.WEAK_ROLLBACK else "llm_risk",
        message="x",
        heuristic_family=family,
    )


def _hist(*families: HeuristicFamily) -> tuple:
    """Canonical histogram for one revision from its family multiset."""
    return compute_family_histogram([_llm_blocker(f) for f in families])


class TestComputeFamilyHistogram:
    def test_counts_blocker_families(self) -> None:
        h = compute_family_histogram(
            [_llm_blocker(HeuristicFamily.RISK), _llm_blocker(HeuristicFamily.RISK),
             _llm_blocker(HeuristicFamily.MISSING_STEPS)]
        )
        assert h == (("missing_steps", 1), ("risk", 2))

    def test_excludes_warnings_and_gate_findings(self) -> None:
        warning = Finding(
            id="w", version=1, severity=Severity.WARNING,
            reason_code="llm_risk", message="x", heuristic_family=HeuristicFamily.RISK,
        )
        gate = Finding(
            id="g", version=1, severity=Severity.BLOCKER,
            reason_code="unsafe_ordering", message="x",
        )
        assert compute_family_histogram([warning, gate]) == ()

    def test_empty_is_canonical_empty(self) -> None:
        assert compute_family_histogram([]) == ()


class TestDetectHistogramCycling:
    def test_period_two_cycle_fires(self) -> None:
        a, b = _hist(HeuristicFamily.RISK), _hist(HeuristicFamily.MISSING_STEPS)
        assert detect_histogram_cycling([a, b, a, b], max_lag=2) is True

    def test_cycle_fires_at_minimum_history(self) -> None:
        a, b = _hist(HeuristicFamily.RISK), _hist(HeuristicFamily.MISSING_STEPS)
        assert detect_histogram_cycling([a, b, a], max_lag=2) is True

    def test_constant_histogram_is_not_cycling(self) -> None:
        """Identical consecutive histograms are stasis territory, not cycling."""
        a = _hist(HeuristicFamily.RISK)
        assert detect_histogram_cycling([a, a, a], max_lag=2) is False

    def test_genuine_progress_does_not_fire(self) -> None:
        """Every revision a new shape, never repeating — no cycle."""
        a = _hist(HeuristicFamily.RISK)
        b = _hist(HeuristicFamily.MISSING_STEPS)
        c = _hist(HeuristicFamily.WEAK_ROLLBACK)
        d = _hist(HeuristicFamily.FEASIBILITY)
        assert detect_histogram_cycling([a, b, c, d], max_lag=2) is False

    def test_insufficient_history(self) -> None:
        a, b = _hist(HeuristicFamily.RISK), _hist(HeuristicFamily.MISSING_STEPS)
        assert detect_histogram_cycling([a, b], max_lag=2) is False

    def test_respects_max_lag(self) -> None:
        """Period-3 repeat only fires when max_lag reaches 3."""
        a, b, c = (_hist(HeuristicFamily.RISK), _hist(HeuristicFamily.MISSING_STEPS),
                   _hist(HeuristicFamily.WEAK_ROLLBACK))
        assert detect_histogram_cycling([a, b, c, a], max_lag=2) is False
        assert detect_histogram_cycling([a, b, c, a], max_lag=3) is True


class TestReasonCodeCatalog:
    def test_code_registered(self) -> None:
        from planner_critic.reason_codes import REASON_CODE_DESCRIPTIONS

        assert FAMILY_HISTOGRAM_CYCLING in REASON_CODE_DESCRIPTIONS


class TestControllerIntegration:
    def test_pure_llm_cycler_escalates_with_cycling_code(self) -> None:
        """Alternating LLM-family mixes over distinct structures trips ONLY this signal."""
        from conftest import ScriptedCritic, ScriptedPlanner, make_goal, make_plan, make_task
        from planner_critic.loop import LoopConfig, run_loop
        from planner_critic.schema.goal import RiskTolerance

        plans = []
        for i in range(6):
            tasks = [make_task(f"t{j}", verification={"what": "x", "how": "y", "expected": "z"})
                     for j in range(1, i + 3)]
            plans.append(make_plan(plan_id=f"plan-{i}", tasks=tasks))

        even = [_llm_blocker(HeuristicFamily.RISK)]
        odd = [_llm_blocker(HeuristicFamily.MISSING_STEPS)]
        critic = ScriptedCritic([even if i % 2 == 0 else odd for i in range(6)])

        result = run_loop(
            make_goal(tolerance=RiskTolerance.STRICT),
            ScriptedPlanner(plans),
            critic,
            config=LoopConfig(revision_cap=10, oscillation_window=4),
        )
        assert result.status == "escalated"
        assert result.reason_code == FAMILY_HISTOGRAM_CYCLING

    def test_structural_oscillation_takes_precedence_when_both(self) -> None:
        """Same shapes repeating structurally keep reporting #152, not this."""
        from conftest import ScriptedCritic, ScriptedPlanner, make_goal, make_plan, make_task
        from planner_critic.loop import LoopConfig, run_loop
        from planner_critic.schema.goal import RiskTolerance

        p0 = make_plan(plan_id="p0", tasks=[make_task("t1")])
        p1 = make_plan(plan_id="p1", tasks=[make_task("t1"), make_task("t2")])
        critic = ScriptedCritic([
            [_llm_blocker(HeuristicFamily.RISK)],
            [_llm_blocker(HeuristicFamily.MISSING_STEPS)],
            [_llm_blocker(HeuristicFamily.RISK)],
            [_llm_blocker(HeuristicFamily.MISSING_STEPS)],
        ])
        result = run_loop(
            make_goal(tolerance=RiskTolerance.STRICT),
            ScriptedPlanner([p0, p1, p0, p1]),
            critic,
            config=LoopConfig(revision_cap=10, oscillation_window=4),
        )
        assert result.reason_code == "plan_oscillation_detected"
