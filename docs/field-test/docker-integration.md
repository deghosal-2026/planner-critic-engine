# Docker Integration Test Design (WBS D19)
#
# ## Topology
#
# ```
# ┌─────────────────────────────────────────────┐
# │  docker-compose.yml                          │
# │                                              │
# │  ┌──────────────┐   ┌──────────────┐        │
# │  │  engine-http  │   │  engine-mcp   │        │
# │  │  :8080        │   │  :9090        │        │
# │  │  FastAPI      │   │  MCP-HTTP     │        │
# │  └──────┬───────┘   └──────┬───────┘        │
# │         │                  │                 │
# │         └────────┬─────────┘                 │
# │                  │                           │
# │         ┌────────▼────────┐                  │
# │         │  llm (host)     │                  │
# │         │  OMLX/Ollama    │                  │
# │         │  :8000/v1       │                  │
# │         └─────────────────┘                  │
# └─────────────────────────────────────────────┘
# ```
#
# The `llm` service runs on the **host** (not in a container). The engine
# containers connect via `host.docker.internal:8000/v1`. This keeps the model
# accessible without GPU passthrough complexity.
#
# ### Services
#
# | Service | Entrypoint | Port | Role |
# |---------|-----------|------|------|
# | `engine-http` | `http_serve.py` | 8080 | REST surface (FastAPI) |
# | `engine-mcp`  | `mcp_http_run.py` | 9090 | MCP-over-HTTP surface |
#
# ### Environment
#
# Both engine containers share the same env vars:
# - `PC_OMLX_BASE_URL` — local LLM endpoint
# - `PC_OMLX_MODEL` — model name
# - `PC_STORE` — SQLite database path (shared volume)
# - `PC_CONFIG` — provider TOML config path
#
# ## CI Strategy
#
# The CI workflow (`docker-integration.yml`) is **opt-in via workflow_dispatch**
# because the current local-model image (Qwen3.5-9B-MLX-4bit) is too heavy for
# standard GitHub hosted runners. When the model image stabilises at a lighter
# footprint, the workflow can switch to `push` / `pull_request` triggers.
#
# ### Running locally
#
# ```bash
# # Start a local LLM (OMLX or Ollama) at localhost:8000/v1
# # Then:
# make integration
# ```
#
# ## Critique Modes Under Containers
#
# The engine runs in `deterministic-first` mode by default (see LoopConfig).
# The three modes are validated as follows:
#
# | Mode | Container test | Assertion |
# |------|---------------|-----------|
# | heuristic-only | adversarial goal → gate blockers → escalated | fail-closed, no LLM needed |
# | deterministic-first | normal goal → gates + LLM → result | structured plan/findings returned |
# | llm-every-revision | full loop via container stack | clean termination (approve/escalate) |
#
# ## Healthchecks
#
# Each engine container has a `/healthz` endpoint checked via Docker healthcheck.
# The test conftest waits for compose to be healthy before running integration
# tests.
#
# ## Dependencies
#
# - Docker Desktop or equivalent
# - Local LLM endpoint (OMLX/Ollama) at the configured `PC_OMLX_BASE_URL`
# - Python 3.12+ for the test runner