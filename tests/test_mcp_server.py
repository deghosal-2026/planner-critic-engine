"""Tests for the PlannerCritic MCP server (M5 T7).

Covers:
1. Server lists exactly 6 tools.
2. ``escalate_list`` works against a seeded store.
3. ``escalate_approve`` resolves against a seeded store.
4. ``explain`` returns the NotImplemented stub.
5. ``plan`` returns a graceful error when no providers configured.
"""

from __future__ import annotations

import json

import pytest

from conftest import make_plan, make_task
from planner_critic.server.mcp import PlannerCriticMCPServer
from planner_critic.store.sqlite import SQLiteStore
from planner_critic.types import Escalation


@pytest.fixture
def store_path(tmp_path) -> str:
    """A fresh SQLite store path per test."""
    return str(tmp_path / "plans.db")


def _seed_escalation(store_path: str, esc_id: str = "esc:plan-1:1") -> None:
    """Create a plan and an open escalation in the store."""
    store = SQLiteStore(store_path)
    store.put_plan_version(make_plan(plan_id="plan-1", version=1))
    store.put_escalation(
        Escalation(id=esc_id, plan_id="plan-1", version=1, question="proceed?")
    )
    store.close()


@pytest.fixture
def server(store_path: str) -> PlannerCriticMCPServer:
    """An MCP server with no LLM config (escalation-only tools)."""
    return PlannerCriticMCPServer(store_path=store_path)


@pytest.fixture
def seeded_server(store_path: str) -> PlannerCriticMCPServer:
    """An MCP server with a pre-seeded escalation."""
    _seed_escalation(store_path)
    return PlannerCriticMCPServer(store_path=store_path)


# -- test group ------------------------------------------------------------


class TestToolListing:
    """Server lists its tools correctly."""

    def test_lists_exactly_6_tools(self, server: PlannerCriticMCPServer) -> None:
        tools = server.list_tools()
        assert len(tools) == 6

        names = {t["name"] for t in tools}
        assert names == {
            "plan",
            "critique",
            "explain",
            "escalate_list",
            "escalate_approve",
            "escalate_deny",
        }

    def test_every_tool_has_input_schema(self, server: PlannerCriticMCPServer) -> None:
        for tool in server.list_tools():
            assert "input_schema" in tool
            assert isinstance(tool["input_schema"], dict)


class TestEscalateList:
    """escalate_list returns escalations from the store."""

    def test_returns_escalations(self, seeded_server: PlannerCriticMCPServer) -> None:
        result = seeded_server.handle_tool("escalate_list", {})
        assert result["status"] == "ok"
        assert len(result["escalations"]) == 1
        assert result["escalations"][0]["id"] == "esc:plan-1:1"
        assert result["escalations"][0]["status"] == "open"

    def test_filters_by_status(self, seeded_server: PlannerCriticMCPServer) -> None:
        open_result = seeded_server.handle_tool("escalate_list", {"status": "open"})
        assert len(open_result["escalations"]) == 1

        approved_result = seeded_server.handle_tool("escalate_list", {"status": "approved"})
        assert len(approved_result["escalations"]) == 0

    def test_empty_when_no_escalations(self, server: PlannerCriticMCPServer) -> None:
        result = server.handle_tool("escalate_list", {})
        assert result["status"] == "ok"
        assert result["escalations"] == []


class TestEscalateApprove:
    """escalate_approve resolves an escalation."""

    def test_approve_resolves(self, seeded_server: PlannerCriticMCPServer) -> None:
        result = seeded_server.handle_tool(
            "escalate_approve",
            {"escalation_id": "esc:plan-1:1", "note": "approved by review"},
        )
        assert result["status"] == "ok"
        assert result["escalation"]["status"] == "approved"
        assert result["escalation"]["resolution"] == "approved by review"
        assert result["escalation"]["resolved_at"] is not None

    def test_approve_with_patch(self, seeded_server: PlannerCriticMCPServer) -> None:
        patch = make_plan(
            plan_id="plan-1",
            version=2,
            parent="plan-1",
            tasks=[make_task("t1", verification={"what": "w", "how": "h", "expected": "e"})],
        )
        result = seeded_server.handle_tool(
            "escalate_approve",
            {
                "escalation_id": "esc:plan-1:1",
                "patch_json": json.dumps(patch.to_dict()),
            },
        )
        assert result["status"] == "ok"
        assert result["escalation"]["status"] == "approved"


class TestEscalateDeny:
    """escalate_deny resolves an escalation."""

    def test_deny_resolves(self, seeded_server: PlannerCriticMCPServer) -> None:
        result = seeded_server.handle_tool(
            "escalate_deny",
            {"escalation_id": "esc:plan-1:1", "note": "rejected"},
        )
        assert result["status"] == "ok"
        assert result["escalation"]["status"] == "denied"
        assert result["escalation"]["resolution"] == "rejected"


class TestExplain:
    """explain is a stub that returns NotImplemented."""

    def test_explain_returns_not_implemented(self, server: PlannerCriticMCPServer) -> None:
        result = server.handle_tool("explain", {"plan_id": "plan-1"})
        assert result["status"] == "ok"
        assert result["result"] == "explain not yet implemented"


class TestPlan:
    """plan returns graceful error when no providers configured."""

    def test_plan_errors_without_providers(
        self, server: PlannerCriticMCPServer
    ) -> None:
        goal_json = json.dumps({"id": "g1", "description": "test goal"})
        result = server.handle_tool("plan", {"goal_json": goal_json})
        assert result["status"] == "error"
        assert "no providers configured" in result["error"]

    def test_plan_errors_on_invalid_goal_json(
        self, server: PlannerCriticMCPServer
    ) -> None:
        result = server.handle_tool("plan", {"goal_json": "not valid json at all"})
        assert result["status"] == "error"
        assert "invalid goal_json" in result["error"]
