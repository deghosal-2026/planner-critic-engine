"""Container entrypoint: uvicorn + FastAPI for the HTTP surface (M8).

Builds a provider config from PC_* env, binds planner/critic roles, and
serves :func:`~planner_critic.server.http.create_fastapi_app` on PC_PORT.
"""

from __future__ import annotations

import os

from ..llm.registry import ProviderRegistry

DEFAULT_PORT = "8080"
DEFAULT_STORE = "/data/plans.db"
DEFAULT_CONFIG = "/data/plancritic.toml"


def bootstrap_config() -> None:
    """Write a plancritic.toml binding planner/critic to the host MLX endpoint."""
    base_url = os.environ.get("PC_OMLX_BASE_URL", "http://host.docker.internal:8000/v1")
    model = os.environ.get("PC_OMLX_MODEL", "")
    config = os.environ.get("PC_CONFIG", DEFAULT_CONFIG)
    registry = ProviderRegistry.load(config)
    registry.add("local", base_url=base_url, model=model, role="planner")
    registry.add("local", base_url=base_url, model=model, role="critic")
    registry.save()


def main() -> None:
    bootstrap_config()
    import uvicorn

    from .http import create_fastapi_app

    store = os.environ.get("PC_STORE", DEFAULT_STORE)
    config = os.environ.get("PC_CONFIG", DEFAULT_CONFIG)
    port = int(os.environ.get("PC_PORT", DEFAULT_PORT))
    app = create_fastapi_app(store, config_path=config)
    if app is None:
        raise RuntimeError("fastapi extra not installed")
    uvicorn.run(app, host="0.0.0.0", port=port)  # noqa: S104 - container binding to all interfaces


if __name__ == "__main__":  # pragma: no cover
    main()
