"""Live-critic boundary-case runner tests (#218).

The #171 boundary fixtures are deterministic — they validate gates and
normalization but never a live critic. This harness sends each boundary pair
through a critic role N times and reports the four community-review metrics:

* label flip rate — trial-to-trial verdict changes on identical input;
* family migration rate — seeded defects landing in advisory families;
* evidence drift rate — explanations claiming different facts per trial;
* underclaim approvals — defect plans with zero blockers (balanced would
  approve).

Tests use stub critics: hermetic by default, $0 LLM. A live run is the same
call with a registry-backed CriticRole.
"""

from __future__ import annotations

from typing import cast

from planner_critic.eval.label_migration import generate_boundary_cases
from planner_critic.eval.live_boundary import run_live_boundary_cases
from planner_critic.roles import CriticRole
from planner_critic.schema.plan import PlanVersion
from planner_critic.types import Finding, HeuristicFamily, Severity


class _SteadyCritic(CriticRole):
    """Always blocks plan_b-style defects in the expected family."""

    def audit(self, plan: PlanVersion, findings: list[Finding]) -> list[Finding]:
        return [
            Finding(
                id=f"{plan.id}:b1",
                task_id=plan.tasks[0].id,
                version=plan.version,
                severity=Severity.BLOCKER,
                reason_code="llm_weak_rollback",
                message="rollback names recovery that does not exist",
                heuristic_family=HeuristicFamily.WEAK_ROLLBACK,
            )
        ]


class _MigratingCritic(CriticRole):
    """Alternates advisory/defect verdicts across trials — flips + migration."""

    def __init__(self) -> None:
        self._n = 0

    def audit(self, plan: PlanVersion, findings: list[Finding]) -> list[Finding]:
        self._n += 1
        if self._n % 2 == 0:
            return [
                Finding(
                    id=f"{plan.id}:adv",
                    task_id=plan.tasks[0].id,
                    version=plan.version,
                    severity=Severity.WARNING,
                    reason_code="llm_risk",
                    message="could also consider latency during cutover",
                    heuristic_family=HeuristicFamily.RISK,
                )
            ]
        return _SteadyCritic().audit(plan, findings)


class TestRunLiveBoundaryCases:
    def test_steady_critic_zero_flips_zero_underclaims(self) -> None:
        report = run_live_boundary_cases(_SteadyCritic(), trials=3)
        assert report["trials_per_plan"] == 3
        assert report["label_flip_rate"] == 0.0
        assert report["underclaim_approvals"] == 0

    def test_migrating_critic_detects_flips_and_underclaims(self) -> None:
        report = run_live_boundary_cases(_MigratingCritic(), trials=4)
        assert cast("float", report["label_flip_rate"]) > 0.0
        assert cast("int", report["underclaim_approvals"]) > 0

    def test_evidence_drift_captured_from_explanations(self) -> None:
        class DriftingCritic(_SteadyCritic):
            """Invents a different missing fact every trial."""

            def __init__(self) -> None:
                self._n = 0

            def audit(self, plan: PlanVersion, findings: list[Finding]) -> list[Finding]:
                self._n += 1
                base = _SteadyCritic.audit(self, plan, findings)
                return [base[0].model_copy(update={"message": f"missing fact v{self._n}"})]

        report = run_live_boundary_cases(DriftingCritic(), trials=3)
        assert report["evidence_drift_rate"] == 1.0

    def test_dry_run_stub_matches_critic_role_interface(self) -> None:
        """Any CriticRole works — dry-run is just a scripted critic."""
        cases = generate_boundary_cases()
        assert len(cases) >= 3  # optional-step, rollback pair, verification twin
        report = run_live_boundary_cases(_SteadyCritic(), cases=cases, trials=1)
        assert report["cases_evaluated"] == len(cases)

    def test_report_shape_has_all_four_metrics(self) -> None:
        report = run_live_boundary_cases(_SteadyCritic(), trials=2)
        for key in (
            "label_flip_rate",
            "family_migration_rate",
            "evidence_drift_rate",
            "underclaim_approvals",
            "cases_evaluated",
            "trials_per_plan",
        ):
            assert key in report
