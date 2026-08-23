"""Cover remaining gap lines in http_serve and gates."""

from __future__ import annotations

import os
from pathlib import Path

from planner_critic.server import http_serve


def test_http_serve_bootstrap_defaults(tmp_path: Path) -> None:
    config = str(tmp_path / "plancritic.toml")
    env = {"PC_CONFIG": config, "PC_OPENAI_MODEL": ""}
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


def test_http_server_close_stress() -> None:
    from planner_critic.server.http import PlannerCriticHTTPServer

    server = PlannerCriticHTTPServer(store_path=":memory:")
    server.close()
    server.close()
