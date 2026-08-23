"""Comprehensive coverage test targeting remaining uncovered paths.

Covers error-handling paths in HTTP, MCP, demo, and loop modules.
Hermetic (no LLM, no network).
"""

from __future__ import annotations

from pathlib import Path

from conftest import EmptyCritic, ScriptedPlanner, make_plan, make_task
from planner_critic.loop import LoopConfig
from planner_critic.schema.goal import RiskTolerance


def test_http_error_paths() -> None:
    from planner_critic.server.http import PlannerCriticHTTPServer

    server = PlannerCriticHTTPServer(store_path=":memory:")
    assert server.handle_request("GET", "/unknown/route")["status"] == 404
    assert server.handle_request("POST", "/plan", {"bad": "data"})["status"] == 400
    assert server.handle_request("POST", "/critique", {"plan": None})["status"] == 400


def test_fastapi_app_routes() -> None:
    from planner_critic.server.http import create_fastapi_app

    app = create_fastapi_app(":memory:")
    assert app is not None
    paths = {getattr(r, "path", None) for r in app.routes}
    for path in ["/healthz", "/plan", "/critique", "/plans", "/escalations"]:
        assert path in paths, f"Missing route: {path}"


def test_mcp_stdio_loop() -> None:
    import io
    import sys

    from planner_critic.server.mcp import PlannerCriticMCPServer

    mcp = PlannerCriticMCPServer(store_path=":memory:")
    fake_in = io.StringIO('{"tool": "escalate_list", "args": {}}\n')
    fake_out = io.StringIO()
    old_in, old_out = sys.stdin, sys.stdout
    sys.stdin = fake_in
    sys.stdout = fake_out
    try:
        mcp.run_stdio()
    finally:
        sys.stdin, sys.stdout = old_in, old_out
    out = fake_out.getvalue().strip()
    assert '"status": "ok"' in out


def test_demo_invalid_goal(tmp_path: Path) -> None:
    from planner_critic.demo.runner import run_demo
    from planner_critic.store.base import InMemoryStore

    path = tmp_path / "goal.json"
    path.write_text("not json")
    rc = run_demo(str(path), InMemoryStore())
    assert rc == 1


def test_loop_budget_via_state() -> None:
    from planner_critic.loop import run_loop
    from planner_critic.loop.budget import SpendState
    from planner_critic.schema.goal import Budget, Constraints, Goal

    goal = Goal(
        id="g-bgt",
        description="budget",
        risk_tolerance=RiskTolerance.STRICT,
        constraints=Constraints(budget=Budget(max_revisions=2)),
    )
    state = SpendState()
    state.revisions_used = 3
    result = run_loop(
        goal,
        ScriptedPlanner([make_plan(tasks=[make_task("t1", risk_class="critical")])]),
        EmptyCritic(),
        config=LoopConfig(mode="deterministic-first"),
        spend=state,
    )
    assert result.status == "escalated"
