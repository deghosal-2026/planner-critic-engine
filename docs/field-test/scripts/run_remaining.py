#!/usr/bin/env python3
"""Run the 61 remaining field-test scenarios one at a time into remain-scenario/.

Usage:
    python3 run_remaining.py [--max N] [--skip-existing]

--max N       Run at most N scenarios (default: all 61)
--skip-existing  Skip goals that already have a trace.json in the output dir
"""
import argparse, json, os, sys, time
from pathlib import Path

GOALS_ROOT = Path("docs/field-test/goals")
OUTPUT_ROOT = Path("docs/field-test/reports/0.1.0-08.20.2026/remain-scenario")
CONFIG = "plancritic-fieldtest.toml"
DIMENSIONS = ["core-api"]

# The 61 new scenarios (domain, goal_id)
SCENARIOS = [
    # Existing domains — 27 goals
    ("database", "db-09-cdc-shift"),
    ("database", "db-10-multi-tenant-split"),
    ("database", "db-11-read-replica-routing"),
    ("database", "db-12-major-version-upgrade"),
    ("kubernetes", "k8s-09-cluster-autoscaler"),
    ("kubernetes", "k8s-10-csi-storageclass-migration"),
    ("kubernetes", "k8s-11-node-taint-specialized"),
    ("cicd", "ci-09-monorepo-ci-split"),
    ("cicd", "ci-10-trunk-based-promo"),
    ("cicd", "ci-11-supply-chain-sbom"),
    ("incident-response", "ir-07-emergency-cve-patching"),
    ("incident-response", "ir-08-ransomware-containment"),
    ("incident-response", "ir-09-root-credential-rotation"),
    ("incident-response", "ir-10-accidental-deletion"),
    ("infrastructure", "inf-08-cross-account-peering"),
    ("infrastructure", "inf-09-ami-pipeline"),
    ("infrastructure", "inf-10-egress-proxy-migration"),
    ("observability", "obs-07-distributed-tracing"),
    ("observability", "obs-08-log-retention-tiering"),
    ("observability", "obs-09-oncall-escalation"),
    ("architecture", "arch-06-sync-to-async"),
    ("architecture", "arch-07-graphql-federation"),
    ("data", "data-06-cdc-rebuild"),
    ("data", "data-07-feature-store"),
    ("platform", "plat-07-tf-provider-freeze"),
    ("platform", "plat-08-repo-permission-model"),
    ("platform", "plat-09-artifact-signing"),
    # New domains — 35 goals
    ("greenfield", "gf-01-net-new-microservice"),
    ("greenfield", "gf-02-eks-bootstrap"),
    ("greenfield", "gf-03-landing-zone"),
    ("decommissioning", "dc-01-eks-retirement"),
    ("decommissioning", "dc-02-app-decommission"),
    ("disaster-recovery", "dr-01-failover-drill"),
    ("disaster-recovery", "dr-02-point-in-time-restore"),
    ("disaster-recovery", "dr-03-both-sides-failover"),
    ("compliance", "cm-01-pci-scope-reduction"),
    ("compliance", "cm-02-gdpr-retention"),
    ("compliance", "cm-03-pii-redaction"),
    ("identity-access", "id-01-idp-migration"),
    ("identity-access", "id-02-zero-trust-rollout"),
    ("serverless", "sf-01-ec2-to-lambda"),
    ("serverless", "sf-02-cdn-origin-migration"),
    ("adversarial-policy", "adv-06-policy-violation"),
    ("adversarial-policy", "adv-07-prompt-injection"),
    ("adversarial-policy", "adv-08-disguised-exfiltration"),
    ("networking", "net-01-vpc-peering-migration"),
    ("networking", "net-02-east-west-firewall"),
    ("networking", "net-03-tls-termination-move"),
    ("finops", "fin-01-commit-plan"),
    ("finops", "fin-02-spot-migration"),
    ("finops", "fin-03-budget-alert-rollout"),
    ("ai-genai", "ai-01-llm-gateway"),
    ("ai-genai", "ai-02-embedding-index-migration"),
    ("ai-genai", "ai-03-model-serving-migration"),
    ("ai-genai", "ai-04-rag-pipeline"),
    ("messaging", "msg-01-kafka-pulsar-migration"),
    ("messaging", "msg-02-dlq-restructure"),
    ("messaging", "msg-03-event-schema-versioning"),
    ("mechanism-targeted", "mch-01-env-promotion"),
    ("mechanism-targeted", "mch-02-parallel-fanout"),
    ("mechanism-targeted", "mch-03-partial-reversibility"),
    ("mechanism-targeted", "mch-04-blast-radius"),
]

