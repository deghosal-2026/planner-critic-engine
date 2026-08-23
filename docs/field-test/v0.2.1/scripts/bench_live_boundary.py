"""Live-critic boundary-case benchmark (#218).

Sends the #171 boundary-corpus plan pairs through a **real critic model** N
times per plan and reduces the four community-review metrics:

* label_flip_rate — same plan, different family/severity verdicts across trials;
* family_migration_rate — seeded defects landing in advisory families;
* evidence_drift_rate — claimed facts/explanations varying across trials;
* underclaim_approvals — defect plans with zero blockers.

The harness itself is :func:`planner_critic.eval.live_boundary.run_live_boundary_cases`;
this script wires a registry/env-backed provider into it and commits the JSON +
markdown artifacts under ``results/0.2.1/``. Mirrors ``bench_cycling.py`` /
``bench_operational.py`` methodology. Spend ceiling: ≤ $1 at mini-class models
(~60 audits at 5 trials × 6 cases × 2 plans).

Usage::

    python3 docs/field-test/v0.2.1/scripts/bench_live_boundary.py            # live, 5 trials
    python3 docs/field-test/v0.2.1/scripts/bench_live_boundary.py --trials 3
    python3 docs/field-test/v0.2.1/scripts/bench_live_boundary.py --self-test  # hermetic, $0

Provider resolution order: a ``plancritic.toml`` registry ``critic`` role if
present; otherwise the ``LLM_BASE_URL`` / ``LLM_MODEL`` / ``LLM_API_KEY`` env
vars (the local-run default).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from planner_critic.eval.label_migration import generate_boundary_cases
from planner_critic.eval.live_boundary import run_live_boundary_cases
from planner_critic.schema.goal import Goal, RiskTolerance

SCRIPTS_DIR = Path(__file__).resolve().parent          # docs/field-test/v0.2.1/scripts
REPO_ROOT = SCRIPTS_DIR.parents[4]                      # repo root
RESULTS_DIR = REPO_ROOT / "results" / "0.2.1"

#: A generic migration goal giving the critic prompt context. The boundary
#: cases are all migration/rollback-flavored synthetic plans (goal_id="test");
#: one goal description covers them — the critic audits the *plan*, the goal
#: is framing only.
_BOUNDARY_GOAL = Goal(
    id="boundary-critic",
    description=(
        "Migrate a stateful service from a legacy platform to a new one with "
        "rollback safety, verified mutations, and correct task ordering."
    ),
    risk_tolerance=RiskTolerance.BALANCED,
)


class _StubCritic:
    """Hermetic stand-in for ``--self-test``: deterministic blocker on plan_b."""

    def audit(self, plan: Any, findings: list) -> list:  # noqa: ANN401
        from planner_critic.types import Finding, HeuristicFamily, Severity

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


def build_provider() -> tuple[Any, str]:
    """Resolve a live critic provider + a human-readable model label.

    Returns:
        (provider, model_label) where provider is an LLMProvider-ready object.

    Raises:
        RuntimeError: if no provider can be configured (no toml, no env).
    """
    from planner_critic.llm.registry import ProviderRegistry

    toml_path = REPO_ROOT / "plancritic.toml"
    if toml_path.exists():
        registry = ProviderRegistry.load(toml_path)
        if "critic" in registry.roles:
            spec = registry.providers[registry.roles["critic"]]
            return registry.get_provider("critic"), spec.model

    base_url = os.environ.get("LLM_BASE_URL", "").strip()
    model = os.environ.get("LLM_MODEL", "").strip()
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if not base_url or not model:
        raise RuntimeError(
            "no critic provider configured: create plancritic.toml or set "
            "LLM_BASE_URL + LLM_MODEL (+ LLM_API_KEY)"
        )

    from planner_critic.llm.transport_openai import OpenAICompatibleProvider

    return (
        OpenAICompatibleProvider(
            name="env-critic",
            base_url=base_url,
            model=model,
            api_key=api_key,
        ),
        model,
    )


def build_live_critic() -> tuple[Any, str]:
    """Build a live LLMCritic bound to the boundary goal + provider."""
    from planner_critic.critique.critic import LLMCritic

    provider, model = build_provider()
    return LLMCritic(_BOUNDARY_GOAL, provider), model


def _markdown_summary(report: dict, model: str, trials: int, elapsed_s: float) -> str:
    """Render a short markdown summary of the live run."""
    lines = [
        "# Live-critic boundary-case report — v0.2.1 (#218)",
        "",
        f"- **Model:** `{model}`",
        f"- **Trials per plan:** {trials}",
        f"- **Cases evaluated:** {report['cases_evaluated']}",
        f"- **Elapsed:** {elapsed_s:.1f}s",
        f"- **Estimated audits:** {report['cases_evaluated'] * trials * 2} "
        f"(cases × trials × 2 plans)",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| label_flip_rate | {report['label_flip_rate']:.3f} |",
        f"| family_migration_rate | {report['family_migration_rate']:.3f} |",
        f"| evidence_drift_rate | {report['evidence_drift_rate']:.3f} |",
        f"| underclaim_approvals | {report['underclaim_approvals']} |",
        "",
        "## Interpretation",
        "",
        "- `label_flip_rate > 0` → the critic is non-deterministic on identical input.",
        "- `family_migration_rate > 0` → seeded defects landed in advisory families "
        "(under-claim blind spot, F-13).",
        "- `evidence_drift_rate > 0` → claimed facts varied across trials (invented "
        "evidence; normalization cannot repair).",
        "- `underclaim_approvals > 0` → defect plans with zero blockers (balanced "
        "tolerance would have approved).",
        "",
        "Per-case × per-trial verdicts are in `live-boundary-report.json`.",
        "",
    ]
    return "\n".join(lines)


def run_boundary(critic: Any, *, trials: int = 5, model: str = "stub") -> dict:
    """Run the boundary cases through ``critic`` and write report artifacts.

    Args:
        critic: Any CriticRole (live LLMCritic or a stub for self-test).
        trials: Repetitions per plan.
        model: Model label for the markdown header.

    Returns:
        The report dict (also written to results/0.2.1/).
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cases = generate_boundary_cases()
    print(f"Running {len(cases)} boundary cases × {trials} trials × 2 plans...")
    start = time.time()
    report = run_live_boundary_cases(critic, cases=cases, trials=trials)
    elapsed = time.time() - start
    report["model"] = model  # type: ignore[assignment]

    json_path = RESULTS_DIR / "live-boundary-report.json"
    md_path = RESULTS_DIR / "live-boundary-report.md"
    json_path.write_text(json.dumps(report, indent=2, default=str))
    md_path.write_text(_markdown_summary(report, model, trials, elapsed))

    print(f"\nReport written to:\n  {json_path}\n  {md_path}")
    print(
        f"label_flip={report['label_flip_rate']:.3f}  "
        f"family_migration={report['family_migration_rate']:.3f}  "
        f"evidence_drift={report['evidence_drift_rate']:.3f}  "
        f"underclaim_approvals={report['underclaim_approvals']}"
    )
    return report


