#!/usr/bin/env python3
"""Batch 12: 5 scenarios — runs each goal individually via run_core_api."""
import json
import time
from pathlib import Path

GOALS_ROOT = Path("docs/field-test/goals")
OUTPUT_ROOT = Path("docs/field-test/reports/0.1.0-08.20.2026/remain-scenario")
RESULTS_FILE = OUTPUT_ROOT / "results.json"
CONFIG = "plancritic-fieldtest.toml"

# Batch 12 scenarios:
#   msg-01-kafka-pulsar-migration (messaging)
#   msg-02-dlq-restructure (messaging)
#   msg-03-event-schema-versioning (messaging)
#   mch-01-env-promotion (mechanism-targeted)
#   mch-02-parallel-fanout (mechanism-targeted)

SCENARIOS = [
    ("messaging", "msg-01-kafka-pulsar-migration"),
    ("messaging", "msg-02-dlq-restructure"),
    ("messaging", "msg-03-event-schema-versioning"),
    ("mechanism-targeted", "mch-01-env-promotion"),
    ("mechanism-targeted", "mch-02-parallel-fanout"),
]

def load_results():
    """Load existing results so multiple batches append instead of overwrite."""
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

    # Skip goals already in results
    existing = {r["goal_id"] for r in results}

    print(f"\n{'='*60}")
    print(f"  Batch 12: {total} scenarios")
    print(f"  Output: {OUTPUT_ROOT}")
    print(f"{'='*60}\n")

    registry = ProviderRegistry.load(CONFIG)
    lc = LoopConfig()

    for i, (domain, gid) in enumerate(SCENARIOS, 1):
        if gid in existing:
            print(f"  [{i}/{total}] {gid:<40} SKIP (already run)")
            continue

        goal_path = GOALS_ROOT / domain / f"{gid}.json"
        assert_path = GOALS_ROOT / domain / "assertions" / f"{gid}.yaml"

        goal = Goal.model_validate(json.loads(goal_path.read_text()))
        assertions = {}
        if assert_path.exists():
            assertions = yaml.safe_load(assert_path.read_text()) or {}

        out_dir = OUTPUT_ROOT / gid
        out_dir.mkdir(parents=True, exist_ok=True)
        core_out = out_dir / "core-api" / gid
        core_out.mkdir(parents=True, exist_ok=True)

        print(f"  [{i}/{total}] {gid:<40} ... ", end="", flush=True)
        start = time.monotonic()

        try:
            tr = run_core_api(goal, assertions, None, registry, lc, core_out)
            elapsed = time.monotonic() - start

            status = tr.get("result", {}).get("status", "unknown")
            reason = tr.get("result", {}).get("reason_code", "unknown")
            revs = tr.get("result", {}).get("revision_count", "?")
            verdict = "PASS" if status == "approved" else "FAIL"
            results.append({"goal_id": gid, "domain": domain, "verdict": verdict, "reason": reason, "revisions": revs})
            print(f"{verdict} ({reason}) rev={revs} [{elapsed:.1f}s]")
        except Exception as e:
            elapsed = time.monotonic() - start
            results.append({"goal_id": gid, "domain": domain, "verdict": "ERROR", "reason": str(e)[:80], "revisions": 0})
            print(f"ERROR ({e}) [{elapsed:.1f}s]")

        with open(RESULTS_FILE, "w") as f:
            json.dump(results, f, indent=2)

    from collections import Counter
    batch_results = [r for r in results if any(r["goal_id"] == gid for _, gid in SCENARIOS)]
    verdicts = Counter(r["verdict"] for r in batch_results)
    print(f"\n  Batch 12 done: {verdicts.get('PASS',0)} PASS, {verdicts.get('FAIL',0)} FAIL, {verdicts.get('ERROR',0)} ERROR")
    print(f"  Total results so far: {len(results)}\n")

if __name__ == "__main__":
    main()
