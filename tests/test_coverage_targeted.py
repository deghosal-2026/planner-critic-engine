"""Targeted coverage test for uncovered code paths across the engine.

Covers edge cases and error-handling paths not hit by the main suite.
Hermetic (no LLM, no network).
"""

from __future__ import annotations

import json

from conftest import EmptyCritic, ScriptedCritic, ScriptedPlanner, make_goal, make_plan, make_task
from planner_critic.loop import LoopConfig, run_loop
from planner_critic.loop.budget import SpendState
from planner_critic.reason_codes import CONVERGED_STALLED
from planner_critic.schema.goal import Budget, Constraints, Goal, RiskTolerance
from planner_critic.types import Finding, Severity


def test_loop_fallthrough_to_llm_after_gate_pass() -> None:
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
                    id="w1",
                    task_id="t1",
                    version=1,
                    severity=Severity.WARNING,
                    reason_code="llm_missing_steps",
                    message="consider adding tests",
                )
            ],
        ]
    )
    goal = make_goal(tolerance=RiskTolerance.BALANCED)
    result = run_loop(
        goal, planner, critic, config=LoopConfig(mode="llm-every-revision", revision_cap=3)
    )
    assert result.status in ("approved", "escalated")


def test_loop_multiple_revisions_with_llm() -> None:
    for i in range(3):
        goal = make_goal(goal_id=f"g-{i}", tolerance=RiskTolerance.STRICT)
        planner = ScriptedPlanner([make_plan(plan_id=f"p-{i}", tasks=[make_task(f"t{i}")])])
        critic = ScriptedCritic(
            [
                [
                    Finding(
                        id="f1",
                        task_id=f"t{i}",
                        version=1,
                        severity=Severity.BLOCKER,
                        reason_code="missing_rollback",
                        message="no rollback",
                    )
                ],
                [
                    Finding(
                        id="f1",
                        task_id=f"t{i}",
                        version=1,
                        severity=Severity.BLOCKER,
                        reason_code="missing_rollback",
                        message="no rollback",
                    )
                ],
            ]
        )
        result = run_loop(
            goal, planner, critic, config=LoopConfig(mode="llm-every-revision", revision_cap=2)
        )
        assert result.reason_code == CONVERGED_STALLED


def test_budget_exhaustion_path() -> None:
    goal = Goal(
        id="g-budget",
        description="budget",
        risk_tolerance=RiskTolerance.STRICT,
        constraints=Constraints(budget=Budget(max_calls=5, max_revisions=5)),
    )
    state = SpendState()
    state.calls_used = 10
    result = run_loop(
        goal,
        ScriptedPlanner([make_plan(tasks=[make_task("t1", risk_class="critical")])]),
        EmptyCritic(),
        config=LoopConfig(mode="deterministic-first"),
        spend=state,
    )
    assert result.status == "escalated"


def test_http_fastapi_healthz_route() -> None:
    from planner_critic.server.http import create_fastapi_app

    app = create_fastapi_app(":memory:")
    assert app is not None
    assert "/healthz" in {getattr(r, "path", None) for r in app.routes}


def test_mcp_server_tool_errors() -> None:
    from planner_critic.server.mcp import PlannerCriticMCPServer

    mcp = PlannerCriticMCPServer(store_path=":memory:")
    assert mcp.handle_tool("nonexistent_tool", {})["status"] == "error"
    assert mcp.handle_tool("plan", {"goal_json": "not json"})["status"] == "error"
    assert mcp.handle_tool("critique", {"plan_json": "not json"})["status"] == "error"


def test_probe_edge_cases() -> None:
    """Cover remaining probe edge cases: non-string results, parse errors."""
    from planner_critic.probe.base import ProbeRequest, run_probe

    result1 = run_probe(
        ProbeRequest(
            kind="db_query", query=json.dumps({"query": "SELECT 1", "result": 1}), expected="1"
        )
    )
    assert result1.matched is True

    result2 = run_probe(ProbeRequest(kind="db_query", query="not-json-{{", expected="x"))
    assert result2.ok is False

    result3 = run_probe(
        ProbeRequest(
            kind="deploy_status", query=json.dumps({"service": "test", "status": 42}), expected="42"
        )
    )
    assert result3.matched is True

    result4 = run_probe(ProbeRequest(kind="deploy_status", query="bad{{json", expected="x"))
    assert result4.ok is False


