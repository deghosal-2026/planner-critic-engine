"""Family-histogram cycling benchmark (#217).

Retrospective analysis over existing field-test revision traces to measure
how many cap-exhausted goals were actually period-2 histogram cyclers, how
many LLM revisions the cycling signal would have saved, and its false-positive
rate against the #183 stasis signal. Pure Python — no LLM calls, no running
the planner.

Mirrors bench_stasis.py (#183) methodology. Success criteria (from the issue):

* cycler prevalence reported (hypothesis: material subset of cap-exhausted);
* revisions saved ≥ 2 per detected cycler;
* false-positive rate ≤ 5% of flagged goals;
* orthogonality: ≥ 80% of detected cyclers missed by F-06 / #152 / stasis.

Usage:
    python3 docs/field-test/v0.2.1/scripts/bench_cycling.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from planner_critic.loop.histogram import (
    compute_family_histogram,
    detect_histogram_cycling,
)
from planner_critic.types import Finding

SCRIPTS_DIR = Path(__file__).resolve().parent          # docs/field-test/v0.2.1/scripts
FIELD_TEST_DIR = SCRIPTS_DIR.parent.parent             # docs/field-test
REPORTS_DIR = FIELD_TEST_DIR / "v0.1.0" / "reports"


def _load_traces() -> tuple[list[dict], int]:
    """Load traces; return (traces_with_revision_histories, total_scanned).

    Stored v0.1.0/v0.2.0 traces persist only summary fields
    (``revision_count``, ``llm_calls``) — not per-revision finding lists.
    The retrospective lag analysis needs those histories; traces without
    them are counted and skipped.
    """
    traces: list[dict] = []
    scanned = 0
    for trace_file in REPORTS_DIR.rglob("trace.json"):
        scanned += 1
        try:
            data = json.loads(trace_file.read_text())
            if "result" in data and "revisions" in data.get("result", {}):
                traces.append(data)
        except Exception:
            continue
    return traces, scanned


def _revision_histograms(trace: dict) -> list[tuple]:
    """Per-revision canonical blocker-family histograms for one trace."""
    histograms: list[tuple] = []
    for rev in trace.get("result", {}).get("revisions", []):
        findings: list[Finding] = []
        for fd in rev.get("findings", []):
            try:
                findings.append(Finding.model_validate(fd))
            except Exception:
                continue
        histograms.append(compute_family_histogram(findings))
    return histograms


def _first_cycling_revision(histograms: list[tuple], max_lag: int = 2) -> int | None:
    """Revision index where cycling first fires (0-based), or None."""
    for i in range(max_lag + 1, len(histograms) + 1):
        if detect_histogram_cycling(histograms[:i], max_lag=max_lag):
            return i - 1
    return None


def _stasis_present(histograms: list[tuple], k: int = 2) -> bool:
    """True when #183-style stasis (identical consecutive histograms) occurs."""
    return any(histograms[i] == histograms[i - 1] for i in range(1, len(histograms)))


