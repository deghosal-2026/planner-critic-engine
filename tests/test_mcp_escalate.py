"""Escalation MCP tool tests (F-32): standalone tool functions for the server.

The MCP server (M5) wraps these into tool definitions; here they are tested
in isolation against a real SQLite store.
"""

from __future__ import annotations

import json

import pytest

from conftest import make_plan, make_task
from planner_critic.server.mcp_tools_escalate import escalate_approve, escalate_deny, escalate_list
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
    store.put_escalation(Escalation(id=esc_id, plan_id="plan-1", version=1, question="proceed?"))
    store.close()


class TestEscalateList:
    """escalate_list returns escalations from the store."""

    def test_lists_open(self, store_path: str) -> None:
        _seed_escalation(store_path)
        result = escalate_list(store_path)
        assert len(result) == 1
        assert result[0]["id"] == "esc:plan-1:1"
        assert result[0]["status"] == "open"

    def test_filters_by_status(self, store_path: str) -> None:
        _seed_escalation(store_path)
        assert len(escalate_list(store_path, status="open")) == 1
        assert len(escalate_list(store_path, status="approved")) == 0

    def test_empty_store(self, store_path: str) -> None:
        assert escalate_list(store_path) == []


class TestEscalateApprove:
    """escalate_approve resolves an escalation with status approved."""

    def test_approve_resolves(self, store_path: str) -> None:
        _seed_escalation(store_path)
        result = escalate_approve(store_path, "esc:plan-1:1", note="approved by review")
        assert result["status"] == "approved"
        assert result["resolution"] == "approved by review"
        assert result["resolved_at"] is not None

    def test_approve_with_patch_stores_new_revision(self, store_path: str) -> None:
        _seed_escalation(store_path)
        patch = make_plan(
            plan_id="plan-1",
            version=2,
            parent="plan-1",
            tasks=[make_task("t1", verification={"what": "w", "how": "h", "expected": "e"})],
        )
        result = escalate_approve(
            store_path, "esc:plan-1:1", patch_json=json.dumps(patch.to_dict())
        )
        assert result["status"] == "approved"

        reopened = SQLiteStore(store_path)
        latest = reopened.get_plan("plan-1")
        reopened.close()
        assert latest is not None
        assert latest.version == 2

    def test_approve_unknown_id_raises(self, store_path: str) -> None:
        with pytest.raises(ValueError):
            escalate_approve(store_path, "esc:ghost")


class TestEscalateDeny:
    """escalate_deny resolves an escalation with status denied."""

    def test_deny_resolves(self, store_path: str) -> None:
        _seed_escalation(store_path)
        result = escalate_deny(store_path, "esc:plan-1:1", note="rejected")
        assert result["status"] == "denied"
        assert result["resolution"] == "rejected"

    def test_deny_unknown_id_raises(self, store_path: str) -> None:
        with pytest.raises(ValueError):
            escalate_deny(store_path, "esc:ghost")
