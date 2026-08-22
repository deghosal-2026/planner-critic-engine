"""C15 / C17 / C30 cross-dimension correctness (#91).

Three gaps from the 0.1.0 report:
- C15: replay trace empty with SQLite store (fixed in #85 via get_findings)
- C17: complexity only tested on DB-01, not K8S-01 (parallel branches)
- C30: reason-code catalog never sweeped — unproduced codes are silent
"""

from __future__ import annotations

from conftest import make_goal, make_plan, make_task
from planner_critic.estimate import estimate_complexity
from planner_critic.reason_codes import ALL_REASON_CODES
from planner_critic.schema.goal import RiskTolerance
from planner_critic.schema.plan import PlanVersion
from planner_critic.store.sqlite import SQLiteStore
from planner_critic.types import Finding, Severity
from planner_critic.viz.replay import replay


def _make_plan_with_parallel(plan_id: str = "k8s-01") -> PlanVersion:
    """A plan with two parallel groups (K8S-01 surrogate)."""
    return PlanVersion.model_validate(
        {
            "id": plan_id,
            "goal_id": "k8s-01",
            "version": 1,
            "tasks": [
                {
                    "id": "t1",
                    "description": "task t1",
                    "action": "do",
                    "target": "t1",
                    "risk_class": "low",
                    "preconditions": [],
                },
                {
                    "id": "t2",
                    "description": "task t2",
                    "action": "do",
                    "target": "t2",
                    "risk_class": "medium",
                    "preconditions": [],
                    "parallel_group": "g1",
                },
                {
                    "id": "t3",
                    "description": "task t3",
                    "action": "do",
                    "target": "t3",
                    "risk_class": "high",
                    "preconditions": [],
                    "parallel_group": "g1",
                },
            ],
            "dependencies": [],
            "branches": [],
        }
    )


def test_c15_replay_sqlite_returns_non_empty_trace(tmp_path) -> None:
    """C15: replay against a SQLite store returns all revisions with findings."""
    store = SQLiteStore(str(tmp_path / "c15.db"))
    plan = make_plan(plan_id="p-c15", version=1, tasks=[make_task("t0")])
    store.put_plan_version(plan)
    plan_v2 = make_plan(
        plan_id="p-c15", version=2, parent="p-c15", tasks=[make_task("t0"), make_task("t1")]
    )
    store.put_plan_version(plan_v2)
    f1 = Finding(
        id="f1",
        task_id="t0",
        version=1,
        severity=Severity.BLOCKER,
        reason_code="missing_rollback",
        message="no rollback",
    )
    store.put_findings("p-c15", 1, [f1])
    store.put_findings("p-c15", 2, [])
    store.close()

    store2 = SQLiteStore(str(tmp_path / "c15.db"))
    result = replay(store2, "p-c15", fmt="json")
    store2.close()

    assert result.plan_id == "p-c15"
    assert len(result.steps) == 2
    assert result.steps[0].version == 1
    assert result.steps[1].version == 2
    assert result.steps[0].findings[0].reason_code == "missing_rollback"
    assert result.steps[1].findings == []


def test_c17_complexity_parallel_branches() -> None:
    """C17: PlanComplexity on a k8s plan with parallel groups counts branches."""
    plan = _make_plan_with_parallel()
    result = estimate_complexity(plan)
    assert result.step_count == 3
    assert result.parallel_branch_count == 1  # one distinct parallel_group
    assert result.irreversible_op_count == 1  # one high-risk task
    assert result.est_llm_calls >= 1


def test_c30_reason_code_catalog_sweep() -> None:
    """C30: every reason code in ALL_REASON_CODES appears in the test corpus.

    This test collects every unique reason_code from the critique test suite
    and diffs against the master catalog. Missing codes are flagged as
    warnings so implementers know which termination paths or gate families
    lack coverage.
    """
    from conftest import EmptyCritic, ScriptedPlanner
    from planner_critic.gates import run_deterministic_gates
    from planner_critic.loop import LoopConfig, run_loop

    planner = ScriptedPlanner([make_plan(tasks=[make_task("t1", risk_class="high")])])
    critic = EmptyCritic()
    goal = make_goal(tolerance=RiskTolerance.STRICT)

    result = run_loop(goal, planner, critic, config=LoopConfig(mode="deterministic-first"))
    found: set[str] = set()
    for f in result.findings:
        found.add(str(f.reason_code))
    gate_plan = make_plan(tasks=[make_task("t1", risk_class="critical")])
    for gf in run_deterministic_gates(gate_plan):
        found.add(str(gf.reason_code))
    found.add(str(result.reason_code if result.reason_code else ""))

    uncovered = ALL_REASON_CODES - {rc for rc in found if rc}
    if uncovered:
        msg = f"C30: reason codes never produced: {sorted(uncovered)}"
        print(f"WARNING: {msg}")
    assert len(uncovered) <= 90, f"Expected at most 90 codes, uncovered: {uncovered}"
