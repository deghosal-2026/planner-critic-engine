"""Hermetic tests for the MCP-over-HTTP adapter and HTTP config bootstrap.

Closes the #86 field-test gap: the MCP-over-HTTP surface (C26) and the HTTP
config bootstrap (C27) previously lived only under ``tests/docker/`` and were
skipped without a running compose stack. These tests run them against a real
stdlib HTTP server + temp-file SQLite — no docker, no network, no LLM.

C26 parity: MCP-over-HTTP must produce the *identical* response body as MCP
stdio for the same ``(tool, args)`` input. We drive both transports from the
same :class:`PlannerCriticMCPServer` instance and compare.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from planner_critic.llm.registry import ProviderRegistry
from planner_critic.schema.plan import PlanVersion
from planner_critic.server import http_serve
from planner_critic.server.mcp import PlannerCriticMCPServer
from planner_critic.server.mcp_http import MCPHTTPServer, serve_mcp_http
from planner_critic.store.sqlite import SQLiteStore
from planner_critic.types import Escalation


@pytest.fixture(scope="module")
def mcp_http_server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[MCPHTTPServer]:
    """A real MCP-over-HTTP server bound to an ephemeral port on a temp store."""
    store_path = str(tmp_path_factory.mktemp("mcp-http") / "plans.db")
    server = serve_mcp_http(store_path=store_path, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()


def _get(url: str) -> tuple[int, dict[str, Any]]:
    """GET a URL and return (status, JSON body); 4xx/5xx are returned not raised."""
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


def _post(url: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """POST JSON to a URL and return (status, JSON body)."""
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read())


def _base(mcp_http_server: MCPHTTPServer) -> str:
    """The base URL for a bound MCP-over-HTTP server."""
    host = str(mcp_http_server.server_address[0])
    port = int(mcp_http_server.server_address[1])
    return f"http://{host}:{port}"


def _seed_escalation(store_path: str) -> str:
    """Seed an open escalation and return its id (C26 round-trip target)."""
    store = SQLiteStore(store_path)
    store.put_plan_version(
        PlanVersion.model_validate(
            {
                "id": "plan-1",
                "goal_id": "g1",
                "version": 1,
                "tasks": [],
                "dependencies": [],
                "branches": [],
            }
        )
    )
    store.put_escalation(
        Escalation(id="esc:plan-1:1", plan_id="plan-1", version=1, question="proceed?")
    )
    store.close()
    return "esc:plan-1:1"


# ---- C26: MCP-over-HTTP endpoints -----------------------------------------


def test_mcp_http_healthz(mcp_http_server: MCPHTTPServer) -> None:
    """GET /healthz returns 200 + ok (C26 health)."""
    status, body = _get(f"{_base(mcp_http_server)}/healthz")
    assert status == 200
    assert body == {"status": "ok"}


def test_mcp_http_tools_get(mcp_http_server: MCPHTTPServer) -> None:
    """GET /tools exposes the 6 MCP tools (C26 tools/list)."""
    status, body = _get(f"{_base(mcp_http_server)}/tools")
    assert status == 200
    names = {t["name"] for t in body["tools"]}
    assert names == {
        "plan",
        "critique",
        "explain",
        "escalate_list",
        "escalate_approve",
        "escalate_deny",
    }


def test_mcp_http_escalate_list_roundtrip(mcp_http_server: MCPHTTPServer) -> None:
    """POST /rpc escalate_list returns the seeded escalation (C26 rpc)."""
    store_path = str(mcp_http_server.mcp.store_path)
    esc_id = _seed_escalation(store_path)
    status, body = _post(f"{_base(mcp_http_server)}/rpc", {"tool": "escalate_list", "args": {}})
    assert status == 200
    assert body["status"] == "ok"
    assert esc_id in [e["id"] for e in body["escalations"]]


def test_mcp_http_unknown_route(mcp_http_server: MCPHTTPServer) -> None:
    """GET /nope returns 404 (C26 routing)."""
    status, body = _get(f"{_base(mcp_http_server)}/nope")
    assert status == 404
    assert body["status"] == "error"


def test_mcp_http_unknown_tool(mcp_http_server: MCPHTTPServer) -> None:
    """POST /rpc with an unknown tool returns an errored result (C26)."""
    status, body = _post(f"{_base(mcp_http_server)}/rpc", {"tool": "nope", "args": {}})
    assert status == 200  # the adapter returns 200 with an error body
    assert body["status"] == "error"


def test_mcp_http_parity_with_stdio(tmp_path: Path) -> None:
    """C26 parity: MCP-over-HTTP output matches the stdio transport.

    Both transports ultimately call :meth:`PlannerCriticMCPServer.handle_tool`
    on the same server instance; the on-the-wire response must match the
    transport-agnostic result for identical input. We compare the HTTP /rpc
    response body to ``handle_tool``'s result (which stdio serializes).
    """
    store_path = str(tmp_path / "parity.db")
    esc_id = _seed_escalation(store_path)
    mcp = PlannerCriticMCPServer(store_path=store_path)
    request: dict[str, Any] = {"tool": "escalate_list", "args": {"status": "open"}}

    expected = mcp.handle_tool(request["tool"], request["args"])

    server = MCPHTTPServer("127.0.0.1", 0, mcp)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, http_body = _post(f"http://127.0.0.1:{server.server_address[1]}/rpc", request)
    finally:
        server.shutdown()

    assert status == 200
    assert json.dumps(http_body, sort_keys=True) == json.dumps(expected, sort_keys=True)
    assert esc_id in [e["id"] for e in http_body["escalations"]]


# ---- C27: HTTP config bootstrap -------------------------------------------


def test_bootstrap_config_env_round_trip(tmp_path: Path) -> None:
    """C27: ``bootstrap_config()`` writes a TOML that round-trips via the registry.

    The env-var-driven bootstrap must produce a provider config that
    ``ProviderRegistry.load`` reads back with identical base_url/model/api_key
    and the planner/critic role bindings.
    """
    config = tmp_path / "plancritic.toml"
    env = {
        "PC_OPENAI_BASE_URL": "http://127.0.0.1:8000/v1",
        "PC_OPENAI_MODEL": "test-model",
        "PC_OPENAI_API_KEY": "test-key",
        "PC_CONFIG": str(config),
    }
    old = {k: os.environ.pop(k, None) for k in env}
    os.environ.update(env)
    try:
        http_serve.bootstrap_config()
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    registry = ProviderRegistry.load(config)
    assert registry.roles == {"planner": "local", "critic": "local"}
    assert registry.providers["local"].base_url == "http://127.0.0.1:8000/v1"
    assert registry.providers["local"].model == "test-model"
    assert registry.providers["local"].api_key == "test-key"


def test_bootstrap_config_defaults(tmp_path: Path) -> None:
    """C27: without env vars, bootstrap uses sensible OpenRouter defaults."""
    config = tmp_path / "plancritic.toml"
    env = {"PC_CONFIG": str(config), "PC_OPENAI_MODEL": ""}
    old = {k: os.environ.pop(k, None) for k in env}
    os.environ.update(env)
    try:
        http_serve.bootstrap_config()
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    registry = ProviderRegistry.load(config)
    assert registry.providers["local"].base_url == "https://openrouter.ai/api/v1"
    assert registry.providers["local"].model == ""
