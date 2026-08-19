"""Hermetic checks for the MCP-over-HTTP adapter + healthz routes."""

from __future__ import annotations

import json
import threading
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

from planner_critic.server.http import create_fastapi_app
from planner_critic.server.mcp_http import MCPHTTPServer, serve_mcp_http


@pytest.fixture(scope="module")
def mcp_server() -> Iterator[MCPHTTPServer]:
    server = serve_mcp_http(store_path=":memory:", host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()


def _get(url: str) -> tuple[int, dict]:
    with urllib.request.urlopen(url, timeout=5) as resp:
        return resp.status, json.loads(resp.read())


def _post(url: str, payload: dict) -> tuple[int, dict]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read())


def _base(mcp_server: MCPHTTPServer) -> str:
    host = str(mcp_server.server_address[0])
    port = int(mcp_server.server_address[1])
    return f"http://{host}:{port}"


def test_mcp_healthz(mcp_server: MCPHTTPServer) -> None:
    status, body = _get(f"{_base(mcp_server)}/healthz")
    assert status == 200
    assert body == {"status": "ok"}


def test_mcp_tools_get(mcp_server: MCPHTTPServer) -> None:
    status, body = _get(f"{_base(mcp_server)}/tools")
    assert status == 200
    names = [t["name"] for t in body["tools"]]
    assert "plan" in names and "critique" in names and "escalate_list" in names


def test_mcp_escalate_list_roundtrip(mcp_server: MCPHTTPServer) -> None:
    status, body = _post(f"{_base(mcp_server)}/rpc", {"tool": "escalate_list", "args": {}})
    assert status == 200
    assert body["status"] == "ok"
    assert "escalations" in body


def test_http_app_has_healthz_route() -> None:
    app = create_fastapi_app(":memory:")
    if app is None:
        pytest.skip("FastAPI not installed in this env")
    routes = {getattr(r, "path", None) for r in app.routes}
    assert "/healthz" in routes


def test_bootstrap_config_writes_toml(tmp_path: Path) -> None:
    import os

    from planner_critic.server import http_serve

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

    from planner_critic.llm.registry import ProviderRegistry

    registry = ProviderRegistry.load(config)
    assert registry.roles == {"planner": "local", "critic": "local"}
    assert registry.providers["local"].base_url == "http://127.0.0.1:8000/v1"
    assert registry.providers["local"].model == "test-model"
    assert registry.providers["local"].api_key == "test-key"
