"""Test FastAPI routes via ASGI transport and MCP error paths."""

from __future__ import annotations

import asyncio

import httpx


def test_fastapi_routes_discovery() -> None:
    """Cover all FastAPI route decorators by checking path registration."""
    from planner_critic.server.http import create_fastapi_app

    app = create_fastapi_app(":memory:")
    assert app is not None
    paths = {r.path for r in app.routes}
    for p in [
        "/healthz",
        "/plan",
        "/critique",
        "/plans",
        "/plans/{plan_id}",
        "/plans/{plan_id}/diff",
        "/plans/{plan_id}/graph",
        "/plans/{plan_id}/explain",
        "/escalations",
        "/escalations/{escalation_id}/approve",
        "/escalations/{escalation_id}/deny",
    ]:
        assert p in paths, f"missing {p}"


def test_fastapi_healthz() -> None:
    """Cover /healthz endpoint via ASGI transport."""
    from planner_critic.server.http import create_fastapi_app

    app = create_fastapi_app(":memory:")
    assert app is not None

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.get("/healthz")
            assert resp.status_code == 200
            assert resp.json() == {"status": "ok"}

    asyncio.run(run())


def test_fastapi_plans_empty() -> None:
    """Cover /plans route on empty store via ASGI."""
    from planner_critic.server.http import create_fastapi_app

    app = create_fastapi_app(":memory:")
    assert app is not None

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.get("/plans")
            assert resp.status_code == 200

    asyncio.run(run())


def test_fastapi_escalations_empty() -> None:
    """Cover /escalations route on empty store via ASGI."""
    from planner_critic.server.http import create_fastapi_app

    app = create_fastapi_app(":memory:")
    assert app is not None

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.get("/escalations")
            assert resp.status_code == 200

    asyncio.run(run())


def test_mcp_tool_resolve_errors() -> None:
    """Cover MCP tool error paths for escalate approvals/denials."""
    from planner_critic.server.mcp import PlannerCriticMCPServer

    mcp = PlannerCriticMCPServer(store_path=":memory:")
    assert (
        mcp.handle_tool("escalate_approve", {"escalation_id": "x", "note": "test"})["status"]
        == "error"
    )
    assert (
        mcp.handle_tool("escalate_deny", {"escalation_id": "x", "note": "test"})["status"]
        == "error"
    )


def test_mcp_plan_with_bad_goal() -> None:
    """Cover MCP plan tool with invalid goal JSON."""
    from planner_critic.server.mcp import PlannerCriticMCPServer

    mcp = PlannerCriticMCPServer(store_path=":memory:", llm_config_path="/nonexistent/config.toml")
    result = mcp.handle_tool(
        "plan", {"goal_json": '{"id": "g1", "description": "test", "risk_tolerance": "invalid"}'}
    )
    assert result["status"] == "error"