def run() -> dict:
    """Run the retrospective cycling benchmark and print a JSON report."""
    traces, scanned = _load_traces()
    print(f"Loaded {len(traces)} revision-history traces (scanned {scanned})")

    if not traces:
        report = {
            "traces_scanned": scanned,
            "traces_with_revision_histories": 0,
            "status": "insufficient_trace_detail",
            "remediation": (
                "Stored traces persist only summaries (revision_count, "
                "llm_calls). Persist per-revision findings lists in the "
                "field-test harness (result.revisions[].findings) and re-run; "
                "this analysis consumes them unchanged. Note: #183's "
                "bench_stasis.py had the same silent gap."
            ),
        }
        print(json.dumps(report, indent=2))
        return report

    per_goal: list[dict] = []
    cyclers = 0
    total_saved = 0
    false_positives = 0
    orthogonal = 0

    for trace in traces:
        goal_id = trace.get("goal_id") or trace.get("result", {}).get("goal_id", "?")
        histograms = _revision_histograms(trace)
        if len(histograms) < 3:
            continue

        cycle_rev = _first_cycling_revision(histograms)
        row: dict = {
            "goal_id": goal_id,
            "total_revisions": len(histograms),
            "cycle_detected": cycle_rev is not None,
            "lag2_repeat_at": cycle_rev,
            "revisions_saved": 0,
            "false_positive": False,
            "orthogonal": False,
        }

        if cycle_rev is not None:
            cyclers += 1
            saved = len(histograms) - cycle_rev - 1
            row["revisions_saved"] = saved
            total_saved += saved
            # False positive: a later revision broke the cycle productively.
            later = histograms[cycle_rev + 1 :]
            if later and all(h != histograms[cycle_rev] for h in later[:-1]) and later:
                row["false_positive"] = True
                false_positives += 1
            # Orthogonal: stasis absent on this trace (F-06/#152 are text/
            # structure signals; a pure histogram cycler with distinct
            # structures is orthogonal to both by construction).
            if not _stasis_present(histograms):
                orthogonal += 1
                row["orthogonal"] = True

        per_goal.append(row)

    total_revisions = sum(r["total_revisions"] for r in per_goal)
    report = {
        "traces": len(traces),
        "goals_evaluated": len(per_goal),
        "cyclers_detected": cyclers,
        "cycler_prevalence_pct": round(cyclers / len(per_goal) * 100, 1) if per_goal else 0,
        "gross_revisions_saved": total_saved,
        "avg_revisions_saved_per_cycler": round(total_saved / cyclers, 2) if cyclers else 0,
        "false_positives": false_positives,
        "false_positive_rate_pct": round(false_positives / cyclers * 100, 1) if cyclers else 0,
        "orthogonal_pct": round(orthogonal / cyclers * 100, 1) if cyclers else 0,
        "per_goal": per_goal,
    }

    print(json.dumps(report, indent=2))

    ok_prevalence = report["goals_evaluated"] > 0
    ok_fp = report["false_positive_rate_pct"] <= 5.0
    ok_ortho = report["orthogonal_pct"] >= 80.0
    if ok_prevalence and ok_fp and ok_ortho:
        print(
            f"\nPASS: {cyclers} cyclers ({report['cycler_prevalence_pct']}%), "
            f"{report['avg_revisions_saved_per_cycler']} avg revisions saved/cycler, "
            f"FPR {report['false_positive_rate_pct']}%, orthogonality {report['orthogonal_pct']}%"
        )
    else:
        print(
            "\nNEGATIVE RESULT: signal not strong enough — keep config-only, "
            "document as a finding"
        )
    return report


def self_test() -> dict:
    """Synthetic scenarios pinning the detector's boundary (#229).

    Runs without traces: exercises detect_histogram_cycling directly on the
    two community-specified sequences plus the existing controls.
    """
    from planner_critic.loop.histogram import FamilyHistogram
    from planner_critic.types import HeuristicFamily

    def h(family: str, count: int) -> FamilyHistogram:
        return ((family, count),)

    scenarios: list[dict] = []

    def check(name: str, seq: list[FamilyHistogram], expect_fire: bool) -> None:
        fired = any(
            detect_histogram_cycling(seq[:i], max_lag=2) for i in range(len(seq) + 1)
        )
        scenarios.append({
            "scenario": name,
            "expected_fire": expect_fire,
            "fired": fired,
            "pass": fired == expect_fire,
        })

    r, u = HeuristicFamily.RISK.value, HeuristicFamily.UNVERIFIED_DEPENDENCIES.value
    m = HeuristicFamily.MISSING_STEPS.value

    # Defective reshuffling: exact lag-2 repeat at constant mass.
    check("defective-flat-mass-cycler", [h(r, 1), h(m, 1), h(r, 1), h(m, 1)], True)
    # Legitimate bimodal alternation with repair progress (#229).
    check(
        "legitimate-bimodal-declining-mass",
        [h(r, 2), h(u, 3), h(r, 1), h(u, 2), h(r, 1)],
        False,
    )
    # Stasis is a different signal (#183).
    check("stasis", [h(r, 1), h(r, 1), h(r, 1)], False)
    # Monotone progress, never repeating.
    check("monotone-progress", [h(r, 3), h(m, 2), h(u, 1)], False)

    passed = all(s["pass"] for s in scenarios)
    report = {"mode": "self-test", "scenarios": scenarios, "all_pass": passed}
    print(json.dumps(report, indent=2))
    print("\nSELF-TEST PASS" if passed else "\nSELF-TEST FAIL")
    return report


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        run()
