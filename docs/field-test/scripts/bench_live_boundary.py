"""Live-critic boundary-case benchmark (#218).

Sends the #171 boundary-corpus plan pairs through a **real critic model** N
times per plan and reduces the four community-review metrics:

* label_flip_rate — same plan, different family/severity verdicts across trials;
* family_migration_rate — seeded defects landing in advisory families;
* evidence_drift_rate — claimed facts/explanations varying across trials;
* underclaim_approvals — defect plans with zero blockers.

The harness itself is :func:`planner_critic.eval.live_boundary.run_live_boundary_cases`;
this script wires a registry/env-backed provider into it and commits the JSON +
markdown artifacts under ``results/0.2.2/``. Mirrors ``bench_cycling.py`` /
``bench_operational.py`` methodology. Spend ceiling: ≤ $1 at mini-class models
(~60 audits at 5 trials × 6 cases × 2 plans).

Usage::

    python3 docs/field-test/scripts/bench_live_boundary.py            # live, 5 trials
    python3 docs/field-test/scripts/bench_live_boundary.py --trials 3
    python3 docs/field-test/scripts/bench_live_boundary.py --self-test  # hermetic, $0
    python3 docs/field-test/scripts/bench_live_boundary.py --trials 5 --provider openai  # OpenRouter gpt-4o-mini

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
from planner_critic.eval.live_boundary import DecisionContext, run_live_boundary_cases
from planner_critic.redaction import SecretsRedactor
from planner_critic.schema.goal import Goal, RiskTolerance

API_KEY = os.environ.get("OPENROUTER_API_KEY")
MLX_API_KEY = os.environ.get("MLX_API_KEY", "omlx-test")

SCRIPTS_DIR = Path(__file__).resolve().parent  # docs/field-test/scripts


def _find_repo_root() -> Path:
    """Walk up from ``SCRIPTS_DIR`` until we find ``pyproject.toml``."""
    here = SCRIPTS_DIR
    for _ in range(10):
        if (here / "pyproject.toml").exists():
            return here
        here = here.parent
    raise RuntimeError(f"cannot find repo root above {SCRIPTS_DIR}")


REPO_ROOT = _find_repo_root()
RESULTS_DIR = REPO_ROOT / "results" / "0.2.3"

PROVIDERS: dict[str, dict] = {
    "openai": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4o-mini",
        "api_key": API_KEY,
    },
    "omlx": {
        "base_url": "http://127.0.0.1:8000/v1",
        "model": "mlx-community/Qwen3-4B-Instruct-2507-4bit",
        "api_key": MLX_API_KEY,
    },
}

#: A generic migration goal giving the critic prompt context. The boundary
#: cases are all migration/rollback-flavored synthetic plans (goal_id="test");
#: one goal description covers them. Use strict framing so seeded defects are
#: expected to land as blockers rather than advisory-only warnings.
_BOUNDARY_GOAL = Goal(
    id="boundary-critic",
    description=(
        "Migrate a stateful service from a legacy platform to a new one with "
        "rollback safety, verified mutations, and correct task ordering."
    ),
    risk_tolerance=RiskTolerance.STRICT,
)


class _StubCritic:
    """Hermetic stand-in for ``--self-test``: deterministic blocker on plan_b."""

    def audit(self, plan: Any, findings: list) -> list:
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


def build_provider(provider_name: str | None = None) -> tuple[Any, str, str, float | None]:
    """Resolve a live critic provider + model label + model version + temperature.

    Args:
        provider_name: ``"openai"`` or ``"omlx"`` for known configs; None
            falls back to plancritic.toml or LLM_* env vars.

    Returns:
        (provider, model_label, model_version, temperature) where provider is
        an LLMProvider-ready object.
    """
    from planner_critic.llm.registry import ProviderRegistry
    from planner_critic.llm.transport_openai import OpenAICompatibleProvider

    if provider_name and provider_name in PROVIDERS:
        spec = PROVIDERS[provider_name]
        return (
            OpenAICompatibleProvider(
                name=provider_name,
                base_url=spec["base_url"],
                model=spec["model"],
                api_key=spec["api_key"],
            ),
            spec["model"],
            "",
            None,
        )

    toml_path = REPO_ROOT / "plancritic.toml"
    if toml_path.exists():
        registry = ProviderRegistry.load(toml_path)
        if "critic" in registry.roles:
            spec = registry.providers[registry.roles["critic"]]
            return registry.get_provider("critic"), spec.model, spec.model_version, spec.temperature

    base_url = os.environ.get("LLM_BASE_URL", "").strip()
    model = os.environ.get("LLM_MODEL", "").strip()
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if not base_url or not model:
        raise RuntimeError(
            "no critic provider configured: pass --provider openai|omlx or "
            "create plancritic.toml or set LLM_BASE_URL + LLM_MODEL (+ LLM_API_KEY)"
        )

    return (
        OpenAICompatibleProvider(
            name="env-critic",
            base_url=base_url,
            model=model,
            api_key=api_key,
        ),
        model,
        "",
        None,
    )


def build_live_critic(provider_name: str | None = None) -> tuple[Any, str, str, float | None]:
    """Build a live LLMCritic bound to the boundary goal + provider.

    Returns:
        (critic, model_label, model_version, temperature)
    """
    from planner_critic.critique.critic import LLMCritic

    provider, model, model_version, temperature = build_provider(provider_name)
    return LLMCritic(_BOUNDARY_GOAL, provider), model, model_version, temperature


def _markdown_summary(report: dict, model: str, trials: int, elapsed_s: float) -> str:
    """Render a short markdown summary of the live run."""
    lines = [
        "# Live-critic boundary-case report — v0.2.2 (#218)",
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


def run_boundary(
    critic: Any,
    *,
    trials: int = 5,
    model: str = "stub",
    decision_context: DecisionContext | None = None,
) -> dict:
    """Run the boundary cases through ``critic`` and write report artifacts.

    Args:
        critic: Any CriticRole (live LLMCritic or a stub for self-test).
        trials: Repetitions per plan.
        model: Model label for the markdown header.
        decision_context: Metadata about the critic model for attribution.

    Returns:
        The report dict (also written to results/0.2.2/).
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cases = generate_boundary_cases()
    print(f"Running {len(cases)} boundary cases × {trials} trials × 2 plans...")
    start = time.time()
    report = run_live_boundary_cases(
        critic, cases=cases, trials=trials, decision_context=decision_context
    )
    elapsed = time.time() - start
    report["model"] = model  # type: ignore[assignment]

    redactor = SecretsRedactor()
    redacted_report = redactor.redact_dict(report)
    redacted_json = json.dumps(redacted_report, indent=2, default=str)
    redacted_md = redactor.redact(_markdown_summary(report, model, trials, elapsed))

    json_path = RESULTS_DIR / "live-boundary-report.json"
    md_path = RESULTS_DIR / "live-boundary-report.md"
    json_path.write_text(redacted_json)
    md_path.write_text(redacted_md)

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
    model_label = None
    provider = None
    for i, arg in enumerate(argv):
        if arg == "--trials" and i + 1 < len(argv):
            trials = int(argv[i + 1])
        if arg == "--model-label" and i + 1 < len(argv):
            model_label = argv[i + 1]
        if arg == "--provider" and i + 1 < len(argv):
            provider = argv[i + 1]

    import datetime
    import hashlib

    critic, model, model_version, temperature = build_live_critic(provider_name=provider)
    ctx = DecisionContext(
        model_id=model,
        model_version=model_version,
        temperature=temperature if temperature is not None else 0.0,
        system_prompt_hash=hashlib.sha256(b"boundary-critic-prompt-v1").hexdigest()[:16],
        timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
    )
    run_boundary(critic, trials=trials, model=model_label or model, decision_context=ctx)


if __name__ == "__main__":
    main(sys.argv[1:])
