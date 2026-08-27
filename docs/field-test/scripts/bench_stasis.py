"""Family-histogram stasis benchmark (#183).

Retrospective analysis over existing field-test revision traces to measure
revision reduction from family-based convergence detection. Pure Python —
no LLM calls, no running the planner.

Usage:
    python3 docs/field-test/scripts/bench_stasis.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from planner_critic.types import Finding, Severity

REPORTS_DIR = Path(__file__).parent.parent.parent.parent / "v0.1.0" / "reports"

SEVERITY_MAP = {Severity.BLOCKER: 2, Severity.WARNING: 1, Severity.INFO: 0}


def _blocker_family_histogram(findings: list[Finding]) -> frozenset[tuple[str, int]]:
    """Compute blocker-family histogram for a revision's findings."""
    eligible = {"unsafe_sequencing", "weak_rollback", "unverified_precondition",
                "missing_verification", "missing_rollback", "dependency_cycle",
                "feasibility", "missing_steps", "risk"}
    counts: Counter[str] = Counter()
    for f in findings:
        if f.severity is not Severity.BLOCKER:
            continue
        family = f.heuristic_family.value if f.heuristic_family else f.reason_code or "unknown"
        if family in eligible:
            counts[family] += 1
    return frozenset(counts.items())


def _load_traces() -> list[dict]:
    """Load all trace.json files from the v0.1.0 reports directory."""
    traces = []
    for trace_file in REPORTS_DIR.rglob("trace.json"):
        try:
            data = json.loads(trace_file.read_text())
            if "result" in data and "findings" in data.get("result", {}):
                traces.append(data)
        except Exception:
            continue
    return traces


def _detect_stasis(histograms: list[frozenset], k: int) -> int | None:
    """Detect stasis at window K. Returns the revision where stasis is detected, or None."""
    if len(histograms) < k:
        return None
    for i in range(k - 1, len(histograms)):
        window = histograms[i - k + 1 : i + 1]
        if all(h == window[0] for h in window):
            return i
    return None


def run() -> dict:
    traces = _load_traces()
    print(f"Loaded {len(traces)} traces from {REPORTS_DIR}")

    if not traces:
        print("⚠ No traces found — run P1/P5 first to generate traces")
        return {"error": "no traces", "traces_found": 0}

    results = {"traces": len(traces), "k2": {}, "k3": {}}

    for k in (2, 3):
        total_revisions = 0
        stasis_detected = 0
        revisions_saved = 0
        false_positives = 0

        for trace in traces:
            result = trace.get("result", {})
            revisions = result.get("revisions", [])
            if not revisions:
                continue

            histograms = []
            for rev in revisions:
                findings_data = rev.get("findings", [])
                findings = []
                for fd in findings_data:
                    try:
                        findings.append(Finding.model_validate(fd))
                    except Exception:
                        continue
                histograms.append(_blocker_family_histogram(findings))

            total_revisions += len(histograms)
            stasis_rev = _detect_stasis(histograms, k)

            if stasis_rev is not None:
                stasis_detected += 1
                saved = len(histograms) - stasis_rev - 1
                revisions_saved += saved
                if stasis_rev + k < len(histograms):
                    future = histograms[stasis_rev + k]
                    if future != histograms[stasis_rev]:
                        false_positives += 1

        results[f"k{k}"] = {
            "stasis_detected": stasis_detected,
            "total_revisions": total_revisions,
            "revisions_saved": revisions_saved,
            "false_positives": false_positives,
            "gross_savings_pct": (revisions_saved / total_revisions * 100) if total_revisions else 0,
            "false_positive_rate": (false_positives / stasis_detected * 100) if stasis_detected else 0,
        }

    print(json.dumps(results, indent=2))
    k2 = results.get("k2", {})
    gross = k2.get("gross_savings_pct", 0)
    fpr = k2.get("false_positive_rate", 0)
    if gross >= 20 and fpr <= 5:
        print(f"\n✅ K=2: {gross:.1f}% savings at {fpr:.1f}% FPR — target met")
    else:
        print(f"\n❌ K=2: {gross:.1f}% savings at {fpr:.1f}% FPR — target not met")
    return results


if __name__ == "__main__":
    run()
