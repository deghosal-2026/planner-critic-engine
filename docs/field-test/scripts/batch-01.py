#!/usr/bin/env python3
"""Batch 1: 5 scenarios."""
import json, time, sys
from pathlib import Path

GOALS_ROOT = Path("docs/field-test/goals")
OUTPUT_ROOT = Path("docs/field-test/reports/0.1.0-08.20.2026/remain-scenario")
CONFIG = "plancritic-fieldtest.toml"

# Batch 1 scenarios:
#   db-09-cdc-shift (database)
#   db-10-multi-tenant-split (database)
#   db-11-read-replica-routing (database)
#   db-12-major-version-upgrade (database)
#   k8s-09-cluster-autoscaler (kubernetes)

SCENARIOS = [
    ("database", "db-09-cdc-shift"),
    ("database", "db-10-multi-tenant-split"),
    ("database", "db-11-read-replica-routing"),
    ("database", "db-12-major-version-upgrade"),
    ("kubernetes", "k8s-09-cluster-autoscaler"),
]

def parse_verdict(trace_path):
    try:
        t = json.loads(trace_path.read_text())
        result = t.get("result", {})
        return result.get("status", "unknown"), result.get("reason_code", "unknown"), result.get("revision_count", "?")
    except Exception:
        return "error", "parse_error", "?"

def main():
    from planner_critic.field_test_harness import run_sweep
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    results = []
    total = len(SCENARIOS)

    print(f"\n{"="*60}")
    print(f"  Batch 1: {total} scenarios")
    print(f"  Output: {OUTPUT_ROOT}")
    print(f"{"="*60}\n")

    for i, (domain, gid) in enumerate(SCENARIOS, 1):
        goal_dir = GOALS_ROOT / domain
        out_dir = OUTPUT_ROOT / gid
        print(f"  [{i}/{total}] {gid:<40} ... ", end="", flush=True)
        start = time.monotonic()
        try:
            run_sweep(goals_root=goal_dir, output_dir=out_dir, dimensions=["core-api"], config_path=CONFIG)
            elapsed = time.monotonic() - start
            trace_path = out_dir / "core-api" / gid / "trace.json"
            if not trace_path.exists():
                traces = list(out_dir.rglob("trace.json"))
                if traces: trace_path = traces[0]
            if trace_path.exists():
                status, reason, revs = parse_verdict(trace_path)
                verdict = "PASS" if status == "approved" else "FAIL"
                results.append({"goal_id": gid, "domain": domain, "verdict": verdict, "reason": reason, "revisions": revs})
                print(f"{verdict} ({reason}) rev={revs} [{elapsed:.1f}s]")
            else:
                results.append({"goal_id": gid, "domain": domain, "verdict": "ERROR", "reason": "no_trace", "revisions": 0})
                print(f"ERROR (no trace) [{elapsed:.1f}s]")
        except Exception as e:
            elapsed = time.monotonic() - start
            results.append({"goal_id": gid, "domain": domain, "verdict": "ERROR", "reason": str(e)[:80], "revisions": 0})
            print(f"ERROR ({e}) [{elapsed:.1f}s]")
        with open(OUTPUT_ROOT / "results.json", "w") as f:
            json.dump(results, f, indent=2)

    from collections import Counter
    verdicts = Counter(r["verdict"] for r in results)
    print(f"\n  Batch {batch_num} done: {verdicts.get("PASS",0)} PASS, {verdicts.get("FAIL",0)} FAIL, {verdicts.get("ERROR",0)} ERROR\n")

if __name__ == "__main__:
    main()
