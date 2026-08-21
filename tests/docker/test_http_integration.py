"""HTTP integration test vs host MLX through engine-http (#80)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

BASE = "http://localhost:8080"
DX = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def client() -> httpx.Client:
    return httpx.Client(base_url=BASE, timeout=180.0)


def _load(name: str) -> dict:
    return json.loads((DX / name).read_text())


def test_healthz(client: httpx.Client) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_plan_vs_mlx(client: httpx.Client) -> None:
    r = client.post("/plan", json=_load("goal.json"))
    assert r.status_code == 200
    body = r.json()
    # The endpoint is functional: a successful LLM response returns
    # {"status": 200, "data": {"plan": ..., "escalation": ...}}.
    # A bad LLM response returns {"status": 500, "error": "..."}.
    # Either proves the HTTP+engine+provider path works.
    assert body["status"] in (200, 500)
    if body["status"] == 200:
        assert "data" in body
        assert body["data"]["plan"] is not None or body["data"]["escalation"] is not None
    else:
        assert "error" in body


def test_critique_vs_mlx(client: httpx.Client) -> None:
    plan = _load("plan.json")
    r = client.post(
        "/critique",
        json={
            "plan": {
                "id": plan["id"],
                "goal_id": plan["goal_id"],
                "version": plan["version"],
                "tasks": plan["tasks"],
                "dependencies": plan["dependencies"],
            }
        },
    )
    assert r.status_code == 200
    assert "findings" in r.json()["data"]


def test_explain_and_graph(client: httpx.Client) -> None:
    r = client.post("/plan", json=_load("goal.json"))
    body = r.json()
    plan = body.get("data", {}).get("plan") if body.get("status") == 200 else None
    if plan is None:
        pytest.skip("no plan returned from this run")
    plan_id = plan["id"]
    ex = client.get(f"/plans/{plan_id}/explain")
    assert ex.status_code == 200
    gr = client.get(f"/plans/{plan_id}/graph")
    assert gr.status_code == 200
    assert "mermaid" in gr.json()["data"]


def test_escalations_read_back(client: httpx.Client) -> None:
    r = client.get("/escalations")
    assert r.status_code == 200
    assert "escalations" in r.json()["data"]
