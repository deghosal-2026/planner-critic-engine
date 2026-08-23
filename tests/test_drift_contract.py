"""Drift-metric blind-spot contract tests (#231).

kenielzep97's distinction: ``drift.py`` measures critic-vs-guardrail
disagreement (needs raw ≠ normalized); the seeded runner measures
critic-vs-reality (needs ground truth). A critic that misclassifies family
AND severity at origin produces raw == normalized — zero drift, zero
underclaims — so a bare zero on ``critical_underclaims`` must never be
readable as a clean bill. The interpretation travels with the number.
"""

from __future__ import annotations

from planner_critic.loop.histogram import detect_histogram_cycling  # noqa: F401  (sibling module)
from planner_critic.types import Finding, HeuristicFamily, Severity


def _origin_misclassified() -> Finding:
    """Real safety defect filed as advisory family + warning severity at origin."""
    return Finding(
        id="w-origin",
        task_id="t1",
        version=1,
        severity=Severity.WARNING,
        reason_code="llm_risk",
        message="could also consider rollback completeness",
        heuristic_family=HeuristicFamily.MISSING_STEPS,
    )


class TestDriftSummaryContract:
    def test_interpretation_key_present(self) -> None:
        from planner_critic.drift import compute_drift_summary

        summary = compute_drift_summary([_origin_misclassified()])
        assert "critical_underclaims_interpretation" in summary

    def test_zero_underclaims_carries_caveat_not_clean_bill(self) -> None:
        from planner_critic.drift import compute_drift_summary

        summary = compute_drift_summary([_origin_misclassified()])
        assert summary["critical_underclaims"] == 0
        caveat = str(summary["critical_underclaims_interpretation"])
        assert "guardrail never overrode" in caveat
        assert "live boundary runner" in caveat.lower() or "live-critic" in caveat.lower()

    def test_origin_misclassification_is_invisible_to_drift(self) -> None:
        """Pins the blind spot itself: raw == normalized means nothing drifts."""
        from planner_critic.drift import compute_drift_summary

        summary = compute_drift_summary([_origin_misclassified()])
        assert summary["drifted_count"] == 0
        assert summary["downgrade_rate"] == 0.0


class TestLiveBoundaryPairingDocstring:
    def test_runner_docstring_names_the_pairing(self) -> None:
        import planner_critic.eval.live_boundary as lb

        doc = lb.__doc__ or ""
        assert (
            "critic-vs-guardrail" in doc.lower().replace(" ", "-")
            or "critic vs guardrail" in doc.lower()
        )
        assert "critic-vs-reality" in doc.lower().replace(" ", "-") or (
            "critic vs reality" in doc.lower()
        )
