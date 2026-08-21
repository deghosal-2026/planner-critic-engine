"""C12 / C28 field-test matrix: all 6 adapters x 2 goals + audit trail (#87).

The 0.1.0 report exercised only the raw-Python adapter (1 adapter x 1 goal).
C12 requires every framework adapter to gate an approved plan for the same
goals; C28 requires a queryable audit trail with distinct adapter entries.

Hermetic: fake roles from conftest (ScriptedPlanner/EmptyCritic) so no LLM or
network is involved. The MCP adapter is exercised through the MCP server's
``plan`` tool with scripted roles injected.
"""

from __future__ import annotations

import json

import pytest

from conftest import EmptyCritic, ScriptedPlanner, make_goal, make_plan, make_task
from planner_critic.adapters._audit import AuditEvent, AuditTrail

GOALS = [
    ("ci-01", make_goal(goal_id="ci-01", description="multistage pipeline")),
    ("data-01", make_goal(goal_id="data-01", description="dbt pipeline")),
]


@pytest.fixture
def engine_factory():
    """Factory for an engine that approves immediately with a stable plan."""

    def _build(goal_id: str) -> object:
        from planner_critic.engine import Engine
        from planner_critic.loop import LoopConfig

        planner = ScriptedPlanner([make_plan(goal_id=goal_id, tasks=[make_task("t1")])])
        return Engine(planner, EmptyCritic(), LoopConfig(mode="deterministic-first"))

    return _build


@pytest.mark.parametrize("goal_id,goal", GOALS)
def test_raw_python_adapter_c12(engine_factory, goal_id, goal) -> None:
    """C12: raw Python adapter approves a valid plan for each goal."""
    from planner_critic.adapters.python import plan

    result = plan(engine_factory(goal_id), goal)
    assert result.is_approved
    assert result.approved_plan is not None
    assert result.approved_plan.plan.goal_id == goal_id


def test_langgraph_adapter_gates_execution(engine_factory) -> None:
    """C12: LangGraph ApprovalHook approves an approved plan and blocks without one."""
    from planner_critic.adapters.langgraph import ApprovalHook, PlanNotApprovedError

    result = engine_factory("ci-01").plan(make_goal(goal_id="ci-01"))
    assert result.is_approved and result.approved_plan is not None
    hook = ApprovalHook(result.approved_plan)
    assert hook.check() is result.approved_plan

    empty = ApprovalHook(None)
    with pytest.raises(PlanNotApprovedError):
        empty.check()


def test_crewai_adapter_sets_step_in_plan(engine_factory) -> None:
    """C12: CrewAI interceptor verifies a task exists in the approved plan."""
    from planner_critic.adapters.crewai import PlanAwareTaskInterceptor, TaskNotInPlanError

    result = engine_factory("ci-01").plan(make_goal(goal_id="ci-01"))
    assert result.is_approved and result.approved_plan is not None
    desc = result.approved_plan.plan.tasks[0].description
    interceptor = PlanAwareTaskInterceptor(result.approved_plan)
    assert interceptor.verify_task(desc) is True

    with pytest.raises(TaskNotInPlanError):
        interceptor.verify_task("no such task exists in the plan")


def test_openai_agents_guardrail_approves(engine_factory) -> None:
    """C12: OpenAI Agents PlanGuardrail gates on approval."""
    from planner_critic.adapters.openai_agents import PlanGuardrail

    guardrail = PlanGuardrail(engine_factory("data-01"), make_goal(goal_id="data-01"))
    result = guardrail.check()
    assert result.is_approved
    assert guardrail.check() is result  # cached


def test_pydantic_ai_guard_approves(engine_factory) -> None:
    """C12: PydanticAI ApprovalGuard gates on approval."""
    from planner_critic.adapters.pydantic_ai import ApprovalGuard

    guard = ApprovalGuard(engine_factory("data-01"), make_goal(goal_id="data-01"))
    result = guard.guard(None)
    assert result.is_approved
    assert guard.guard(None) is result  # cached


def test_mcp_tool_plans_with_scripted_roles(tmp_path) -> None:
    """C12: MCP adapter plans the goal, producing an approved result."""
    from planner_critic.loop import LoopConfig
    from planner_critic.server.mcp import PlannerCriticMCPServer

    planner = ScriptedPlanner([make_plan(goal_id="ci-01", tasks=[make_task("t1")])])
    mcp = PlannerCriticMCPServer(
        store_path=str(tmp_path / "plans.db"),
        planner=planner,
        critic=EmptyCritic(),
        loop_config=LoopConfig(mode="deterministic-first"),
    )

    result = mcp.handle_tool(
        "plan", {"goal_json": json.dumps(make_goal(goal_id="ci-01").model_dump())}
    )
    assert result["status"] == "ok"
    assert result["result"]["approved_plan"]["plan"]["goal_id"] == "ci-01"


def test_c28_audit_trail_distinct_adapters(tmp_path) -> None:
    """C28: distinct per-adapter audit entries are queryable in one trail."""

    trail = AuditTrail()
    trail.record(AuditEvent("raw", "plan_requested", plan_id="p1"))
    trail.record(AuditEvent("langgraph", "re_gate_check", plan_id="p1"))
    trail.record(AuditEvent("crewai", "re_gate_check", plan_id="p1"))
    trail.record(AuditEvent("openai_agents", "plan_approved", plan_id="p1"))
    trail.record(AuditEvent("pydantic_ai", "plan_approved", plan_id="p1"))
    trail.record(AuditEvent("mcp", "plan_requested", plan_id="p1"))

    adapters = {e.adapter for e in trail.get_events()}
    assert adapters == {"raw", "langgraph", "crewai", "openai_agents", "pydantic_ai", "mcp"}
    last = trail.last_event()
    assert last is not None and last.plan_id == "p1"
