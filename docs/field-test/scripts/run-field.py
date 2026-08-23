#!/usr/bin/env python3
"""Run LLM-based field tests for v0.2.0.

Only LLM-required tests. Deterministic tests are in pytest:
    pytest tests/field_test_v0_2_0/ -v --no-cov

Usage:
    # Goal sweep (170 goals through live LLM)
    run-field.py --goals-sweep --all
    run-field.py --goals-sweep --domain idp,mao,sre
    run-field.py --goals-sweep --goals db-01,k8s-01 --skip-existing

    # Security oracle (SWE-bench critic evaluation)
    run-field.py --security --all
    run-field.py --security --adversarial

    # Both
    run-field.py --all
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from planner_critic.llm.registry import ProviderRegistry, ProviderSpec
from planner_critic.loop import LoopConfig
from planner_critic.schema.goal import Goal

API_KEY = os.environ.get("OPENROUTER_API_KEY")
MLX_API_KEY = os.environ.get("MLX_API_KEY", "omlx-test")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
GOALS_ROOT = Path(__file__).resolve().parent.parent / "goals"
RESULTS_ROOT = REPO_ROOT / "results" / "0.2.0"

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


# ── Goal sweep ──────────────────────────────────────────────────────────────


def discover_goals(domains: list[str] | None = None, goal_ids: list[str] | None = None) -> list[tuple[str, str]]:
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
    return {
        "goal_id": gid, "domain": domain, "status": result.get("status", "unknown"),
        "reason": result.get("reason_code", ""), "revisions": result.get("revision_count", "?"),
        "elapsed": round(elapsed, 1),
    }


def run_goals_sweep(args) -> None:
    domains = args.domain.split(",") if args.domain else None
    goal_ids = args.goals.split(",") if args.goals else None
    spec = PROVIDERS[args.provider]
    model_slug = spec.model.replace("/", "-").replace(".", "-")
    output_dir = Path(args.output) if args.output else RESULTS_ROOT / f"{args.provider}-{model_slug}"

    scenarios = discover_goals(domains, goal_ids)
    if not scenarios:
        print("No goals found.")
        return

    print(f"[goals-sweep] {len(scenarios)} goals across {len({d for d, _ in scenarios})} domains")
    if args.dry_run:
        for domain, gid in scenarios:
            print(f"  {domain}/{gid}")
        return

    registry = make_registry(args.provider)
    config = LoopConfig(mode="deterministic-first", revision_cap=args.revision_cap)
    results: list[dict] = []
    existing = {p.parent.name for p in output_dir.rglob("trace.json")} if args.skip_existing else set()

    for i, (domain, gid) in enumerate(scenarios, 1):
        if gid in existing:
            print(f"[{i}/{len(scenarios)}] {gid} — skip")
            continue
        try:
            r = run_goal(domain, gid, registry, config, output_dir)
            label = "PASS" if r["status"] == "approved" else "FAIL"
            print(f"[{i}/{len(scenarios)}] {label} {gid} ({r['reason']}) rev={r['revisions']} [{r['elapsed']}s]")
            results.append(r)
        except Exception as e:
            print(f"[{i}/{len(scenarios)}] ERROR {gid} ({e})")
            results.append({"goal_id": gid, "domain": domain, "status": "ERROR", "reason": str(e)[:80], "revisions": 0})

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(json.dumps(results, indent=2))
    passed = sum(1 for r in results if r["status"] == "approved")
    print(f"\n[goals-sweep] Done: {len(results)} results ({passed} passed)")


# ── Security oracle ─────────────────────────────────────────────────────────


def run_security(args) -> None:
    print("[security] Running SWE-bench security oracle evaluation...")
    if args.adversarial:
        print("[security] Running injection harness (adversarial)...")
        cmd = [sys.executable, "-m", "planner_critic.cli.eval", "swebench-security", "--adversarial"]
    else:
        cmd = [sys.executable, "-m", "planner_critic.cli.eval", "swebench-security"]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("[security] FAILED or incomplete")
    else:
        print("[security] DONE")

    if args.all:
        print("[security] Running injection harness...")
        subprocess.run([sys.executable, "-m", "planner_critic.cli.eval", "swebench-security", "--adversarial"])
        print("[security] Running gate regression...")
        subprocess.run([sys.executable, "-m", "planner_critic.cli.eval", "swebench-security", "--regression"])
        print("[security] Proposing standing rules...")
        subprocess.run([sys.executable, "-m", "planner_critic.cli.lessons", "propose"])
        print("[security] ALL DONE")


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run LLM-based field tests for v0.2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  run-field.py --goals-sweep --all                    # All 170 goals (cloud)
  run-field.py --goals-sweep --all --provider omlx    # All 170 goals (local)
  run-field.py --goals-sweep --domain idp,mao,sre     # Specific domains
  run-field.py --goals-sweep --goals db-01,k8s-01     # Specific goals
  run-field.py --goals-sweep --all --skip-existing    # Resume
  run-field.py --security --all                       # Security oracle (all)
  run-field.py --security --adversarial               # Injection harness only
  run-field.py --all                                  # Both goals + security

  Deterministic tests (no LLM):
  pytest tests/field_test_v0_2_0/ -v --no-cov
""",
    )

    parser.add_argument("--goals-sweep", action="store_true", help="Run 170 goals through LLM")
    parser.add_argument("--security", action="store_true", help="SWE-bench security oracle (requires LLM)")
    parser.add_argument("--all", action="store_true", help="Run all LLM phases")
    parser.add_argument("--domain", type=str, help="Comma-separated domains (goals-sweep only)")
    parser.add_argument("--goals", type=str, help="Comma-separated goal IDs (goals-sweep only)")
    parser.add_argument("--provider", default="openai", choices=list(PROVIDERS),
                        help="LLM provider (default: openai/gpt-4o-mini)")
    parser.add_argument("--output", type=str, default=None, help="Output directory (goals-sweep only)")
    parser.add_argument("--revision-cap", type=int, default=4, help="Max revisions per goal")
    parser.add_argument("--skip-existing", action="store_true", help="Skip goals with existing traces")
    parser.add_argument("--dry-run", action="store_true", help="List without executing")
    parser.add_argument("--adversarial", action="store_true", help="Run injection harness (security only)")

    args = parser.parse_args()

    if not any([args.goals_sweep, args.security, args.all]):
        parser.print_help()
        sys.exit(1)

    if args.all and not any([args.goals_sweep, args.security]):
        print("=== Running ALL LLM phases ===\n")
        run_security(args)
        print()
        run_goals_sweep(args)
        return

    if args.security:
        run_security(args)
    if args.goals_sweep:
        if not args.all and not args.domain and not args.goals:
            print("--goals-sweep requires --all, --domain, or --goals")
            sys.exit(1)
        run_goals_sweep(args)


if __name__ == "__main__":
    main()
