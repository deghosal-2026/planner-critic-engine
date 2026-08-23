#!/usr/bin/env python3
"""Run field tests for v0.2.1 (four-phase: P0/P2/P3/P4).

Phases are cost-tiered so hermetic ($0) work runs first and LLM-spending work
is gated behind an explicit ``--run-llm`` flag:

* **P0 — validate** (``--validate --all``): parse every goal JSON + assertion
  YAML; ~5 min, $0.
* **P2 — subsystem, hermetic** (``--subsystem --all``): deterministic WBS
  coverage tests via pytest; ~45 min, $0.
* **P4 — benchmarks** (``--benchmarks --all``): hermetic bench scripts
  (cycling #217, operational #221, live-boundary self-test #218); ~30 min, $0.
* **P3 — subsystem, LLM** (``--subsystem --all --run-llm``): live goals sweep
  + live-critic boundary-case run (#218); ~1–2 hr, ~$0.10.

Legacy flags ``--goals-sweep`` / ``--security`` route into the P3 LLM phase.

Usage::

    # P0: validate all 170 assertion YAMLs ($0)
    run-field.py --validate --all

    # P2: deterministic WBS coverage tests ($0)
    run-field.py --subsystem --all

    # P4: benchmarks — auto-repair, rollback, stasis, boundary self-test ($0)
    run-field.py --benchmarks --all

    # P3: LLM subsystem tests — goals sweep + live boundary (#218) (~$0.10)
    run-field.py --subsystem --all --run-llm
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
RESULTS_ROOT = REPO_ROOT / "results" / "0.2.1"
FIELD_TEST_DIR = Path(__file__).resolve().parent.parent  # docs/field-test
BENCH_DIR_V021 = FIELD_TEST_DIR / "v0.2.1" / "scripts"

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


# ── P0: validate assertion YAMLs ($0) ────────────────────────────────────────


def discover_goals(
    domains: list[str] | None = None, goal_ids: list[str] | None = None
) -> list[tuple[str, str]]:
    """List (domain, goal_id) pairs under GOALS_ROOT, filtered as requested."""
    results: list[tuple[str, str]] = []
    for gfile in sorted(GOALS_ROOT.rglob("*.json")):
        if "assertions" in gfile.parts:
            continue
        domain = gfile.parent.name
        gid = gfile.stem
        if domains and domain not in domains:
            continue
        if goal_ids and not any(pid in gid for pid in goal_ids):
            continue
        results.append((domain, gid))
    return results


def run_validate(args) -> None:
    """P0: parse every goal JSON + its assertion YAML; report breakages ($0)."""
    import yaml

    scenarios = discover_goals(
        args.domain.split(",") if args.domain else None,
        args.goals.split(",") if args.goals else None,
    )
    if not scenarios:
        print("[validate] No goals found.")
        return
    print(f"[validate] {len(scenarios)} goals across {len({d for d, _ in scenarios})} domains")
    ok, broken = 0, []
    for domain, gid in scenarios:
        goal_path = GOALS_ROOT / domain / f"{gid}.json"
        assert_path = GOALS_ROOT / domain / "assertions" / f"{gid}.yaml"
        try:
            Goal.model_validate(json.loads(goal_path.read_text()))
            if assert_path.exists():
                yaml.safe_load(assert_path.read_text())
            ok += 1
        except Exception as exc:  # noqa: BLE001
            broken.append((domain, gid, str(exc)[:120]))
    print(f"[validate] {ok}/{len(scenarios)} valid; {len(broken)} broken")
    for domain, gid, err in broken:
        print(f"  BROKEN {domain}/{gid}: {err}")


# ── P2: hermetic subsystem tests ($0) ─────────────────────────────────────────


def run_subsystem_hermetic(args) -> None:
    """P2: deterministic WBS coverage tests via pytest ($0)."""
    test_dirs = [
        "tests/field_test_v0_2_0",
        "tests/field_test_v0_2_1",
    ]
    label = " ".join(d for d in test_dirs if (REPO_ROOT / d).exists())
    print(f"[subsystem] hermetic WBS coverage: pytest {label} --no-cov")
    cmd = [sys.executable, "-m", "pytest", *test_dirs, "--no-cov", "-q"]
    if args.dry_run:
        print(" ".join(cmd))
        return
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        print("[subsystem] FAILED")
        sys.exit(result.returncode)
    print("[subsystem] DONE")


# ── P3: LLM subsystem tests (~$0.10) ──────────────────────────────────────────


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
    """Live goal sweep through the configured LLM provider."""
    domains = args.domain.split(",") if args.domain else None
    goal_ids = args.goals.split(",") if args.goals else None
    spec = PROVIDERS[args.provider]
    model_slug = spec.model.replace("/", "-").replace(".", "-")
    output_dir = Path(args.output) if args.output else RESULTS_ROOT / f"{args.provider}-{model_slug}"

    scenarios = discover_goals(domains, goal_ids)
    if not scenarios:
        print("[goals-sweep] No goals found.")
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
        except Exception as e:  # noqa: BLE001
            print(f"[{i}/{len(scenarios)}] ERROR {gid} ({e})")
            results.append({"goal_id": gid, "domain": domain, "status": "ERROR", "reason": str(e)[:80], "revisions": 0})

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(json.dumps(results, indent=2))
    passed = sum(1 for r in results if r["status"] == "approved")
    print(f"\n[goals-sweep] Done: {len(results)} results ({passed} passed)")


def run_boundary_live(args) -> None:
    """P3 #218: live-critic boundary-case run via bench_live_boundary.py.

    Writes JSON + markdown to results/0.2.1/. Spend ≤ $1 (mini-class model,
    ~60 audits). Provider is overridden to match the --provider flag so the
    boundary run uses the same model as the goals sweep.
    """
    script = BENCH_DIR_V021 / "bench_live_boundary.py"
    if not script.exists():
        print(f"[boundary] missing {script}")
        return
    trials = str(args.boundary_trials)
    spec = PROVIDERS[args.provider]
    cmd = [sys.executable, str(script), "--trials", trials, "--model-label", spec.model, "--provider", args.provider]
    print(f"[boundary] live-critic run (#218) via {spec.model}: {' '.join(cmd)}")
    if args.dry_run:
        print(" ".join(cmd))
        return
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        print("[boundary] FAILED or incomplete")
    else:
        print("[boundary] DONE — see results/0.2.1/live-boundary-report.{json,md}")


def run_subsystem_llm(args) -> None:
    """P3: live LLM subsystem tests — goals sweep + live boundary (#218)."""
    print("=== P3: LLM subsystem tests (spends money) ===\n")
    if not args.no_goals:
        run_goals_sweep(args)
        print()
    if not args.no_boundary:
        run_boundary_live(args)


def run_security(args) -> None:
    """Legacy: SWE-bench security oracle (LLM)."""
    print("[security] Running SWE-bench security oracle evaluation...")
    if args.adversarial:
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


# ── P4: hermetic benchmarks ($0) ──────────────────────────────────────────────


def run_benchmarks(args) -> None:
    """P4: hermetic bench scripts — cycling, operational, boundary self-test ($0)."""
    print("=== P4: benchmarks (hermetic, $0) ===\n")
    benches = [
        ("cycling (#217 self-test)", BENCH_DIR_V021 / "bench_cycling.py", ["--self-test"]),
        ("operational (#221)", BENCH_DIR_V021 / "bench_operational.py", []),
        ("boundary (#218 self-test)", BENCH_DIR_V021 / "bench_live_boundary.py", ["--self-test"]),
    ]
    failed = []
    for label, script, extra in benches:
        if not script.exists():
            print(f"[bench] missing {script} — skipping {label}")
            continue
        cmd = [sys.executable, str(script), *extra]
        print(f"[bench] {label}: {' '.join(cmd)}")
        if args.dry_run:
            continue
        result = subprocess.run(cmd, cwd=REPO_ROOT)
        if result.returncode != 0:
            print(f"[bench] {label} FAILED")
            failed.append(label)
        print()
    if failed:
        print(f"[bench] {len(failed)} benchmark(s) failed: {', '.join(failed)}")
        sys.exit(1)
    print("[bench] ALL DONE")


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run v0.2.1 field tests (four-phase: P0/P2/P3/P4)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Phases (cost-tiered):
  P0  --validate --all              Validate 170 assertion YAMLs ($0)
  P2  --subsystem --all             Deterministic WBS coverage tests ($0)
  P4  --benchmarks --all            Hermetic benchmarks: cycling/operational/boundary ($0)
  P3  --subsystem --all --run-llm   LLM subsystem tests: goals sweep + boundary #218 (~$0.10)

Legacy (route to P3 LLM phase):
  --goals-sweep --all               Live goal sweep (cloud)
  --security --all                  SWE-bench security oracle

Deterministic tests also runnable directly:
  pytest tests/field_test_v0_2_0/ tests/field_test_v0_2_1/ -v --no-cov
""",
    )

    # Phase selectors
    parser.add_argument("--validate", action="store_true", help="P0: validate assertion YAMLs ($0)")
    parser.add_argument("--subsystem", action="store_true", help="P2 hermetic WBS tests; P3 LLM with --run-llm")
    parser.add_argument("--benchmarks", action="store_true", help="P4: hermetic bench scripts ($0)")
    parser.add_argument("--run-llm", action="store_true", help="Gate LLM-spending tests (P3)")
    parser.add_argument("--all", action="store_true", help="All domains/goals/cases for the selected phase")

    # Legacy selectors (route into P3)
    parser.add_argument("--goals-sweep", action="store_true", help="Legacy: live goal sweep (P3)")
    parser.add_argument("--security", action="store_true", help="Legacy: SWE-bench security oracle (P3)")

    # Filters / options
    parser.add_argument("--domain", type=str, help="Comma-separated domains (validate/goals-sweep)")
    parser.add_argument("--goals", type=str, help="Comma-separated goal IDs (validate/goals-sweep)")
    parser.add_argument("--provider", default="openai", choices=list(PROVIDERS),
                        help="LLM provider (default: openai/gpt-4o-mini)")
    parser.add_argument("--output", type=str, default=None, help="Output directory (goals-sweep)")
    parser.add_argument("--revision-cap", type=int, default=4, help="Max revisions per goal (goals-sweep)")
    parser.add_argument("--boundary-trials", type=int, default=5, help="Trials per plan (#218 boundary run)")
    parser.add_argument("--skip-existing", action="store_true", help="Skip goals with existing traces")
    parser.add_argument("--no-goals", action="store_true", help="P3: skip the goals sweep (boundary only)")
    parser.add_argument("--no-boundary", action="store_true", help="P3: skip the #218 boundary run (goals only)")
    parser.add_argument("--dry-run", action="store_true", help="List without executing")
    parser.add_argument("--adversarial", action="store_true", help="Run injection harness (security only)")

    args = parser.parse_args()

    if not any([args.validate, args.subsystem, args.benchmarks, args.goals_sweep, args.security]):
        parser.print_help()
        sys.exit(1)

    # P0 — hermetic validation
    if args.validate:
        run_validate(args)

    # P2 / P3 — subsystem (hermetic by default; LLM with --run-llm)
    if args.subsystem:
        if args.run_llm:
            run_subsystem_llm(args)
        else:
            run_subsystem_hermetic(args)

    # P4 — hermetic benchmarks
    if args.benchmarks:
        run_benchmarks(args)

    # Legacy LLM selectors route into P3
    if args.goals_sweep:
        if not args.all and not args.domain and not args.goals:
            print("--goals-sweep requires --all, --domain, or --goals")
            sys.exit(1)
        run_goals_sweep(args)
    if args.security:
        run_security(args)


if __name__ == "__main__":
    main()
