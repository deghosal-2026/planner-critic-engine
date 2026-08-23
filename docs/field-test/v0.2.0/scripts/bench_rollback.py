"""Rollback credibility field test (#182).

Measures gate false-negative rate and critic recall for rollback-related
findings across domains. Uses hermetic seeded plans — no LLM required.

Usage:
    python3 docs/field-test/v0.2.0/scripts/bench_rollback.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from planner_critic.gates import run_deterministic_gates
from planner_critic.schema.plan import PlanVersion

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "tests"))
from conftest import make_plan, make_task  # type: ignore[import-not-found]


def _credibility_plan(rollback_pattern: str) -> PlanVersion:
    """Build a plan with a specific rollback credibility pattern."""
    if rollback_pattern == "none":
        return make_plan(tasks=[make_task("t1", risk_class="critical", blast_radius="high")])
    if rollback_pattern == "weak":
        return make_plan(tasks=[make_task(
            "t1", risk_class="critical", blast_radius="high",
            rollback={"trigger": "fail", "action": "revert", "safety_guard": "none"},
        )])
    return make_plan(tasks=[make_task(
        "t1", risk_class="critical", blast_radius="high",
        rollback={"trigger": "fail", "action": "revert", "safety_guard": "backup_confirmed"},
        verification={"what": "check", "how": "manual", "expected": "pass"},
    )])


PATTERNS = ["none", "weak", "strong"]
DOMAINS = ["database", "kubernetes", "cicd", "infrastructure", "data",
           "incident-response", "multi-cloud", "architecture"]


def run() -> dict:
    results = {"domains": len(DOMAINS), "patterns": PATTERNS, "per_domain": {}}
    total = 0
    gate_false_negatives = 0

    for domain in DOMAINS:
        domain_result = {}
        for pattern in PATTERNS:
            plan = _credibility_plan(pattern)
            findings = run_deterministic_gates(plan)
            blockers = [f for f in findings if f.severity.value == "blocker"]
            has_rollback_finding = any("rollback" in (f.reason_code or "") for f in findings)
            total += 1
            if pattern in ("none", "weak") and not blockers:
                gate_false_negatives += 1
            domain_result[pattern] = {
                "blockers": len(blockers),
                "has_rollback_finding": has_rollback_finding,
            }
        results["per_domain"][domain] = domain_result

    results["total"] = total
    results["gate_false_negative_rate"] = gate_false_negatives / total if total else 0
    results["target"] = "< 5%"
    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    run()