def self_test() -> dict:
    """Hermetic wiring check ($0): stub critic, verify report shape + artifacts.

    Confirms the script end-to-end (cases → harness → file artifacts) without
    touching a network. A deterministic stub critic should yield zero flips,
    zero drift, zero underclaim approvals.
    """
    import tempfile

    global RESULTS_DIR
    original = RESULTS_DIR
    with tempfile.TemporaryDirectory() as tmp:
        RESULTS_DIR = Path(tmp)
        report = run_boundary(_StubCritic(), trials=2, model="stub-self-test")
        RESULTS_DIR = original

    checks = {
        "cases_evaluated_positive": report["cases_evaluated"] > 0,
        "has_all_four_metrics": all(
            k in report
            for k in (
                "label_flip_rate",
                "family_migration_rate",
                "evidence_drift_rate",
                "underclaim_approvals",
            )
        ),
        "stub_yields_zero_flips": report["label_flip_rate"] == 0.0,
        "stub_yields_zero_drift": report["evidence_drift_rate"] == 0.0,
        "per_case_records_present": len(report["cases"]) == report["cases_evaluated"],
    }
    passed = all(checks.values())
    summary = {"all_pass": passed, "checks": checks, "model": report["model"]}
    print(json.dumps(summary, indent=2))
    print("\nSELF-TEST PASS" if passed else "\nSELF-TEST FAIL")
    return summary


def main(argv: list[str]) -> None:
    if "--self-test" in argv:
        self_test()
        return

    trials = 5
    for i, arg in enumerate(argv):
        if arg == "--trials" and i + 1 < len(argv):
            trials = int(argv[i + 1])

    critic, model = build_live_critic()
    run_boundary(critic, trials=trials, model=model)


if __name__ == "__main__":
    main(sys.argv[1:])
