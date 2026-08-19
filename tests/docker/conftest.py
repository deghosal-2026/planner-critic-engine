"""Shared fixtures for tests/docker.

Everything here SKIPs unless PC_INTEGRATION=1 AND the compose services are
healthy, so the hermetic suite stays green on hosts without Docker/MLX.
"""

from __future__ import annotations

import os
import subprocess

import pytest

PC_INTEGRATION = os.environ.get("PC_INTEGRATION") == "1"

# Modules that require live compose services + MLX. test_healthz.py is
# hermetic (adapter + healthz + bootstrap_config) and always runs.
_INTEGRATION_MODULES = {
    "test_cli_smoke",
    "test_http_integration",
    "test_mcp_integration",
    "test_loop_real_llm",
}


def _compose_up() -> bool:
    if not PC_INTEGRATION:
        return False
    try:
        probe = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return probe.returncode == 0 and "engine-http" in probe.stdout
    except (OSError, subprocess.SubprocessError):
        return False


def pytest_collection_modifyitems(session: pytest.Session, items: list[pytest.Item]) -> None:
    skip_integration = not _compose_up()
    if not skip_integration:
        return
    for item in items:
        module = getattr(item, "module", None)
        module_name = getattr(module, "__name__", "").rsplit(".", 1)[-1]
        if module_name in _INTEGRATION_MODULES:
            item.add_marker(
                pytest.mark.skip(
                    reason=(
                        "docker compose not healthy;"
                        " run 'docker compose up -d' then PC_INTEGRATION=1"
                    ),
                )
            )
