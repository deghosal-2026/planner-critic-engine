"""Model & robustness sweeps — C5 fail-closed, concurrency stress (#93)."""

from __future__ import annotations

import threading
from collections.abc import Sequence
from pathlib import Path

import pytest

from conftest import EmptyCritic, ScriptedPlanner, make_goal, make_plan, make_task
from planner_critic.engine import Engine
from planner_critic.llm.base import Completion, Message, ToolSchema
from planner_critic.loop import LoopConfig
from planner_critic.store.sqlite import SQLiteStore
from planner_critic.types import PlanningError


def test_fail_closed_provider_failure_is_recorded() -> None:
    """Fail-closed: Engine wraps a decompose failure as PlanningError."""

    class BrokenProvider:
        name = "broken"
        base_url = "http://x"
        model = "x"

        def complete(
            self, messages: Sequence[Message], tool_schemas: Sequence[ToolSchema] = ()
        ) -> Completion:
            raise ValueError("simulated provider failure")

    from planner_critic.cli.plan import _CLIPlanner

    planner = _CLIPlanner(BrokenProvider())
    engine = Engine(
        planner=planner, critic=EmptyCritic(), config=LoopConfig(mode="deterministic-first")
    )
    try:
        engine.plan(make_goal())
        pytest.fail("expected PlanningError")
    except PlanningError as e:
        assert "simulated provider failure" in str(e)


def test_concurrent_plan_writes_no_store_corruption(tmp_path: Path) -> None:
    """D: 5 concurrent goal plans from separate threads — no corruption."""
    import concurrent.futures

    store_path = str(tmp_path / "concurrent.db")

    def run_plan(goal_id: str) -> bool:
        try:
            store = SQLiteStore(store_path)
            engine = Engine(
                planner=ScriptedPlanner(
                    [make_plan(plan_id=f"p-{goal_id}", tasks=[make_task("t1")])]
                ),
                critic=EmptyCritic(),
                config=LoopConfig(mode="deterministic-first"),
            )
            result = engine.plan(make_goal(goal_id=goal_id))
            if not result.is_approved or result.approved_plan is None:
                return False
            store.put_plan_version(result.approved_plan.plan)
            store.put_findings(
                result.approved_plan.plan.id,
                result.approved_plan.plan.version,
                result.findings,
            )
            store.close()
            return True
        except Exception:
            return False

    results = list(
        concurrent.futures.ThreadPoolExecutor(max_workers=2).map(
            run_plan, [f"g-{i}" for i in range(5)]
        )
    )
    assert all(results), "some concurrent plan writes failed"

    store = SQLiteStore(store_path)
    all_plans = store.list_plans()
    plan_ids = {p.id for p in all_plans}
    store.close()
    expected = {f"p-g-{i}" for i in range(5)}
    assert expected.issubset(plan_ids), f"missing plans: {expected - plan_ids}"


def test_concurrent_store_reads_no_exceptions(tmp_path: Path) -> None:
    """D: each thread opens its own SQLite connection — no cross-thread errors."""
    store_path = str(tmp_path / "concurrent_read.db")
    store = SQLiteStore(store_path)
    for i in range(100):
        store.put_plan_version(make_plan(plan_id=f"p{i}", tasks=[make_task("t1")]))
    store.close()

    errors = []
    lock = threading.Lock()

    def reader(n: int) -> None:
        local = SQLiteStore(store_path)
        try:
            for i in range(50):
                try:
                    local.list_plans()
                    local.get_plan(f"p{i % 100}")
                except Exception as e:
                    with lock:
                        errors.append(f"reader {n}: {e}")
        finally:
            local.close()

    threads = [threading.Thread(target=reader, args=(t,)) for t in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"concurrent reads failed: {errors}"
