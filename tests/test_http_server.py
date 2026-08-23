"""Tests for the HTTP service (F-62, §5.9).

Tests exercise :class:`PlannerCriticHTTPServer` via ``handle_request()``
directly — no web framework, no network. Hermetic: uses InMemoryStore
through a temporary SQLite file.
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import pytest

from conftest import EmptyCritic, ScriptedPlanner, make_goal, make_plan, make_task
from planner_critic.engine import Engine
from planner_critic.loop import LoopConfig
from planner_critic.server.http import PlannerCriticHTTPServer, create_fastapi_app


@pytest.fixture
def server() -> PlannerCriticHTTPServer:
    """An HTTP server backed by a temporary SQLite database."""
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    return PlannerCriticHTTPServer(db_path)


def _seed_plan(server: PlannerCriticHTTPServer) -> str:
    """Run a scripted plan through the engine and persist it in the store."""
    planner = ScriptedPlanner([make_plan(tasks=[make_task("t1")])])
    engine = Engine(planner=planner, critic=EmptyCritic(), config=LoopConfig(revision_cap=1))
    server.set_engine(engine)
    goal = make_goal()
    resp = server.handle_request("POST", "/plan", goal.model_dump(mode="json"))
    assert resp["status"] == 200
    plan_id: str = resp["data"]["plan"]["id"]
    return plan_id


def _seed_multi_revision(server: PlannerCriticHTTPServer) -> str:
    """Persist two revisions of a plan directly so diff has added/changed/removed."""
    from planner_critic.store.base import PlanStore

    store: PlanStore = server.store
    v1 = make_plan(tasks=[make_task("t0")])
    v2 = make_plan(
        plan_id=v1.id,
        version=2,
        parent=str(v1.version),
        tasks=[make_task("t0"), make_task("t1"), make_task("t2")],
    )
    store.put_plan_version(v1)
    store.put_plan_version(v2)
    store.put_findings(v1.id, 1, [])
    store.put_findings(v2.id, 2, [])
    return v1.id


# ---- Tests ----------------------------------------------------------------


def test_get_plans_empty(server: PlannerCriticHTTPServer) -> None:
    """GET /plans returns an empty list initially."""
    resp = server.handle_request("GET", "/plans")
    assert resp["status"] == 200
    assert resp["data"]["plans"] == []
    assert resp["data"]["count"] == 0


def test_post_plan_returns_result(server: PlannerCriticHTTPServer) -> None:
    """POST /plan with a goal returns a result via engine."""
    planner = ScriptedPlanner([make_plan(tasks=[make_task("t1")])])
    engine = Engine(planner=planner, critic=EmptyCritic(), config=LoopConfig(revision_cap=1))
    server.set_engine(engine)
    goal = make_goal()
    resp = server.handle_request("POST", "/plan", goal.model_dump(mode="json"))
    assert resp["status"] == 200
    data = resp["data"]
    assert data["status"] == "approved"
    assert data["plan"] is not None
    assert data["plan"]["id"] == "plan-1"


def test_get_plan_detail(server: PlannerCriticHTTPServer) -> None:
    """GET /plans/{id} returns plan details after planning."""
    plan_id = _seed_plan(server)
    resp = server.handle_request("GET", f"/plans/{plan_id}")
    assert resp["status"] == 200
    assert resp["data"]["plan"]["id"] == plan_id
    assert resp["data"]["plan"]["version"] >= 1


def test_get_plan_graph(server: PlannerCriticHTTPServer) -> None:
    """GET /plans/{id}/graph returns a Mermaid DAG."""
    plan_id = _seed_plan(server)
    resp = server.handle_request("GET", f"/plans/{plan_id}/graph")
    assert resp["status"] == 200
    graph = resp["data"]
    assert graph["plan_id"] == plan_id
    assert "graph TD" in graph["mermaid"]
    assert "t1" in graph["mermaid"]


def test_get_escalations_empty(server: PlannerCriticHTTPServer) -> None:
    """GET /escalations returns an empty list when no escalations exist."""
    resp = server.handle_request("GET", "/escalations")
    assert resp["status"] == 200
    assert resp["data"]["escalations"] == []
    assert resp["data"]["count"] == 0


def test_escalate_approve(server: PlannerCriticHTTPServer) -> None:
    """POST /escalations/{id}/approve resolves an escalation."""
    planner = ScriptedPlanner([make_plan(tasks=[make_task("t1", risk_class="critical")])])
    engine = Engine(planner=planner, critic=EmptyCritic(), config=LoopConfig(revision_cap=1))
    server.set_engine(engine)
    goal = make_goal()
    resp = server.handle_request("POST", "/plan", goal.model_dump(mode="json"))
    assert resp["data"]["status"] == "escalated"
    escalation_id: str = resp["data"]["escalation"]["id"]

    resp2 = server.handle_request(
        "POST", f"/escalations/{escalation_id}/approve", {"note": "approved"}
    )
    assert resp2["status"] == 200
    assert resp2["data"]["status"] == "approved"
    assert resp2["data"]["resolution"] == "approved"


def test_unknown_route(server: PlannerCriticHTTPServer) -> None:
    """An unknown path returns 404."""
    resp = server.handle_request("GET", "/nonexistent")
    assert resp["status"] == 404


def test_post_plan_no_engine(server: PlannerCriticHTTPServer) -> None:
    """POST /plan without an engine returns 501."""
    goal = make_goal()
    resp = server.handle_request("POST", "/plan", goal.model_dump(mode="json"))
    assert resp["status"] == 501


def test_get_plan_detail_unknown(server: PlannerCriticHTTPServer) -> None:
    """GET /plans/{id} for an unknown plan returns 404."""
    resp = server.handle_request("GET", "/plans/ghost-plan")
    assert resp["status"] == 404


def test_get_plan_graph_unknown(server: PlannerCriticHTTPServer) -> None:
    """GET /plans/{id}/graph for an unknown plan returns 404."""
    resp = server.handle_request("GET", "/plans/ghost-plan/graph")
    assert resp["status"] == 404


def test_get_plan_explain(server: PlannerCriticHTTPServer) -> None:
    """GET /plans/{id}/explain returns explain result."""
    plan_id = _seed_plan(server)
    resp = server.handle_request("GET", f"/plans/{plan_id}/explain")
    assert resp["status"] == 200
    data = resp["data"]
    assert data["plan_id"] == plan_id
    assert len(data["decisions"]) >= 1


def test_escalations_list_with_escalation(server: PlannerCriticHTTPServer) -> None:
    """GET /escalations returns an escalation after a plan that escalated."""
    planner = ScriptedPlanner([make_plan(tasks=[make_task("t1", risk_class="critical")])])
    engine = Engine(planner=planner, critic=EmptyCritic(), config=LoopConfig(revision_cap=1))
    server.set_engine(engine)
    goal = make_goal()
    server.handle_request("POST", "/plan", goal.model_dump(mode="json"))
    resp = server.handle_request("GET", "/escalations")
    assert resp["status"] == 200
    assert resp["data"]["count"] >= 1


def test_escalate_deny(server: PlannerCriticHTTPServer) -> None:
    """POST /escalations/{id}/deny resolves an escalation as denied."""
    planner = ScriptedPlanner([make_plan(tasks=[make_task("t1", risk_class="critical")])])
    engine = Engine(planner=planner, critic=EmptyCritic(), config=LoopConfig(revision_cap=1))
    server.set_engine(engine)
    goal = make_goal()
    resp = server.handle_request("POST", "/plan", goal.model_dump(mode="json"))
    assert resp["data"]["status"] == "escalated"
    escalation_id: str = resp["data"]["escalation"]["id"]

    resp2 = server.handle_request(
        "POST", f"/escalations/{escalation_id}/deny", {"note": "not ready"}
    )
    assert resp2["status"] == 200
    assert resp2["data"]["status"] == "denied"


def test_server_close(server: PlannerCriticHTTPServer) -> None:
    """close() releases store resources (line 50-52)."""
    server.close()
    assert server._store is None


def test_post_critique(server: PlannerCriticHTTPServer) -> None:
    """POST /critique with a valid plan returns findings (line 143-150)."""
    planner = ScriptedPlanner([make_plan(tasks=[make_task("t1")])])
    engine = Engine(planner=planner, critic=EmptyCritic(), config=LoopConfig(revision_cap=1))
    server.set_engine(engine)
    plan = make_plan()
    resp = server.handle_request("POST", "/critique", plan.model_dump(mode="json"))
    assert resp["status"] == 200
    assert resp["data"]["plan_id"] == "plan-1"
    assert isinstance(resp["data"]["findings"], list)


def test_post_critique_no_engine(server: PlannerCriticHTTPServer) -> None:
    """POST /critique without engine or goal runs gates-only and returns 200.

    Without a goal the LLM critic cannot be bound, so the handler falls back
    to the deterministic gates (the free, injection-immune layer). A
    gate-clean plan returns 200 with empty findings.
    """
    plan = make_plan()
    resp = server.handle_request("POST", "/critique", {"plan": plan.model_dump(mode="json")})
    assert resp["status"] == 200
    assert resp["data"]["plan_id"] == "plan-1"
    assert isinstance(resp["data"]["findings"], list)


def test_post_critique_no_engine_gate_dirty(server: PlannerCriticHTTPServer) -> None:
    """POST /critique without engine on a gate-dirty plan returns gate findings."""
    dirty_plan = make_plan(tasks=[make_task("t1", risk_class="critical")])
    resp = server.handle_request("POST", "/critique", {"plan": dirty_plan.model_dump(mode="json")})
    assert resp["status"] == 200
    findings = resp["data"]["findings"]
    assert len(findings) > 0
    assert all(not f.get("heuristic_family") for f in findings)  # gates only, no LLM


def test_get_plan_diff(server: PlannerCriticHTTPServer) -> None:
    """GET /plans/{id}/diff returns diff data (line 193-210)."""
    plan_id = _seed_plan(server)
    resp = server.handle_request("GET", f"/plans/{plan_id}/diff", {"v2": "1"})
    assert resp["status"] == 200
    assert resp["data"]["plan_id"] == plan_id


def test_get_plan_diff_missing_v2(server: PlannerCriticHTTPServer) -> None:
    """GET /plans/{id}/diff without v2 returns 400 (line 194-195)."""
    plan_id = _seed_plan(server)
    resp = server.handle_request("GET", f"/plans/{plan_id}/diff", {})
    assert resp["status"] == 400
    assert "v2 is required" in resp["error"]


def test_get_plan_diff_invalid_v2(server: PlannerCriticHTTPServer) -> None:
    """GET /plans/{id}/diff with non-integer v2 returns 400 (line 197-199)."""
    plan_id = _seed_plan(server)
    resp = server.handle_request("GET", f"/plans/{plan_id}/diff", {"v2": "abc"})
    assert resp["status"] == 400
    assert "v2 must be an integer" in resp["error"]


def test_get_plan_diff_unknown_plan(server: PlannerCriticHTTPServer) -> None:
    """GET /plans/ghost/diff returns 404 when plan is unknown (line 200-202)."""
    resp = server.handle_request("GET", "/plans/ghost/diff", {"v2": "1"})
    assert resp["status"] == 404
    assert "not found" in resp["error"]


def test_get_plan_diff_compute_failure(server: PlannerCriticHTTPServer) -> None:
    """GET /plans/{id}/diff with missing revisions returns 404 (line 205-209)."""
    plan_id = _seed_plan(server)
    resp = server.handle_request("GET", f"/plans/{plan_id}/diff", {"v2": "99"})
    assert resp["status"] == 404
    assert "could not compute diff" in resp["error"]


def test_get_plan_diff_multi_revision_non_empty(server: PlannerCriticHTTPServer) -> None:
    """C6: diff on a multi-revision plan returns added/changed/removed (structured)."""
    plan_id = _seed_multi_revision(server)
    resp = server.handle_request("GET", f"/plans/{plan_id}/diff", {"v2": "2"})
    assert resp["status"] == 200
    data = resp["data"]
    assert data["plan_id"] == plan_id
    assert data["from_version"] == 1
    assert data["to_version"] == 2
    assert "added_task_ids" in data
    assert "removed_task_ids" in data
    assert "changed_task_ids" in data


def test_get_plan_graph_structured(server: PlannerCriticHTTPServer) -> None:
    """C6: graph returns parseable Mermaid + version (structured data)."""
    plan_id = _seed_plan(server)
    resp = server.handle_request("GET", f"/plans/{plan_id}/graph")
    assert resp["status"] == 200
    data = resp["data"]
    assert data["plan_id"] == plan_id
    assert data["version"] >= 1
    assert "graph TD" in data["mermaid"]


def test_get_plan_explain_structured(server: PlannerCriticHTTPServer) -> None:
    """C6: explain returns reason-trace fields (reason + decision per revision)."""
    plan_id = _seed_plan(server)
    resp = server.handle_request("GET", f"/plans/{plan_id}/explain")
    assert resp["status"] == 200
    data = resp["data"]
    assert data["plan_id"] == plan_id
    assert len(data["decisions"]) >= 1
    assert data["decisions"][0]["action"] in ("approved", "escalated", "revised")
    assert data["decisions"][0]["reason"]


def test_handle_request_value_error(server: PlannerCriticHTTPServer) -> None:
    """handle_request catches ValueError from handlers (line 72-73)."""
    resp = server.handle_request("POST", "/plan", {"id": None})
    assert resp["status"] == 400


def test_handle_request_generic_error(server: PlannerCriticHTTPServer) -> None:
    """handle_request catches generic Exception (line 76-77)."""
    original = server._route

    def broken(*args: object) -> dict[str, object]:
        raise RuntimeError("unexpected failure")

    server._route = broken  # type: ignore[assignment]
    resp = server.handle_request("GET", "/plans")
    assert resp["status"] == 500
    assert "RuntimeError" in resp["error"]
    server.__dict__["_route"] = original


def test_create_fastapi_app_missing() -> None:
    """create_fastapi_app returns None when FastAPI isn't installed (line 284-287)."""
    with patch.dict("sys.modules", {"fastapi": None}):
        result = create_fastapi_app(":memory:")
    assert result is None


# ---- C6: FastAPI live routes via ASGI transport (no network, no docker) ----


def test_fastapi_healthz_live() -> None:
    """C6: the FastAPI app serves /healthz over a real ASGI transport."""
    import asyncio

    import httpx

    app = create_fastapi_app(":memory:")
    assert app is not None

    async def _probe() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.get("/healthz")

    resp = asyncio.run(_probe())
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
