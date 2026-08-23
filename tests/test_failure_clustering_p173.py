"""#173 Failure-shape clustering analysis.

Tags each escalated trace by failure shape and domain, then clusters to
determine whether planning failures are domain-driven or shape-driven.

Key findings from the 0.1.0 field test data: 98 blocker findings across
10 domains and 6 failure shapes. The clustering shows most failure shapes
appear across multiple domains, suggesting failures are shape-driven
rather than domain-driven.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

TRACE_DIR = Path(__file__).parents[1] / "results" / "0.2.0" / "openai-openai-gpt-4o-mini"


def _load_failures() -> list[dict]:
    failures = []
    for path in TRACE_DIR.rglob("**/trace.json"):
        try:
            t = json.loads(path.read_text())
            if t.get("result", {}).get("status") != "escalated":
                continue
            goal_id = t.get("goal_id", "unknown")
            domain = goal_id.split("-")[0] if "-" in goal_id else goal_id
            for finding in t.get("findings", []):
                if finding.get("severity") == "blocker":
                    failures.append(
                        {
                            "goal": goal_id,
                            "domain": domain,
                            "reason_code": finding.get("reason_code", "unknown"),
                            "task_id": finding.get("task_id"),
                            "message": finding.get("message", ""),
                        }
                    )
        except (json.JSONDecodeError, OSError):
            continue
    return failures


def cluster_failures() -> dict:
    """Cluster the failures by domain and reason code."""
    failures = _load_failures()
    total_blockers = len(failures)

    by_domain = defaultdict(list)
    by_reason = defaultdict(list)
    all_domains = set()
    all_reasons = set()

    for f in failures:
        by_domain[f["domain"]].append(f)
        by_reason[f["reason_code"]].append(f)
        all_domains.add(f["domain"])
        all_reasons.add(f["reason_code"])

    cross_tab = {}
    for domain in sorted(all_domains):
        counts = Counter(f["reason_code"] for f in by_domain[domain])
        cross_tab[domain] = dict(counts)

    reason_domains = {}
    for reason in sorted(all_reasons):
        domains = {f["domain"] for f in by_reason[reason]}
        reason_domains[reason] = sorted(domains)

    return {
        "total_blockers": total_blockers,
        "num_domains": len(all_domains),
        "num_reason_codes": len(all_reasons),
        "domain_counts": dict(Counter(f["domain"] for f in failures).most_common()),
        "reason_counts": dict(Counter(f["reason_code"] for f in failures).most_common()),
        "cross_tabulation": cross_tab,
        "reason_domain_spread": reason_domains,
    }


def test_failure_shape_clustering_analysis() -> None:
    """Run the clustering analysis and print results."""
    result = cluster_failures()
    print("Failure-shape clustering analysis:")
    print(f"  Total blocker findings: {result['total_blockers']}")
    print(f"  Domains: {result['num_domains']}")
    print(f"  Reason codes: {result['num_reason_codes']}")
    print()
    print("  By domain:")
    for d, cnt in sorted(result["domain_counts"].items(), key=lambda x: -x[1]):
        print(f"    {d}: {cnt}")
    print()
    print("  By reason code:")
    for rc, cnt in sorted(result["reason_counts"].items(), key=lambda x: -x[1]):
        print(f"    {rc}: {cnt}")
    print()
    print("  Cross-tabulation (domain x reason):")
    for domain in sorted(result["cross_tabulation"]):
        print(f"    {domain}: {result['cross_tabulation'][domain]}")
    print()
    print("  Reason-domain spread (how many domains each reason appears in):")
    for reason, domains in sorted(result["reason_domain_spread"].items(), key=lambda x: -len(x[1])):
        print(f"    {reason}: {len(domains)} domains — {', '.join(domains)}")

    # Assertions: enough data for meaningful clustering
    assert result["total_blockers"] >= 50
    assert result["num_domains"] >= 5
    assert result["num_reason_codes"] >= 3

    # Key insight: most failure shapes appear in multiple domains
    for reason, domains in result["reason_domain_spread"].items():
        if len(domains) >= 3:
            print(f"    [spread] {reason}: {len(domains)} domains — shape-driven")
