#!/usr/bin/env python3
"""Multi-model planner comparison benchmark (#252).

Runs the same goal corpus through multiple planner models using the same
critic model as a control. Measures pass/fail rate, cost per goal, and
defect-family distribution per planner model.

Usage:
    python bench_multi_model.py --corpus <dir> --roles <toml> [--goals N]

    --corpus   Directory of goal JSON files (default: docs/field-test/goals)
    --roles    Provider registry TOML defining planner/critic providers
    --goals    Optional limit on number of goals to run per model
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from planner_critic.engine import Engine
from planner_critic.llm.registry import ProviderRegistry
from planner_critic.loop import LoopConfig
from planner_critic.schema.goal import Goal

sys.path.append(str(Path(__file__).resolve().parents[1]))


def load_goals(corpus_dir: Path, limit: int | None = None) -> list[Goal]:
    """Load all goal files from a directory tree."""
    goals: list[Goal] = []
    for p in sorted(corpus_dir.rglob("*.json")):
        if "assertions" in str(p):
            continue
        try:
            goals.append(Goal.model_validate(json.loads(p.read_text())))
        except Exception:
            continue
    if limit:
        goals = goals[:limit]
    return goals


def run_model_comparison(
    corpus_dir: Path,
    roles_config: str,
    limit: int | None = None,
) -> dict[str, object]:
    """Run the same corpus through each configured planner model.

    Returns:
        A JSON-ready comparison report.
    """
    registry = ProviderRegistry.load(roles_config)
    goals = load_goals(corpus_dir, limit)

    # Distinct planner providers, same critic
    planner_names = sorted(set(registry.roles.get("planner", "local").split(",")))
    critic_name = registry.roles.get("critic", "local")

    results: dict[str, object] = {}
    for planner_name in planner_names:
        provider = registry.providers.get(planner_name)
        if provider is None:
            continue
        from planner_critic.cli.plan import _CLIPlanner
        from planner_critic.critique.critic import LLMCritic

        planner = _CLIPlanner(provider)
        critic = LLMCritic(
            goals[0] if goals else _dummy_goal(), registry.providers[critic_name]
        )
        engine = Engine(planner=planner, critic=critic, config=LoopConfig(revision_cap=3))

        model_results: dict[str, object] = {"approved": 0, "escalated": 0, "errors": 0, "goals": []}
        start = time.monotonic()
        for goal in goals:
            try:
                result = engine.plan(goal)
                if result.status == "approved":
                    model_results["approved"] += 1
                else:
                    model_results["escalated"] += 1
                model_results["goals"].append(
                    {
                        "goal_id": goal.id,
                        "status": result.status,
                        "reason_code": result.reason_code,
                    }
                )
            except Exception as exc:
                model_results["errors"] += 1
                model_results["goals"].append(
                    {"goal_id": goal.id, "status": "error", "error": str(exc)}
                )
        model_results["duration_s"] = round(time.monotonic() - start, 2)
        model_results["cost_estimate"] = estimate_cost(
            provider.model, int(model_results["approved"]) + int(model_results["escalated"])
        )
        results[planner_name] = model_results

    return {"planner_models": planner_names, "critic_model": critic_name, "by_planner": results}


def _dummy_goal() -> Goal:
    return Goal(id="dummy", description="dummy", risk_tolerance="balanced")


def estimate_cost(model: str, calls: int) -> float:
    """Rough cost estimate based on model and call count."""
    rates = {
        "gpt-4o-mini": 0.00015,
        "gpt-4o": 0.0025,
        "claude-3.5": 0.003,
        "deepseek-v4": 0.0005,
    }
    per_call = next((v for k, v in rates.items() if k in model), 0.00015)
    return round(per_call * calls, 4)


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-model planner comparison benchmark")
    parser.add_argument("--corpus", default="docs/field-test/goals", type=Path)
    parser.add_argument("--roles", default="plancritic.toml")
    parser.add_argument("--goals", type=int, default=None)
    args = parser.parse_args()

    report = run_model_comparison(args.corpus, args.roles, args.goals)
    print(json.dumps(report, indent=2))
    out = Path("docs/field-test/v0.2.2/multi-model-comparison.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(f"\nReport written to {out}")


if __name__ == "__main__":
    main()