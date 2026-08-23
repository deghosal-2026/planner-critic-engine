"""Live-critic boundary-case runner (#218).

The #171 boundary fixtures are deterministic: they prove gates and
normalization behave, but they never exercise a real critic model. This
harness sends each boundary pair through any :class:`CriticRole` ``N`` times
per plan and reduces the trials to the four metrics community review asked
for (peterbuildssecure / kenielzep97 threads):

* **label_flip_rate** — share of (case, plan) groups whose verdict signature
  differs across trials of identical input;
* **family_migration_rate** — share of defect-plan (plan_b) trials where a
  defect was acknowledged only as advisory (no blocker, some warning): the
  seeded defect landed in an advisory family;
* **evidence_drift_rate** — share of (case, plan) groups whose explanation
  texts differ across trials — invented evidence a normalization layer
  cannot repair;
* **underclaim_approvals** — defect-plan trials with zero blockers at all,
  i.e. plans balanced tolerance would have approved.

**Measurement class (#231):** this harness measures *critic-vs-reality* —
seeded known defects judged against pre-registered expectations. Its
complement, :mod:`planner_critic.drift`, measures critic-vs-guardrail
disagreement (raw vs normalized severity). The two are paired, not
redundant: an origin misclassification (family AND severity wrong from the
start) is invisible to drift metrics, while a guardrail override is
invisible here. A zero on either alone is not a safety result; report them
together.

Dry-run/hermetic usage: pass any scripted :class:`CriticRole` (tests do).
A live run is the same call with a registry-backed critic; budget caps stay
with the caller's provider config.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..roles import CriticRole
from ..types import Finding, Severity
from .label_migration import BoundaryCase, generate_boundary_cases


def _verdict_signature(findings: list[Finding]) -> frozenset[tuple[str, str]]:
    """Trial verdict signature: {(family-or-code, severity), …}."""
    return frozenset(
        (str(f.heuristic_family) if f.heuristic_family else str(f.reason_code), str(f.severity))
        for f in findings
    )


def run_live_boundary_cases(
    critic: CriticRole,
    cases: Iterable[BoundaryCase] | None = None,
    trials: int = 5,
) -> dict[str, object]:
    """Run boundary pairs through a critic repeatedly and reduce metrics.

    Args:
        critic: The critic role under evaluation (stub for dry-run, registry-
            backed provider role for live runs).
        cases: Boundary cases to evaluate; defaults to the full #171 corpus.
        trials: Repetitions per plan (community-specified protocol).

    Returns:
        A JSON-ready report dict with per-metric aggregates plus per-case
        trial records (labels + explanations retained for audit).
    """
    if trials < 1:
        raise ValueError("trials must be >= 1")
    boundary_cases = list(cases) if cases is not None else generate_boundary_cases()

    label_flips = 0
    groups = 0
    drifts = 0
    plan_b_trials = 0
    migrated_trials = 0
    underclaim_approvals = 0
    case_records: list[dict[str, object]] = []

    for case in boundary_cases:
        plans_map: dict[str, object] = {}
        case_entry: dict[str, object] = {"case_id": case.case_id, "plans": plans_map}
        for role, plan in (("a", case.plan_a), ("b", case.plan_b)):
            trial_records = []
            signatures: set[frozenset[tuple[str, str]]] = set()
            explanation_signatures: set[frozenset[str]] = set()
            for trial in range(trials):
                try:
                    found = critic.audit(plan, [])
                except Exception as exc:
                    trial_records.append({"trial": trial, "error": f"{type(exc).__name__}: {exc}"})
                    continue
                signatures.add(_verdict_signature(found))
                # Drift measures cross-trial variation of the explanation set:
                # a deterministic multi-finding critic (intra-trial variety)
                # must not be scored as drift (#239). Pool the per-trial message
                # set as one signature and compare those signatures across trials.
                explanation_signatures.add(frozenset(f.message or "" for f in found))
                trial_records.append(
                    {
                        "trial": trial,
                        "verdicts": [
                            {
                                "family": str(f.heuristic_family)
                                if f.heuristic_family
                                else str(f.reason_code),
                                "severity": str(f.severity),
                                "explanation": f.message,
                            }
                            for f in found
                        ],
                    }
                )
                if role == "b":
                    plan_b_trials += 1
                    blockers = [f for f in found if f.severity is Severity.BLOCKER]
                    advisories = [f for f in found if f.severity is not Severity.BLOCKER]
                    if not blockers:
                        underclaim_approvals += 1
                        if advisories:
                            migrated_trials += 1

            groups += 1
            if len(signatures) > 1:
                label_flips += 1
            if len(explanation_signatures) > 1:
                drifts += 1

            plans_map[role] = {"trials": trial_records}
        case_records.append(case_entry)

    total_groups = groups if groups else 1
    return {
        "cases_evaluated": len(boundary_cases),
        "trials_per_plan": trials,
        "label_flip_rate": label_flips / total_groups,
        "family_migration_rate": (migrated_trials / plan_b_trials if plan_b_trials else 0.0),
        "evidence_drift_rate": drifts / total_groups,
        "underclaim_approvals": underclaim_approvals,
        "cases": case_records,
    }


__all__ = ["run_live_boundary_cases"]
