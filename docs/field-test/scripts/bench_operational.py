"""Before/after operational benchmark (#221).

Answers the standing community question ("what changed in latency, error
rate, review time, or operator workload?") with the three engine-side metrics
computable from stored field-test traces, plus the protocol for the fourth:

* **Latency** — wall-clock seconds per goal (`duration_seconds`), reported
  separately for approved and escalated plans.
* **Reviewer burden** — findings surfaced per goal (blockers vs advisory),
  i.e. what a human reviewing the plan would have to read.
* **Operator workload** — escalation decisions demanded per 100 goals.
* **Downstream error rate** — NOT computable solo (the engine stops at
  approval). The paired-baseline protocol below hands this metric to the
  first executing runner integration.

Paired-baseline protocol (the "before" arm):
    Re-run the identical goal corpus with the critic disabled —
    ``PC_CRITIQUE_MODE=heuristic-only plancritic field-test run …`` —
    keeping provider, budget caps, and corpus fixed. Diff the two JSON
    reports; every delta is attributable to LLM-critique review. See
    [#221](https://github.com/deghosal-2026/planner-critic-engine/issues/221)
    for the acceptance table.

Pure Python over stored traces — no LLM calls, no planner runs.

Usage:
    python3 docs/field-test/scripts/bench_operational.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent          # docs/field-test/scripts
FIELD_TEST_DIR = SCRIPTS_DIR.parent.parent             # docs/field-test

REPORTS_DIRS = [
    FIELD_TEST_DIR / "v0.1.0" / "reports",
    FIELD_TEST_DIR / "v0.2.0" / "reports",
    FIELD_TEST_DIR / "v0.2.1" / "reports",
]


def _load_traces() -> list[dict]:
    """Load every trace.json with a usable result block."""
    traces: list[dict] = []
    seen: set[Path] = set()
    for base in REPORTS_DIRS:
        if not base.exists():
            continue
        for path in base.rglob("trace.json"):
            if path in seen:
                continue
            seen.add(path)
            try:
                data = json.loads(path.read_text())
                if "result" in data and "goal_id" in data:
                    traces.append(data)
            except Exception:
                continue
    return traces


def _percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile; 0 for empty input."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(pct / 100 * (len(ordered) - 1))))
    return ordered[index]


def _severity_split(findings: list[dict]) -> tuple[int, int]:
    """Return (blocker_count, advisory_count) from raw finding dicts."""
    blockers = sum(
        1 for f in findings if str(f.get("severity", "")).lower() == "blocker"
    )
    return blockers, len(findings) - blockers


def run() -> dict:
    """Compute the operational metrics and print a JSON report."""
    traces = _load_traces()
    print(f"Loaded {len(traces)} traces")

    if not traces:
        print("WARNING: no traces found — run field tests to generate them")
        return {"error": "no traces", "traces_found": 0}

    lat_approved: list[float] = []
    lat_escalated: list[float] = []
    revisions: list[int] = []
    llm_calls: list[int] = []
    blocker_counts: list[int] = []
    advisory_counts: list[int] = []
    escalations = 0

    for trace in traces:
        result = trace.get("result", {})
        duration = trace.get("duration_seconds")
        approved = str(result.get("status")) == "approved"
        if isinstance(duration, (int, float)):
            (lat_approved if approved else lat_escalated).append(float(duration))
        rev = result.get("revision_count")
        if isinstance(rev, int):
            revisions.append(rev)
        calls = result.get("llm_calls")
        if isinstance(calls, int):
            llm_calls.append(calls)

        findings = trace.get("findings") or []
        if isinstance(findings, list):
            blockers, advisories = _severity_split(findings)
            blocker_counts.append(blockers)
            advisory_counts.append(advisories)

        if not approved:
            escalations += 1

    goals = len(traces)

    def _lat_bucket(bucket: list[float]) -> dict:
        return {
            "n": len(bucket),
            "p50_s": round(_percentile(bucket, 50), 2),
            "p95_s": round(_percentile(bucket, 95), 2),
        }

    report = {
        "goals": goals,
        "latency_added": {
            "approved_plans": _lat_bucket(lat_approved),
            "escalated_plans": _lat_bucket(lat_escalated),
        },
        "reviewer_burden": {
            "mean_blockers_per_goal": round(statistics.mean(blocker_counts), 2)
            if blocker_counts else 0,
            "mean_advisories_per_goal": round(statistics.mean(advisory_counts), 2)
            if advisory_counts else 0,
        },
        "operator_workload": {
            "escalation_decisions": escalations,
            "decisions_per_100_goals": round(escalations / goals * 100, 1) if goals else 0,
        },
        "cost_proxy": {
            "mean_llm_calls_per_goal": round(statistics.mean(llm_calls), 2)
            if llm_calls else 0,
        },
        "revisions_to_resolution_median": statistics.median(revisions) if revisions else 0,
        "downstream_error_rate": {
            "status": "deferred — requires partner runner integration",
            "protocol": (
                "Paired baseline: re-run the identical corpus with "
                "PC_CRITIQUE_MODE=heuristic-only, then compare post-execution "
                "incident/rollback counts recorded by the executing adapter."
            ),
        },
        "paired_baseline_protocol": (
            "PC_CRITIQUE_MODE=heuristic-only over the same corpus/provider/caps; "
            "diff reports for the before/after delta"
        ),
    }
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    run()
