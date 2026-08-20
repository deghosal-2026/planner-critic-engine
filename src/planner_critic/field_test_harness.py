"""Field test harness — load goals, run engine, check invariants, save traces.

The harness is the core of M9. It loads Goal JSON files and their companion
assertion YAML files from a directory, runs each through ``Engine.plan()``
against a real LLM, checks invariant assertions, and saves the full trace
(plan, findings, LLM responses, pass/fail) to an output directory.

Usage from CLI:
    ``plancritic field-test run --goals docs/field-test/goals/database/``

Domain batching: pass a goals directory to run only that domain.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .engine import Engine
from .llm.registry import ProviderRegistry
from .loop import LoopConfig
from .schema.goal import Goal
from .types import Finding, PlanningError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_goal(path: Path) -> Goal:
    """Load a single Goal JSON file."""
    raw = json.loads(path.read_text())
    return Goal.model_validate(raw)


def load_assertions(path: Path) -> dict[str, Any]:
    """Load the assertion YAML for a goal.

    Returns an empty dict when the file does not exist (no-op assertions).
    """
    if not path.exists():
        return {}
    with path.open() as fh:
        return yaml.safe_load(fh) or {}


def discover_goals(goals_dir: str | Path) -> list[Path]:
    """Discover all Goal JSON files in a directory (non-recursive)."""
    root = Path(goals_dir)
    if root.is_file():
        return [root]
    return sorted(root.glob("*.json"))


# ---------------------------------------------------------------------------
# Invariant checks
# ---------------------------------------------------------------------------

def _check_approve_expected(
    result_status: str, approve_expected: bool
) -> tuple[bool, str]:
    if approve_expected:
        if result_status == "approved":
            return True, "approved as expected"
        return False, f"expected approve but got status={result_status}"
    else:
        if result_status == "escalated":
            return True, "escalated as expected"
        return False, f"expected escalate but got status={result_status}"


def _check_max_revisions(
    revision_count: int | None, max_revisions: int | None
) -> tuple[bool, str]:
    if max_revisions is None or revision_count is None:
        return True, "max_revisions not checked"
    if revision_count <= max_revisions:
        return True, f"revisions={revision_count} <= max={max_revisions}"
    return False, f"revisions={revision_count} > max={max_revisions}"


def _check_min_tasks(
    task_count: int, min_tasks: int | None
) -> tuple[bool, str]:
    if min_tasks is None:
        return True, "min_tasks not checked"
    if task_count >= min_tasks:
        return True, f"tasks={task_count} >= min={min_tasks}"
    return False, f"tasks={task_count} < min={min_tasks}"


def _check_mandatory_elements(
    task_ids: list[str], descriptions: list[str], elements: list[str] | None
) -> tuple[bool, str]:
    if not elements:
        return True, "mandatory_elements not checked"
    combined = " ".join(task_ids).lower() + " " + " ".join(descriptions).lower()
    missing = [e for e in elements if e.lower() not in combined]
    if not missing:
        return True, f"all mandatory elements present: {elements}"
    return False, f"missing mandatory elements: {missing}"


def _check_mandatory_blocker_reason_codes(
    findings: list[Finding], codes: list[str] | None
) -> tuple[bool, str]:
    if not codes:
        return True, "mandatory_blocker_reason_codes not checked"
    found_codes = {f.reason_code for f in findings if f.severity.value == "blocker"}
    missing = [c for c in codes if c not in found_codes]
    if not missing:
        return True, f"all mandatory blocker codes present: {codes}"
    return False, f"missing mandatory blocker codes: {missing}"


def _check_forbidden_blockers(
    findings: list[Finding], forbidden: list[str] | None
) -> tuple[bool, str]:
    if not forbidden:
        return True, "forbidden_blockers not checked"
    found = {
        f.reason_code
        for f in findings
        if f.severity.value == "blocker" and f.reason_code in forbidden
    }
    if not found:
        return True, "no forbidden blockers"
    return False, f"forbidden blockers found: {found}"


def _check_high_risk_attributes(
    tasks: list[dict[str, Any]],
) -> list[tuple[bool, str]]:
    results: list[tuple[bool, str]] = []
    high_risk_classes = {"high", "critical"}
    for task in tasks:
        risk = task.get("risk_class", "medium")
        if risk in high_risk_classes:
            has_ver = task.get("verification") is not None
            has_roll = task.get("rollback") is not None
            tid = task.get("id", "?")
            if not has_ver:
                results.append(
                    (False, f"high-risk task {tid} missing verification")
                )
            if not has_roll:
                results.append(
                    (False, f"high-risk task {tid} missing rollback")
                )
    if not results:
        results.append((True, "all high-risk tasks have verification and rollback"))
    return results


def check_invariants(
    result_status: str,
    findings: list[Finding],
    tasks: list[dict[str, Any]],
    revision_count: int | None,
    assertions: dict[str, Any],
) -> list[dict[str, Any]]:
    """Run all invariant checks against a goal's loop result.

    Returns a list of check dicts: {"name": str, "pass": bool, "message": str}.
    """
    inv = assertions.get("invariants", {})
    checks: list[dict[str, Any]] = []

    # approve_expected
    ae = inv.get("approve_expected", True)
    ok, msg = _check_approve_expected(result_status, ae)
    checks.append({"name": "approve_expected", "pass": ok, "message": msg})

    # max_revisions
    ok, msg = _check_max_revisions(revision_count, inv.get("max_revisions"))
    checks.append({"name": "max_revisions", "pass": ok, "message": msg})

    # min_tasks
    ok, msg = _check_min_tasks(len(tasks), inv.get("min_tasks"))
    checks.append({"name": "min_tasks", "pass": ok, "message": msg})

    # mandatory_elements
    task_ids = [t.get("id", "") for t in tasks]
    descriptions = [t.get("description", "") for t in tasks]
    ok, msg = _check_mandatory_elements(
        task_ids, descriptions, inv.get("mandatory_elements")
    )
    checks.append({"name": "mandatory_elements", "pass": ok, "message": msg})

    # mandatory_blocker_reason_codes
    ok, msg = _check_mandatory_blocker_reason_codes(
        findings, inv.get("mandatory_blocker_reason_codes")
    )
    checks.append({"name": "mandatory_blocker_reason_codes", "pass": ok, "message": msg})

    # forbidden_blockers
    ok, msg = _check_forbidden_blockers(findings, inv.get("forbidden_blockers"))
    checks.append({"name": "forbidden_blockers", "pass": ok, "message": msg})

    # high-risk task attributes
    hr_results = _check_high_risk_attributes(tasks)
    for ok, msg in hr_results:
        checks.append({"name": "high_risk_attributes", "pass": ok, "message": msg})

    return checks


# ---------------------------------------------------------------------------
# Trace saving
# ---------------------------------------------------------------------------

def _findings_to_dict(findings: list[Finding]) -> list[dict[str, Any]]:
    return [f.model_dump(mode="json") for f in findings]


def save_trace(
    goal_id: str,
    goal_dict: dict[str, Any],
    assertions_dict: dict[str, Any],
    result_status: str,
    reason_code: str | None,
    revision_count: int | None,
    llm_calls: int | None,
    plan_dict: dict[str, Any] | None,
    findings: list[Finding],
    checks: list[dict[str, Any]],
    escalation_dict: dict[str, Any] | None,
    approved_plan_dict: dict[str, Any] | None,
    error: str | None,
    duration_seconds: float,
    output_dir: Path,
) -> Path:
    """Save the full trace for one goal to a JSON file.

    Args:
        output_dir: Base domain output directory (e.g., reports/20260819/database/).
        goal_id: The goal id (used as filename).

    Returns:
        The path to the written trace file.
    """
    trace_dir = output_dir / goal_id
    trace_dir.mkdir(parents=True, exist_ok=True)

    trace = {
        "meta": {
            "goal_id": goal_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "duration_seconds": round(duration_seconds, 2),
        },
        "goal": goal_dict,
        "assertions": assertions_dict,
        "result": {
            "status": result_status,
            "reason_code": reason_code,
            "revision_count": revision_count,
            "llm_calls": llm_calls,
        },
        "plan": plan_dict,
        "findings": _findings_to_dict(findings),
        "escalation": escalation_dict,
        "approved_plan": approved_plan_dict,
        "checks": checks,
        "error": error,
        "pass": all(c["pass"] for c in checks),
    }
    trace_path = trace_dir / "trace.json"
    trace_path.write_text(json.dumps(trace, indent=2, default=str))
    return trace_path


# ---------------------------------------------------------------------------
# Domain summary
# ---------------------------------------------------------------------------

def build_domain_summary(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a summary for one domain (or the full sweep)."""
    total = len(traces)
    passed = sum(1 for t in traces if t.get("pass", False))
    failed = total - passed
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total, 2) if total > 0 else 0.0,
        "goals": [
            {
                "goal_id": t.get("meta", {}).get("goal_id", "?"),
                "pass": t.get("pass", False),
                "status": t.get("result", {}).get("status"),
                "reason_code": t.get("result", {}).get("reason_code"),
                "revision_count": t.get("result", {}).get("revision_count"),
                "task_count": len(t.get("plan", {}).get("tasks", [])) if t.get("plan") else 0,
                "finding_count": len(t.get("findings", [])),
                "error": t.get("error"),
            }
            for t in traces
        ],
    }


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def run_sweep(
    goals_dir: str | Path,
    output_dir: str | Path,
    config_path: str | Path | None = None,
    loop_config: LoopConfig | None = None,
    save_raw_llm: bool = False,
) -> dict[str, Any]:
    """Run the full field test sweep for one domain.

    Args:
        goals_dir: Directory containing Goal JSON files.
        output_dir: Where to write per-goal traces and the summary report.
        config_path: Path to the provider TOML config.
        loop_config: Loop configuration (revision cap, mode, etc.).
        save_raw_llm: When True, save raw LLM provider responses (large).

    Returns:
        A summary dict with pass/fail per goal.
    """
    goals_root = Path(goals_dir)
    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    goal_paths = discover_goals(goals_root)
    if not goal_paths:
        logger.warning("no goal files found in %s", goals_root)
        return {"total": 0, "passed": 0, "failed": 0, "goals": []}

    # Load provider config
    cfg_path = str(config_path) if config_path else "plancritic.toml"
    registry = ProviderRegistry.load(cfg_path)
    lc = loop_config or LoopConfig()

    traces: list[dict[str, Any]] = []
    planner_cache: Any = None  # cache planner across goals

    for gp in goal_paths:
        goal_id = gp.stem
        logger.info("=== %s ===", goal_id)
        goal_start = time.monotonic()

        # Load goal + assertions
        goal = load_goal(gp)
        ap = goals_root / "assertions" / f"{goal_id}.yaml"
        assertions = load_assertions(ap)

        # Build engine (reuse planner, build critic per goal)
        from .cli.plan import _CLIPlanner
        from .critique.critic import LLMCritic

        planner_provider = registry.get_provider("planner")
        critic_provider = registry.get_provider("critic")
        if planner_cache is None:
            planner_cache = _CLIPlanner(planner_provider)
        planner = planner_cache
        critic = LLMCritic(goal, critic_provider)
        engine = Engine(planner, critic, config=lc)

        # Run
        error: str | None = None
        result_status = "error"
        reason_code: str | None = None
        revision_count: int | None = None
        llm_calls: int | None = None
        plan_dict: dict[str, Any] | None = None
        findings: list[Finding] = []
        escalation_dict: dict[str, Any] | None = None
        approved_plan_dict: dict[str, Any] | None = None

        try:
            result = engine.plan(goal)
            result_status = result.status
            reason_code = result.reason_code
            revision_count = result.spend.revisions_used if result.spend else None
            llm_calls = result.spend.calls_used if result.spend else None
            findings = result.findings
            if result.plan:
                plan_dict = result.plan.model_dump(mode="json")
            if result.escalation:
                escalation_dict = result.escalation.model_dump(mode="json")
            if result.approved_plan:
                approved_plan_dict = result.approved_plan.model_dump(mode="json")
        except PlanningError as e:
            error = str(e)
            result_status = "error"
            reason_code = getattr(e, "reason_code", "planning_unavailable")
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            result_status = "error"

        duration = time.monotonic() - goal_start

        # Check invariants
        checks = check_invariants(
            result_status,
            findings,
            plan_dict.get("tasks", []) if plan_dict else [],
            revision_count,
            assertions,
        )

        # Save trace
        goal_dict = json.loads(gp.read_text()) if gp.exists() else {}
        trace_path = save_trace(
            goal_id=goal_id,
            goal_dict=goal_dict,
            assertions_dict=assertions,
            result_status=result_status,
            reason_code=reason_code,
            revision_count=revision_count,
            llm_calls=llm_calls,
            plan_dict=plan_dict,
            findings=findings,
            checks=checks,
            escalation_dict=escalation_dict,
            approved_plan_dict=approved_plan_dict,
            error=error,
            duration_seconds=duration,
            output_dir=out_root,
        )
        logger.info("  -> %s trace saved to %s", "PASS" if all(c["pass"] for c in checks) else "FAIL", trace_path)
        traces.append(json.loads(trace_path.read_text()))

    # Build domain summary
    summary = build_domain_summary(traces)
    summary_path = out_root / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str))
    logger.info("Domain summary: %d/%d passed", summary["passed"], summary["total"])
    return summary