#!/usr/bin/env python3
"""Batch 23: 5 scenarios — runs each goal individually via run_core_api."""
import json, time
from pathlib import Path

GOALS_ROOT = Path("docs/field-test/goals")
OUTPUT_ROOT = Path("docs/field-test/v0.2.0/reports/p5-sweep")
RESULTS_FILE = OUTPUT_ROOT / "results.json"
CONFIG = "plancritic-fieldtest.toml"

SCENARIOS = [
    ("disaster-recovery", "dr-01-failover-drill"),
    ("disaster-recovery", "dr-02-point-in-time-restore"),
    ("disaster-recovery", "dr-03-both-sides-failover"),
    ("erp", "erp-01-module-adoption"),
    ("erp", "erp-02-workflow-platform"),
]

def load_results():
    if RESULTS_FILE.exists():
        try:
            return json.loads(RESULTS_FILE.read_text())
        except Exception:
            return []
    return []

def main():
    import yaml
    from planner_critic.field_test_harness import run_core_api
    from planner_critic.llm.registry import ProviderRegistry
    from planner_critic.loop import LoopConfig
    from planner_critic.schema.goal import Goal

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    results = load_results()
    total = len(SCENARIOS)
    existing = {r["goal_id"] for r in results}

    for i, (domain, gid) in enumerate(SCENARIOS, 1):
        if gid in existing:
            print(f"[{i}/{total}] {gid} - skip (already run)")
            continue
        goal_path = GOALS_ROOT / domain / f"{gid}.json"
        assert_path = GOALS_ROOT / domain / "assertions" / f"{gid}.yaml"
        goal = Goal.model_validate(json.loads(goal_path.read_text()))
        assertions = yaml.safe_load(assert_path.read_text())
        start = time.monotonic()
        try:
            registry = ProviderRegistry.load(CONFIG)
            config = LoopConfig(mode="deterministic-first", revision_cap=4)
            tr = run_core_api(goal, registry, config, assertions, OUTPUT_ROOT / gid)
            status = tr.get("result", {}).get("status", "unknown")
            reason = tr.get("result", {}).get("reason_code", "")
            revs = tr.get("result", {}).get("revision_count", "?")
            verdict = "PASS" if status == "approved" else "FAIL"
            elapsed = time.monotonic() - start
            results.append({"goal_id": gid, "domain": domain, "verdict": verdict, "reason": reason, "revisions": revs})
            print(f"[{i}/{total}] {verdict} {gid} ({reason}) rev={revs} [{elapsed:.1f}s]")
        except Exception as e:
            elapsed = time.monotonic() - start
            results.append({"goal_id": gid, "domain": domain, "verdict": "ERROR", "reason": str(e)[:80], "revisions": 0})
            print(f"[{i}/{total}] ERROR {gid} ({e}) [{elapsed:.1f}s]")
        RESULTS_FILE.write_text(json.dumps(results, indent=2))

    print(f"\nDone: {len(results)} results")
    RESULTS_FILE.write_text(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
