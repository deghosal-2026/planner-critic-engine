"""Acceptance-matrix runner (M1 Task 10 / issue #10).

Loads ``tests/fixtures/loop_matrix.yaml`` and parametrizes every cell through
:func:`planner_critic.loop.run_loop`. Each cell fixes the goal, mode, revision
cap, planner drafts, and critic script and asserts the loop terminates with
exactly the expected status + reason_code. A 100% green matrix in CI asserts
loop correctness and determinism (F-74, M1 success metric).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from conftest import (
    EmptyCritic,
    ScriptedCritic,
    ScriptedPlanner,
    finding,
    make_plan,
    make_task,
)
from planner_critic.loop import LoopConfig, run_loop
from planner_critic.schema.goal import Budget, Constraints, Goal, RiskTolerance
from planner_critic.types import Severity

MATRIX_PATH = Path(__file__).parent / "fixtures" / "loop_matrix.yaml"


def _clean_plan() -> object:
    """The 'clean' draft: passes every deterministic gate."""
    return make_plan()


def _dirty_plan() -> object:
    """The 'dirty' draft: high-risk task with no verification/rollback."""
    return make_plan(tasks=[make_task("t1", risk_class="critical")])


#: Sentinels for critic scripts, resolved to concrete finding lists.
CRITIC_SCRIPTS: dict[str, list[list[object]]] = {
    "quiet": [[]],                                          # type: ignore[list-item]
    "warning_only": [[finding("t1", "unsafe_ordering", severity=Severity.WARNING)]],
    "blocker": [[finding("t1", "missing_verification")]],
    "warning_then_blocker": [
        [finding("t1", "unsafe_ordering", severity=Severity.WARNING)],
        [
            finding("t1", "unsafe_ordering", severity=Severity.WARNING),
            finding("t1", "missing_verification"),
        ],
    ],
}

DRAFTS: dict[str, object] = {"clean": _clean_plan(), "dirty": _dirty_plan()}


def _load_matrix() -> list[dict]:
    """Load and validate the matrix document."""
    data = yaml.safe_load(MATRIX_PATH.read_text())
    scenarios = data["scenarios"]
    assert isinstance(scenarios, list) and scenarios, "matrix must define scenarios"
    return scenarios


MATRIX = _load_matrix()


@pytest.mark.parametrize("cell", MATRIX, ids=[c["id"] for c in MATRIX])
def test_matrix_cell(cell: dict) -> None:
    """Run one matrix cell and assert the exact termination."""
    goal_kwargs = dict(cell["goal"])
    tolerance = RiskTolerance(goal_kwargs.pop("tolerance", "balanced"))
    budget_kwargs = goal_kwargs.pop("budget", None) or {}
    goal = Goal(
        id=f"matrix-{cell['id']}",
        description="matrix goal",
        risk_tolerance=tolerance,
        constraints=Constraints(budget=Budget(**budget_kwargs)),
    )

    drafts = [DRAFTS[d] for d in cell["planner_drafts"]]  # type: ignore[misc]
    planner = ScriptedPlanner(drafts)  # type: ignore[arg-type]

    critic_revisions: list[list[object]] = []
    for label in cell["critic"]:
        critic_revisions.extend(CRITIC_SCRIPTS[label])  # type: ignore[arg-type]
    if all(len(rev) == 0 for rev in critic_revisions):  # type: ignore[arg-type]
        critic = EmptyCritic()
    else:
        critic = ScriptedCritic(critic_revisions)  # type: ignore[arg-type]

    config = LoopConfig(
        mode=cell.get("mode", "deterministic-first"),  # type: ignore[arg-type]
        revision_cap=int(cell.get("revision_cap", 3)),
    )
    result = run_loop(goal, planner, critic, config)  # type: ignore[arg-type]

    expected = cell["expect"]
    assert result.status == expected["status"], cell
    assert result.reason_code == expected["reason_code"], cell
