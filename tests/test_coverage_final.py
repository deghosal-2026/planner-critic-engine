"""Final coverage push — targeting http.py, mcp.py, _controller.py, cli/plan.py."""

from __future__ import annotations

from conftest import ScriptedCritic, ScriptedPlanner, make_goal, make_plan, make_task
from planner_critic.loop import LoopConfig, run_loop
from planner_critic.reason_codes import REGRESSION_THRASHING
from planner_critic.schema.goal import RiskTolerance
from planner_critic.types import Finding, Severity


def test_fastapi_all_endpoints() -> None:
    """Cover all FastAPI route endpoints via ASGI transport."""
    import asyncio

    import httpx

    from planner_critic.server.http import create_fastapi_app

    app = create_fastapi_app(":memory:")
    assert app is not None

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.get("/healthz")
            assert resp.status_code == 200
            resp2 = await c.get("/plans")
            assert resp2.status_code == 200
            resp3 = await c.get("/escalations")
            assert resp3.status_code == 200

    asyncio.run(run())


def test_mcp_plan_and_critique_errors() -> None:
    """Cover MCP plan/critique error paths (provider not configured)."""
    import json

    from planner_critic.server.mcp import PlannerCriticMCPServer

    mcp = PlannerCriticMCPServer(store_path=":memory:")
    goal = make_goal()
    result = mcp.handle_tool("plan", {"goal_json": json.dumps(goal.model_dump())})
    assert result["status"] == "error"


def test_mcp_escalate_errors() -> None:
    """Cover MCP escalation error paths (unknown escalation id)."""

    from planner_critic.server.mcp import PlannerCriticMCPServer

    mcp = PlannerCriticMCPServer(store_path=":memory:")
    result = mcp.handle_tool("escalate_list", {"status": "open"})
    assert result["status"] == "ok"
    assert result["escalations"] == []
    result2 = mcp.handle_tool("escalate_approve", {"escalation_id": "nope", "note": "test"})
    assert result2["status"] == "error"
    result3 = mcp.handle_tool("escalate_deny", {"escalation_id": "nope", "note": "test"})
    assert result3["status"] == "error"


def test_loop_regression_escalation() -> None:
    """Cover regression detection path in _controller.py."""
    goal = make_goal(tolerance=RiskTolerance.STRICT)
    plan = make_plan(
        tasks=[
            make_task(
                "t1", risk_class="low", verification={"what": "x", "how": "y", "expected": "z"}
            )
        ]
    )
    planner = ScriptedPlanner([plan])
    critic = ScriptedCritic(
        [
            [
                Finding(
                    id="w",
                    task_id="t1",
                    version=1,
                    severity=Severity.WARNING,
                    reason_code="llm_missing_steps",
                    message="w",
                )
            ],
            [
                Finding(
                    id="w",
                    task_id="t1",
                    version=1,
                    severity=Severity.WARNING,
                    reason_code="llm_missing_steps",
                    message="w",
                ),
                Finding(
                    id="b",
                    task_id="t1",
                    version=1,
                    severity=Severity.BLOCKER,
                    reason_code="missing_rollback",
                    message="new blocker",
                ),
            ],
        ]
    )
    result = run_loop(goal, planner, critic, config=LoopConfig(revision_cap=5))
    assert result.reason_code == REGRESSION_THRASHING, f"got {result.reason_code}"
