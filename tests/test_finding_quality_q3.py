"""§1 Q3 finding-quality audit on all stored traces (#97).

Classifies every finding from stored traces on three axes:
1. Specificity — names a concrete action/artifact vs generic hedging
2. Actionability — implies a corrective step the planner could apply
3. Task-ID linkage — references a real task id from the plan

Produces metrics: % noise, % specific, % actionable, % task-linked,
noise top-10, per-domain + per-severity noise rates.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

TRACE_DIR = Path(__file__).parents[1] / "docs" / "field-test" / "reports" / "0.1.0" / "full-sweep"

_NOISE_PATTERNS = [
    re.compile(r"be careful", re.I),
    re.compile(r"make sure", re.I),
    re.compile(r"ensure\s+correctness", re.I),
    re.compile(r"^[Cc]onsider\s", re.I),
    re.compile(r"^[Ii]t is (advisable|recommended)", re.I),
    re.compile(r"^[Tt]his (plan|step|task) (appears|seems|looks)", re.I),
    re.compile(r"double-check", re.I),
    re.compile(r"^[Mm]onitor\s", re.I),
]

_SPECIFIC_PATTERNS = [
    re.compile(r"(?i)backup"),
    re.compile(r"(?i)verif(y|ication|ied)"),
    re.compile(r"(?i)rollback"),
    re.compile(r"(?i)snapshot"),
    re.compile(r"(?i)ALTER|DROP|CREATE|TRUNCATE|INSERT|UPDATE|DELETE"),
    re.compile(r"(?i)terraform|kubectl|helm|aws|gcloud|azure"),
    re.compile(r"(?i)test|migration|deploy"),
    re.compile(r"(?i)schema|database|pipeline"),
    re.compile(r"task\s+(id\s*[:=])?\s*\w+", re.I),
]


def _load_traces() -> list[dict]:
    traces = []
    for path in TRACE_DIR.rglob("**/trace.json"):
        try:
            traces.append(json.loads(path.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    return traces


def _is_noise(message: str) -> bool:
    return any(p.search(message) for p in _NOISE_PATTERNS)


def _is_specific(message: str) -> bool:
    return any(p.search(message) for p in _SPECIFIC_PATTERNS)


def _is_actionable(message: str) -> bool:
    actionable_keywords = [
        "add ",
        "create ",
        "implement ",
        "run ",
        "execute ",
        "write ",
        "use ",
        "configure ",
        "modify ",
        "update ",
        "fix ",
        "patch ",
        "backup ",
        "verify ",
        "rollback ",
        "restore ",
        "rename ",
        "schedule ",
        "review ",
        "test ",
        "sign ",
        "check ",
        "validate ",
        "must ",
        "should ",
        "need to ",
        "required to ",
    ]
    msg = message.lower()
    return any(kw in msg for kw in actionable_keywords)


def audit_traces() -> dict:
    """Run the Q3 finding-quality audit over all stored traces."""
    traces = _load_traces()
    total_findings = 0
    noise_count = 0
    specific_count = 0
    actionable_count = 0
    task_linked_count = 0
    noise_examples: list[tuple[str, str, str]] = []
    domain_stats: dict[str, dict] = {}
    severity_stats: dict[str, dict] = {}

    for trace in traces:
        goal_id = trace.get("goal_id", "unknown")
        domain = goal_id.split("-")[0] if "-" in goal_id else goal_id
        if domain not in domain_stats:
            domain_stats[domain] = {"total": 0, "noise": 0}
        for finding in trace.get("findings", []):
            total_findings += 1
            domain_stats[domain]["total"] += 1
            severity = finding.get("severity", "unknown")
            if severity not in severity_stats:
                severity_stats[severity] = {"total": 0, "noise": 0}
            severity_stats[severity]["total"] += 1
            message = finding.get("message", "")
            task_id = finding.get("task_id")

            if _is_noise(message):
                noise_count += 1
                domain_stats[domain]["noise"] += 1
                severity_stats[severity]["noise"] += 1
                noise_examples.append((message[:80], domain, severity))
            if _is_specific(message):
                specific_count += 1
            if _is_actionable(message):
                actionable_count += 1
            if task_id:
                task_linked_count += 1

    noise_examples.sort(key=lambda x: len(x[0]), reverse=True)
    noise_top10 = [{"message": m, "domain": d, "severity": s} for m, d, s in noise_examples[:10]]

    return {
        "total_findings": total_findings,
        "noise_count": noise_count,
        "noise_pct": round(noise_count / total_findings * 100, 1) if total_findings else 0,
        "specific_count": specific_count,
        "specific_pct": round(specific_count / total_findings * 100, 1) if total_findings else 0,
        "actionable_count": actionable_count,
        "actionable_pct": round(actionable_count / total_findings * 100, 1)
        if total_findings
        else 0,
        "task_linked_count": task_linked_count,
        "task_linked_pct": round(task_linked_count / total_findings * 100, 1)
        if total_findings
        else 0,
        "noise_top10": noise_top10,
        "domain_breakdown": {
            d: {"total": s["total"], "noise": s["noise"]} for d, s in sorted(domain_stats.items())
        },
        "severity_breakdown": {
            s: {"total": st["total"], "noise": st["noise"]}
            for s, st in sorted(severity_stats.items())
        },
    }


def test_q3_finding_quality_noise_rate() -> None:
    """Q3: noise findings are within tolerance across all stored traces."""
    result = audit_traces()
    blocker_noise = result["severity_breakdown"].get("blocker", {}).get("noise", 0)
    blocker_total = result["severity_breakdown"].get("blocker", {}).get("total", 1)
    blocker_noise_pct = round(blocker_noise / blocker_total * 100, 1) if blocker_total else 0
    print(
        f"Q3: {result['total_findings']} findings: "
        f"{result['specific_pct']}% specific, "
        f"{result['actionable_pct']}% actionable, "
        f"{result['task_linked_pct']}% task-linked. "
        f"Blocker noise: {blocker_noise_pct}%"
    )
    print("Q3 noise top-10:")
    for item in result["noise_top10"]:
        print(f"  [{item['severity']}] {item['domain']}: {item['message']}")
    print(f"Q3 domain breakdown: {json.dumps(result['domain_breakdown'], indent=2)}")
    print(f"Q3 severity breakdown: {json.dumps(result['severity_breakdown'], indent=2)}")

    if result["severity_breakdown"].get("blocker", {}).get("total", 0) > 0:
        assert blocker_noise_pct <= 5.0, "Q3 blocker noise too high"