def parse_verdict(trace_path):
    """Extract verdict from a trace.json file."""
    try:
        t = json.loads(trace_path.read_text())
        result = t.get("result", {})
        status = result.get("status", "unknown")
        reason = result.get("reason_code", "unknown")
        revs = result.get("revision_count", "?")
        return status, reason, revs
    except Exception:
        return "error", "parse_error", "?"

def main():
    parser = argparse.ArgumentParser(description="Run 61 remaining field-test scenarios")
    parser.add_argument("--max", type=int, default=999, help="Max scenarios to run")
    parser.add_argument("--skip-existing", action="store_true", help="Skip goals with existing trace.json")
    parser.add_argument("--goals", type=str, default=None,
                        help="Comma-separated goal IDs or domain names to run (e.g. 'db-09,k8s-09' or 'greenfield,networking'). "
                             "Default: all 61 scenarios.")
    args = parser.parse_args()

    from planner_critic.field_test_harness import run_sweep

    # Filter scenarios if --goals is provided
    scenarios = SCENARIOS
    if args.goals:
        wanted = {g.strip() for g in args.goals.split(",")}
        scenarios = [(d, g) for d, g in SCENARIOS if g in wanted or d in wanted]
        if not scenarios:
            print(f"No scenarios matched: {args.goals}")
            print(f"Available: {', '.join(g for _, g in SCENARIOS)}")
            return 1

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    results = []
    total = min(len(scenarios), args.max)

    print(f"\n{'='*60}")
    print(f"  Running {total} of {len(scenarios)} scenarios" + (f" (filtered: {args.goals})" if args.goals else ""))
    print(f"  Output: {OUTPUT_ROOT}")
    print(f"  Config: {CONFIG}")
    print(f"{'='*60}\n")

    for i, (domain, gid) in enumerate(scenarios, 1):
        if i > args.max:
            break

        goal_dir = GOALS_ROOT / domain
        out_dir = OUTPUT_ROOT / gid

        # Check if already run
        trace_path = out_dir / "core-api" / gid / "trace.json"
        if args.skip_existing and trace_path.exists():
            status, reason, revs = parse_verdict(trace_path)
            verdict = "PASS" if status == "approved" else "FAIL"
            results.append({"goal_id": gid, "domain": domain, "verdict": verdict,
                            "reason": reason, "revisions": revs})
            print(f"  [{i:2d}/{total}] {gid:<40} SKIP (exists) → {verdict} ({reason})")
            continue

        print(f"  [{i:2d}/{total}] {gid:<40} ... ", end="", flush=True)
        start = time.monotonic()

        try:
            run_sweep(
                goals_root=goal_dir,
                output_dir=out_dir,
                dimensions=DIMENSIONS,
                config_path=CONFIG,
            )
            elapsed = time.monotonic() - start

            # Find the trace
            trace_path = out_dir / "core-api" / gid / "trace.json"
            if trace_path.exists():
                status, reason, revs = parse_verdict(trace_path)
                verdict = "PASS" if status == "approved" else "FAIL"
                results.append({"goal_id": gid, "domain": domain, "verdict": verdict,
                                "reason": reason, "revisions": revs})
                print(f"{verdict} ({reason}) rev={revs} [{elapsed:.1f}s]")
            else:
                # Try alternate path
                traces = list(out_dir.rglob("trace.json"))
                if traces:
                    status, reason, revs = parse_verdict(traces[0])
                    verdict = "PASS" if status == "approved" else "FAIL"
                    results.append({"goal_id": gid, "domain": domain, "verdict": verdict,
                                    "reason": reason, "revisions": revs})
                    print(f"{verdict} ({reason}) rev={revs} [{elapsed:.1f}s]")
                else:
                    results.append({"goal_id": gid, "domain": domain, "verdict": "ERROR",
                                    "reason": "no_trace", "revisions": 0})
                    print(f"ERROR (no trace) [{elapsed:.1f}s]")
        except Exception as e:
            elapsed = time.monotonic() - start
            results.append({"goal_id": gid, "domain": domain, "verdict": "ERROR",
                            "reason": str(e)[:80], "revisions": 0})
            print(f"ERROR ({e}) [{elapsed:.1f}s]")

        # Save results incrementally
        results_path = OUTPUT_ROOT / "results.json"
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    from collections import Counter
    verdicts = Counter(r["verdict"] for r in results)
    print(f"  Total: {len(results)}")
    print(f"  PASS:  {verdicts.get('PASS', 0)}")
    print(f"  FAIL:  {verdicts.get('FAIL', 0)}")
    print(f"  ERROR: {verdicts.get('ERROR', 0)}")
    print(f"\n  Results: {OUTPUT_ROOT / 'results.json'}")
    print()

if __name__ == "__main__":
    main()
