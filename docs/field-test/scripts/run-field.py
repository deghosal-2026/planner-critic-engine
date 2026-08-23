#!/usr/bin/env python3
"""Run field-test scenarios for v0.2.0.

Single entry point for all field test phases. Each --<phase> flag
selects a test category; --all runs every test in that category.

Usage:
    # Goal sweep (170 goals through live LLM)
    run-field.py --goals-sweep --all
    run-field.py --goals-sweep --domain idp,mao,sre
    run-field.py --goals-sweep --goals db-01,k8s-01 --skip-existing

    # P0: Assertion validation (no LLM)
    run-field.py --validate --all

    # P2: Deterministic subsystem tests (50 tests, no LLM)
    run-field.py --subsystem --all

    # P3: LLM subsystem tests (requires live LLM)
    run-field.py --subsystem --all --run-llm

    # Security oracle (SWE-bench critic evaluation)
    run-field.py --security --all
    run-field.py --security --adversarial

    # Benchmarks (auto-repair, rollback, stasis — no LLM)
    run-field.py --benchmarks --all

    # Run EVERYTHING
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
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "v0.2.0" / "scripts"
TESTS_DIR = REPO_ROOT / "tests" / "field_test_v0_2_0"
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


# ── Skip-existing helpers ───────────────────────────────────────────────────


def _has_results(path: Path) -> bool:
    """Check if output already exists for skip-existing logic."""
    if path.is_file():
        return path.exists() and path.stat().st_size > 0
    if path.is_dir():
        return any(path.rglob("trace.json")) or (path / "results.json").exists()
    return False


def _should_skip(args, marker: str) -> bool:
    """Check if a phase should be skipped (--skip-existing)."""
    if not args.skip_existing:
        return False
    marker_path = RESULTS_ROOT / f".{marker}_done"
    return marker_path.exists()


def _mark_done(marker: str) -> None:
    """Mark a phase as done (for --skip-existing)."""
    marker_path = RESULTS_ROOT / f".{marker}_done"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text("done")


# ── P0: Validation ─────────────────────────────────────────────────────────


def run_validate(args) -> None:
    if _should_skip(args, "validate"):
        print("[validate] ✅ SKIP (already done)")
        return
    print("[validate] Checking all 170 assertion YAMLs...")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "pre_run_validation.py")],
        capture_output=False,
    )
    if result.returncode != 0:
        print("[validate] ❌ FAILED")
    else:
        print("[validate] ✅ PASSED")
        _mark_done("validate")


# ── P2/P3: Subsystem tests ──────────────────────────────────────────────────


def run_subsystem(args) -> None:
    marker = "subsystem_llm" if args.run_llm else "subsystem"
    if _should_skip(args, marker):
        print(f"[subsystem] ✅ SKIP (already done, {marker})")
        return
    cmd = [sys.executable, "-m", "pytest", str(TESTS_DIR), "-v", "--no-cov"]
    if args.run_llm:
        print("[subsystem] Running with --run-llm (requires live LLM)")
    else:
        print("[subsystem] Running deterministic tests only (no LLM)")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("[subsystem] ❌ FAILED")
    else:
        print("[subsystem] ✅ PASSED")
        _mark_done(marker)


# ── Security oracle ─────────────────────────────────────────────────────────


def run_security(args) -> None:
    if _should_skip(args, "security"):
        print("[security] ✅ SKIP (already done)")
        return
    print("[security] Running SWE-bench security oracle evaluation...")
    if args.adversarial:
        print("[security] Running injection harness (adversarial)...")
        cmd = [sys.executable, "-m", "planner_critic.cli.eval", "swebench-security", "--adversarial"]
    else:
        cmd = [sys.executable, "-m", "planner_critic.cli.eval", "swebench-security"]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("[security] ❌ FAILED or incomplete")
    else:
        print("[security] ✅ DONE")

    if args.all:
        print("[security] Running injection harness...")
        subprocess.run([sys.executable, "-m", "planner_critic.cli.eval", "swebench-security", "--adversarial"])
        print("[security] Running gate regression...")
        subprocess.run([sys.executable, "-m", "planner_critic.cli.eval", "swebench-security", "--regression"])
        print("[security] Proposing standing rules...")
        subprocess.run([sys.executable, "-m", "planner_critic.cli.lessons", "propose"])
        print("[security] ✅ ALL DONE")
        _mark_done("security")


# ── Benchmarks ───────────────────────────────────────────────────────────────


def run_benchmarks(args) -> None:
    if _should_skip(args, "benchmarks"):
        print("[benchmarks] ✅ SKIP (already done)")
        return
    benchmarks = [
        ("auto-repair", SCRIPTS_DIR / "bench_auto_repair.py"),
        ("rollback", SCRIPTS_DIR / "bench_rollback.py"),
        ("stasis", SCRIPTS_DIR / "bench_stasis.py"),
    ]
    all_ok = True
    for name, script in benchmarks:
        if not script.exists():
            print(f"[benchmarks] ❌ {name}: script not found ({script})")
            all_ok = False
            continue
        out_file = RESULTS_ROOT / f"bench_{name}.json"
        if args.skip_existing and out_file.exists() and out_file.stat().st_size > 0:
            print(f"[benchmarks] ✅ {name}: SKIP (results exist)")
            continue
        print(f"[benchmarks] Running {name}...")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w") as f:
            result = subprocess.run([sys.executable, str(script)], stdout=f, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"[benchmarks] ❌ {name}: {result.stderr.decode()[:200]}")
            all_ok = False
        else:
            print(f"[benchmarks] ✅ {name}: results → {out_file}")
    if all_ok:
        _mark_done("benchmarks")


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run v0.2.0 field tests — single entry point for all phases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  run-field.py --goals-sweep --all                          # All 170 goals (cloud)
  run-field.py --goals-sweep --all --provider omlx          # All 170 goals (local)
  run-field.py --goals-sweep --domain idp,mao,sre           # Specific domains
  run-field.py --goals-sweep --goals db-01,k8s-01           # Specific goals
  run-field.py --goals-sweep --all --skip-existing          # Resume
  run-field.py --validate --all                             # P0 assertion validation
  run-field.py --subsystem --all                            # P2 deterministic tests
  run-field.py --subsystem --all --run-llm                  # P3 LLM tests
  run-field.py --security --all                             # Security oracle (all)
  run-field.py --security --adversarial                     # Injection harness only
  run-field.py --benchmarks --all                           # All 3 benchmarks
  run-field.py --all                                        # EVERYTHING
""",
    )

    # Phase selectors
    parser.add_argument("--goals-sweep", action="store_true", help="Run 170 goals through LLM")
    parser.add_argument("--validate", action="store_true", help="P0: assertion YAML validation")
    parser.add_argument("--subsystem", action="store_true", help="P2/P3: 50 WBS coverage tests")
    parser.add_argument("--security", action="store_true", help="§4.3: SWE-bench security oracle")
    parser.add_argument("--benchmarks", action="store_true", help="§4.6/4.7: auto-repair, rollback, stasis")

    # Shared options
    parser.add_argument("--all", action="store_true", help="Run all tests in selected phase(s)")
    parser.add_argument("--domain", type=str, help="Comma-separated domains (goals-sweep only)")
    parser.add_argument("--goals", type=str, help="Comma-separated goal IDs (goals-sweep only)")
    parser.add_argument("--provider", default="openai", choices=list(PROVIDERS),
                        help="LLM provider (default: openai/gpt-4o-mini)")
    parser.add_argument("--output", type=str, default=None, help="Output directory (goals-sweep only)")
    parser.add_argument("--revision-cap", type=int, default=4, help="Max revisions per goal")
    parser.add_argument("--skip-existing", action="store_true", help="Skip goals with existing traces")
    parser.add_argument("--dry-run", action="store_true", help="List without executing")
    parser.add_argument("--run-llm", action="store_true", help="Run LLM-required subsystem tests")
    parser.add_argument("--adversarial", action="store_true", help="Run injection harness (security only)")

    args = parser.parse_args()

    # If no phase selected, show help
    if not any([args.goals_sweep, args.validate, args.subsystem, args.security, args.benchmarks, args.all]):
        parser.print_help()
        sys.exit(1)

    # If --all with no phase, run everything
    if args.all and not any([args.goals_sweep, args.validate, args.subsystem, args.security, args.benchmarks]):
        print("=== Running ALL phases ===\n")
        run_validate(args)
        print()
        run_subsystem(args)
        print()
        run_benchmarks(args)
        print()
        run_security(args)
        print()
        run_goals_sweep(args)
        return

    # Run selected phase(s)
    if args.validate:
        run_validate(args)
    if args.subsystem:
        run_subsystem(args)
    if args.security:
        run_security(args)
    if args.benchmarks:
        run_benchmarks(args)
    if args.goals_sweep:
        if not args.all and not args.domain and not args.goals:
            print("--goals-sweep requires --all, --domain, or --goals")
            sys.exit(1)
        run_goals_sweep(args)


if __name__ == "__main__":
    main()
