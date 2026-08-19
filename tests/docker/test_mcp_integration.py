"""MCP integration test vs host MLX through engine-mcp (#81)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

BASE = "http://localhost:9090"
DX = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def client() -> httpx.Client:
    return httpx.Client(base_url=BASE, timeout=180.0)


def test_tools_list(client: httpx.Client) -> None:
    r = client.get("/tools")
    assert r.status_code == 200
    names = [t["name"] for t in r.json()["tools"]]
    assert "plan" in names and "critique" in names and "escalate_list" in names


def test_rpc_plan_vs_mlx(client: httpx.Client) -> None:
    goal = json.loads((DX / "goal.json").read_text())
    r = client.post("/rpc", json={"tool": "plan", "args": {"goal_json": json.dumps(goal)}})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "result" in body


def test_rpc_critique(client: httpx.Client) -> None:
    plan = json.loads((DX / "plan.json").read_text())
    r = client.post("/rpc", json={"tool": "critique", "args": {"plan_json": json.dumps(plan)}})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "findings" in body


def test_rpc_escalate_list(client: httpx.Client) -> None:
    r = client.post("/rpc", json={"tool": "escalate_list", "args": {}})
    assert r.status_code == 200
    assert r.json()["status"] == "ok"