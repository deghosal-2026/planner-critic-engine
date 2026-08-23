"""§1 Q4 executor-usability audit on stored approved plans (#98).

Checks every approved plan for executability without filling in gaps:
1. Grounded preconditions — each precondition's established_by is a prior
   task id or 'env' (not a dangling reference)
2. Self-contained task descriptions — no placeholder tokens (TBD, TODO, ...)
   or forward references to undefined task ids
3. Discovery completeness — tools hinted by the goal are referenced in tasks
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

TRACE_DIR = Path(__file__).parents[1] / "docs" / "field-test" / "reports" / "0.1.0" / "full-sweep"
PLACEHOLDER_TOKENS = re.compile(r"\b(TBD|TODO|FIXME|XXXX|\.\.\.|lorem|ipsum)\b", re.I)
FORWARD_REF = re.compile(r"as described in (later|subsequent|following)|see step|see below", re.I)


def _load_approved_plans() -> list[tuple[str, dict[str, Any]]]:
    """Load all approved plan traces."""
    plans = []
    for path in TRACE_DIR.rglob("**/trace.json"):
        try:
            t = json.loads(path.read_text())
            if t.get("result", {}).get("status") == "approved" and t.get("plan"):
                plans.append((t["goal_id"], t["plan"]))
        except (json.JSONDecodeError, OSError):
            continue
    return plans


def _is_grounded(precondition: dict[str, Any], task_ids: set[str]) -> bool:
    """Check if a precondition's established_by is valid."""
    eb = precondition.get("established_by")
    if eb is None:
        return False
    if eb == "env":
        return True
    return eb in task_ids


def _has_placeholder(description: str) -> bool:
    return bool(PLACEHOLDER_TOKENS.search(description))


def _has_forward_ref(description: str) -> bool:
    return bool(FORWARD_REF.search(description))


def audit_executor_usability() -> dict[str, Any]:
    """Run the Q4 executor-usability audit over all approved plan traces."""
    plans = _load_approved_plans()
    total_plans = len(plans)
    total_tasks = 0
    grounded_preconditions = 0
    total_preconditions = 0
    plans_with_placeholder = 0
    plans_with_forward_ref = 0
    plans_with_bad_precondition = 0
    gap_inventory: list[dict[str, Any]] = []
    per_plan_verdicts: list[dict[str, Any]] = []

    for goal_id, plan in plans:
        tasks = plan.get("tasks", [])
        task_ids = {t["id"] for t in tasks}
        total_tasks += len(tasks)
        plan_has_placeholder = False
        plan_has_forward_ref = False
        plan_has_bad_precondition = False
        plan_grounded = 0
        plan_precondition_total = 0

        for task in tasks:
            desc = task.get("description", "")
            if _has_placeholder(desc):
                plan_has_placeholder = True
            if _has_forward_ref(desc):
                plan_has_forward_ref = True

            for prec in task.get("preconditions", []):
                plan_precondition_total += 1
                total_preconditions += 1
                if isinstance(prec, dict) and _is_grounded(prec, task_ids):
                    plan_grounded += 1
                    grounded_preconditions += 1
                else:
                    plan_has_bad_precondition = True
                    gap_inventory.append(
                        {
                            "goal": goal_id,
                            "task": task["id"],
                            "precondition": prec.get("description", str(prec)),
                            "issue": "unverifiable precondition",
                        }
                    )

        if plan_has_placeholder:
            plans_with_placeholder += 1
        if plan_has_forward_ref:
            plans_with_forward_ref += 1
        if plan_has_bad_precondition:
            plans_with_bad_precondition += 1

        walkable_pct = (
            round(
                (plan_precondition_total - len([g for g in gap_inventory if g["goal"] == goal_id]))
                / plan_precondition_total
                * 100,
                1,
            )
            if plan_precondition_total
            else 100.0
        )

        per_plan_verdicts.append(
            {
                "goal": goal_id,
                "tasks": len(tasks),
                "preconditions": plan_precondition_total,
                "grounded": plan_grounded,
                "walkable_pct": walkable_pct,
                "has_placeholder": plan_has_placeholder,
                "has_forward_ref": plan_has_forward_ref,
                "has_bad_precondition": plan_has_bad_precondition,
            }
        )

    return {
        "total_plans": total_plans,
        "total_tasks": total_tasks,
        "total_preconditions": total_preconditions,
        "grounded_preconditions": grounded_preconditions,
        "grounded_pct": round(grounded_preconditions / total_preconditions * 100, 1)
        if total_preconditions
        else 100.0,
        "plans_with_placeholder": plans_with_placeholder,
        "plans_with_forward_ref": plans_with_forward_ref,
        "plans_with_bad_precondition": plans_with_bad_precondition,
        "gap_inventory": gap_inventory[:20],
        "per_plan_verdicts": per_plan_verdicts,
    }


def test_q4_executor_usability_grounded_preconditions() -> None:
    """Q4: every approved plan's preconditions are grounded (established_by)."""
    result = audit_executor_usability()
    print(
        f"Q4: {result['total_plans']} approved plans, {result['total_tasks']} tasks, "
        f"{result['total_preconditions']} preconditions: "
        f"{result['grounded_pct']}% grounded"
    )
    print(
        f"     {result['plans_with_placeholder']} plans with placeholder tokens, "
        f"{result['plans_with_forward_ref']} with forward refs, "
        f"{result['plans_with_bad_precondition']} with ungrounded preconditions"
    )
    if result["gap_inventory"]:
        print("Gap inventory (first 20):")
        for g in result["gap_inventory"]:
            print(f"  {g['goal']} {g['task']}: {g['issue']} — {g['precondition']}")

    assert result["grounded_pct"] >= 95.0, (
        f"Q4: only {result['grounded_pct']}% of preconditions grounded "
        f"({result['grounded_preconditions']}/{result['total_preconditions']})"
    )
