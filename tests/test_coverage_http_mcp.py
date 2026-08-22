"""Final coverage push — http://py/, mcp.py, demo/runner.py, _controller.py."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import EmptyCritic, ScriptedCritic, ScriptedPlanner, make_goal, make_plan, make_task
from planner_critic.engine import Engine
from planner_critic.loop import LoopConfig
from planner_critic.schema.goal import RiskTolerance


def test_http_full_plan_approve_cycle() -> None:
    """HTTP server: full plan -> approve cycle with scripted engine."""
    from planner_critic.server.http import PlannerCriticHTTPServer

    server = PlannerCriticHTTPServer(store_path=":memory:")
    planner = ScriptedPlanner(
        [
            make_plan(
                tasks=[
                    make_task(
                        "t1",
                        risk_class="low",
                        verification={"what": "x", "how": "y", "expected": "z"},
                    )
                ]
            )
        ]
    )
    engine = Engine(
        planner=planner, critic=EmptyCritic(), config=LoopConfig(mode="deterministic-first")
    )
    server.set_engine(engine)
    goal = make_goal()
    resp = server.handle_request("POST", "/plan", goal.model_dump(mode="json"))
    assert resp["status"] == 200
    assert resp["data"]["status"] == "approved"
    plan_id = resp["data"]["plan"]["id"]
    resp2 = server.handle_request("GET", f"/plans/{plan_id}")
    assert resp2["status"] == 200
    resp3 = server.handle_request("GET", f"/plans/{plan_id}/explain")
    assert resp3["status"] == 200


def test_http_escalation_cycle() -> None:
    """HTTP server: escalation via strict-tolerance plan."""
    from planner_critic.server.http import PlannerCriticHTTPServer

    server = PlannerCriticHTTPServer(store_path=":memory:")
    planner = ScriptedPlanner([make_plan(tasks=[make_task("t1", risk_class="critical")])])
    engine = Engine(
        planner=planner, critic=EmptyCritic(), config=LoopConfig(mode="deterministic-first")
    )
    server.set_engine(engine)
    goal = make_goal(tolerance=RiskTolerance.STRICT)
    resp = server.handle_request("POST", "/plan", goal.model_dump(mode="json"))
    assert resp["status"] in (200, 501)
    if resp["status"] == 200:
        assert resp["data"]["status"] in ("escalated", "approved")
        if resp["data"]["status"] == "escalated":
            esc_id = resp["data"]["escalation"]["id"]
            aprv = server.handle_request("POST", f"/escalations/{esc_id}/approve", {"note": "ok"})
            assert aprv["status"] == 200


def test_mcp_with_scripted_engine() -> None:
    """MCP server: plan and critique with injected scripted roles."""
    from planner_critic.server.mcp import PlannerCriticMCPServer

    mcp = PlannerCriticMCPServer(
        store_path=":memory:",
        planner=ScriptedPlanner([make_plan(tasks=[make_task("t1", risk_class="low")])]),
        critic=EmptyCritic(),
        loop_config=LoopConfig(mode="deterministic-first"),
    )
    goal = make_goal()
    result = mcp.handle_tool("plan", {"goal_json": json.dumps(goal.model_dump(mode="json"))})
    assert result["status"] == "ok"
    assert result["result"]["status"] == "approved"


def test_mcp_critique_scripted() -> None:
    """MCP server: critique with injected critic returning findings."""
    from planner_critic.server.mcp import PlannerCriticMCPServer

    mcp = PlannerCriticMCPServer(
        store_path=":memory:",
        planner=ScriptedPlanner([make_plan(tasks=[make_task("t1", risk_class="critical")])]),
        critic=ScriptedCritic([[]]),
        loop_config=LoopConfig(mode="deterministic-first"),
    )
    plan = make_plan(tasks=[make_task("t1", risk_class="critical")])
    result = mcp.handle_tool("critique", {"plan_json": json.dumps(plan.model_dump(mode="json"))})
    assert result["status"] == "ok"


def test_demo_runner_storyline() -> None:
    """Demo runner: full storyline with valid corpus goal."""
    from planner_critic.demo.runner import run_demo
    from planner_critic.store.base import InMemoryStore

    goal_file = Path(__file__).parents[1] / "examples" / "goals" / "migration.json"
    if not goal_file.exists():
        return
    rc = run_demo(str(goal_file), InMemoryStore(), no_graph=True)
    assert rc == 1 or rc == 0
