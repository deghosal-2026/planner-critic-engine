"""In-container CLI smoke test (WBS #79): run plancritic inside the image.

The heavy live-LLM plan path is exercised by HTTP/MCP integration tests and
the loop test; here we keep fast, deterministic surface checks that prove the
image ships a working ``plancritic`` with the provider CLI wired up.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

IMAGE = "planner-critic-engine:test"
FIXTURES = Path(__file__).parent / "fixtures"


def _run_in_container(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "run", "--rm", "--network", "host",
         "-v", f"{FIXTURES}:/fixtures:ro",
         IMAGE, *args],
        capture_output=True,
        text=True,
        timeout=300,
    )


def test_cli_version() -> None:
    proc = _run_in_container("--version")
    assert proc.returncode == 0
    assert "plancritic" in proc.stdout


def test_cli_providers_add() -> None:
    proc = _run_in_container(
        "providers", "--config", "/tmp/plancritic.toml",
        "add", "local",
        "--base-url", "http://127.0.0.1:8000/v1",
        "--model", "Qwen3.5-9B-MLX-4bit",
        "--role", "planner",
    )
    assert proc.returncode == 0, proc.stderr


def test_cli_critique_deterministic() -> None:
    proc = _run_in_container("critique", "/fixtures/plan.json")
    assert proc.returncode in (0, 1), proc.stderr
