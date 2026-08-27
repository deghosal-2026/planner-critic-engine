"""Auto-repair benchmark (#177).

Measures revision reduction on ordering-violation and precondition-gap plans
when auto-repair and precondition closer are enabled. Hermetic — no LLM.

Usage:
    python3 docs/field-test/scripts/bench_auto_repair.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from planner_critic.loop import LoopConfig, run_loop
from planner_critic.schema.goal import Goal, RiskTolerance

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "tests"))
from conftest import EmptyCritic, ScriptedPlanner, hard_dep, make_goal, make_plan, make_task  # type: ignore[import-not-found]


def bench_ordering_repair() -> dict:
    """Ordering violation: auto-repair OFF vs ON."""
    plan = make_plan(
        tasks=[make_task("C"), make_task("A")],
        dependencies=[hard_dep("A", "C")],
    )
    goal = make_goal()
    planner = ScriptedPlanner([plan])

    # OFF
    r_off = run_loop(goal, ScriptedPlanner([plan]), EmptyCritic(), config=LoopConfig(auto_repair=False, revision_cap=1))
    # ON
    r_on = run_loop(goal, ScriptedPlanner([plan]), EmptyCritic(), config=LoopConfig(auto_repair=True, revision_cap=1))

    return {
        "test": "ordering_repair",
        "off_status": r_off.status,
        "on_status": r_on.status,
        "off_revisions": r_off.spend.revisions_used if r_off.spend else 0,
        "on_revisions": r_on.spend.revisions_used if r_on.spend else 0,
        "reduction": (r_off.spend.revisions_used if r_off.spend else 0) - (r_on.spend.revisions_used if r_on.spend else 0),
    }


def bench_precondition_closer() -> dict:
    """Precondition gap: closer OFF vs ON."""
    plan = make_plan(
        tasks=[
            make_task("A"),
            make_task("B", preconditions=[
                {"description": "outage window", "fact": "outage_window", "established_by": "book-outage-window"}
            ]),
        ],
    )
    goal = make_goal()

    r_off = run_loop(goal, ScriptedPlanner([plan]), EmptyCritic(), config=LoopConfig(precondition_closer=False, revision_cap=1))
    r_on = run_loop(goal, ScriptedPlanner([plan]), EmptyCritic(), config=LoopConfig(precondition_closer=True, revision_cap=1))

    return {
        "test": "precondition_closer",
        "off_status": r_off.status,
        "on_status": r_on.status,
        "off_revisions": r_off.spend.revisions_used if r_off.spend else 0,
        "on_revisions": r_on.spend.revisions_used if r_on.spend else 0,
    }


def run() -> dict:
    results = {
        "ordering": bench_ordering_repair(),
        "precondition": bench_precondition_closer(),
    }
    target = 0.30
    ordering_reduction = results["ordering"]["reduction"]
    print(json.dumps(results, indent=2))
    if ordering_reduction >= 1:
        print(f"\n✅ Ordering: {ordering_reduction} revision(s) saved — target ≥30% met")
    else:
        print(f"\n❌ Ordering: {ordering_reduction} revision(s) saved — target not met")
    return results


if __name__ == "__main__":
    run()
