#!/usr/bin/env python3
"""Run field-test goals against a live LLM.

Usage:
    # All 170 goals (P5 full sweep)
    python3 docs/field-test/scripts/run.py --all

    # Specific domains
    python3 docs/field-test/scripts/run.py --domain idp,mao,sre,scp,fng

    # Specific goals
    python3 docs/field-test/scripts/run.py --goals db-01,k8s-01,adv-01

    # Dry run: list what would run without executing
    python3 docs/field-test/scripts/run.py --all --dry-run

    # Resume after interruption (skip existing traces)
    python3 docs/field-test/scripts/run.py --all --skip-existing

    # Use MLX local model instead of cloud
    python3 docs/field-test/scripts/run.py --all --provider mlx
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from planner_critic.llm.registry import ProviderRegistry, ProviderSpec
from planner_critic.loop import LoopConfig
from planner_critic.schema.goal import Goal

API_KEY = os.environ.get("OPENROUTER_API_KEY")
MLX_API_KEY = os.environ.get("MLX_API_KEY", "omlx-test")

GOALS_ROOT = Path(__file__).parent.parent / "goals"
RESULTS_ROOT = Path(__file__).parent.parent.parent / "results"

PROVIDERS = {
    "openai": ProviderSpec(
        name="openai", transport="openai-compatible",
        base_url="https://openrouter.ai/api/v1", model="openai/gpt-4o-mini",
        api_key=API_KEY, max_tokens=16384, timeout_s=300.0,
    ),
    "omlx": ProviderSpec(
        name="omlx", transport="openai-compatible",
        base_url="http://127.0.0.1:8000/v1", model="mlx-community/Qwen3-4B-Instruct-2507-4bit",
        api_key=MLX_API_KEY, max_tokens=16384, timeout_s=300.0,
    ),
}


def discover_goals(domains: list[str] | None = None, goal_ids: list[str] | None = None) -> list[tuple[str, str]]:
    """Discover goal files on disk. Returns [(domain, goal_id), ...] sorted.

    ``goal_ids`` are matched as substrings against the full goal ID
    (e.g. ``--goals db-01`` matches ``db-01-schema-migration``).
    """
    results: list[tuple[str, str]] = []
    for gfile in sorted(GOALS_ROOT.rglob("*.json")):
        domain = gfile.parent.name
        gid = gfile.stem
        if domains and domain not in domains:
            continue
        if goal_ids and not any(pid in gid for pid in goal_ids):
            continue
        results.append((domain, gid))
    return results


def make_registry(provider: str) -> ProviderRegistry:
    spec = PROVIDERS.get(provider)
    if not spec:
        sys.exit(f"Unknown provider: {provider}. Choose from: {','.join(PROVIDERS)}")
    if spec.name == "openai" and not API_KEY:
        sys.exit("OPENROUTER_API_KEY not set")
    return ProviderRegistry(
        providers={"default": spec},
        roles={"planner": "default", "critic": "default"},
    )


def run_goal(domain: str, gid: str, registry: ProviderRegistry, config: LoopConfig,
             output_dir: Path) -> dict:
    """Run a single goal through the harness and return the result dict."""
    import yaml
    from planner_critic.field_test_harness import run_core_api

    goal_path = GOALS_ROOT / domain / f"{gid}.json"
    goal = Goal.model_validate(json.loads(goal_path.read_text()))
    assert_path = GOALS_ROOT / domain / "assertions" / f"{gid}.yaml"
    assertions = yaml.safe_load(assert_path.read_text()) if assert_path.exists() else {}
    start = time.monotonic()
    trace = run_core_api(goal, assertions, planner=None, registry=registry, lc=config, out=output_dir / gid)
    elapsed = time.monotonic() - start
    result = trace.get("result", {})
    status = result.get("status", "unknown")
    reason = result.get("reason_code", "")
    revs = result.get("revision_count", "?")
    return {
        "goal_id": gid, "domain": domain, "status": status,
        "reason": reason, "revisions": revs, "elapsed": round(elapsed, 1),
    }


def _default_output(provider: str) -> Path:
    """Derive output directory from provider: results/<version>/<provider-model>/."""
    spec = PROVIDERS[provider]
    model_slug = spec.model.replace("/", "-").replace(".", "-")
    return Path(__file__).parent.parent.parent / "results" / "0.2.0" / f"{provider}-{model_slug}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run field-test goals against a live LLM")
    parser.add_argument("--all", action="store_true", help="Run all 170 goals")
    parser.add_argument("--domain", type=str, help="Comma-separated domains to run")
    parser.add_argument("--goals", type=str, help="Comma-separated goal IDs to run")
    parser.add_argument("--provider", default="openai", choices=list(PROVIDERS),
                        help="LLM provider (default: openai/gpt-4o-mini)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output directory (default: results/0.2.0/<provider-model>/)")
    parser.add_argument("--revision-cap", type=int, default=4, help="Max revisions per goal")
    parser.add_argument("--skip-existing", action="store_true", help="Skip goals with existing traces")
    parser.add_argument("--dry-run", action="store_true", help="List goals without running")
    args = parser.parse_args()

    if not args.all and not args.domain and not args.goals:
        parser.print_help()
        sys.exit(1)

    domains = args.domain.split(",") if args.domain else None
    goal_ids = args.goals.split(",") if args.goals else None
    output_dir = Path(args.output) if args.output else _default_output(args.provider)

    scenarios = discover_goals(domains, goal_ids)
    if not scenarios:
        print("No goals found matching the filters.")
        sys.exit(1)

    print(f"Found {len(scenarios)} goal(s) across {len({d for d, _ in scenarios})} domain(s)")
    if args.dry_run:
        for domain, gid in scenarios:
            print(f"  {domain}/{gid}")
        return

    registry = make_registry(args.provider)
    config = LoopConfig(mode="deterministic-first", revision_cap=args.revision_cap)
    results: list[dict] = []
    existing_outputs = set(output_dir.rglob("trace.json"))
    existing_goals = {p.parent.parent.name for p in existing_outputs}

    for i, (domain, gid) in enumerate(scenarios, 1):
        if args.skip_existing and gid in existing_goals:
            print(f"[{i}/{len(scenarios)}] {gid} — skip (trace exists)")
            continue
        try:
            r = run_goal(domain, gid, registry, config, output_dir)
            label = "PASS" if r["status"] == "approved" else "FAIL"
            print(f"[{i}/{len(scenarios)}] {label} {gid} ({r['reason']}) rev={r['revisions']} [{r['elapsed']}s]")
            results.append(r)
        except Exception as e:
            print(f"[{i}/{len(scenarios)}] ERROR {gid} ({e})")
            results.append({"goal_id": gid, "domain": domain, "status": "ERROR",
                            "reason": str(e)[:80], "revisions": 0})

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(json.dumps(results, indent=2))
    passed = sum(1 for r in results if r["status"] == "approved")
    print(f"\nDone: {len(results)} results ({passed} passed)")


if __name__ == "__main__":
    main()