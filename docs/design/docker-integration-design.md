# D19 — Docker Integration Test Design (M8)

> **Milestone:** M8 — Docker Integration Tests (containerized engine + delivery surfaces vs a real local LLM)
> **WBS:** `docs/wbs/v0.1.0/wbs-v0.1.0-part5-docker-integration.md`
> **PRD:** [02-architecture](../design/prd/02-architecture.md) (§2.4 hermetic, §2.10 terminal state) · [05-features](../design/prd/05-features.md) (§5.9) · [07-success-metrics](../design/prd/07-success-metrics.md) (§7.1)
> **Related decisions:** D13 (DD-11 containerized local LLM, DD-12 docker gate before field test)

## Objective

Prove the engine ships as a runnable artifact and its delivery surfaces (CLI, HTTP
service, MCP server) work end-to-end against a **real local LLM**, replacing "works on
my machine" with a reproducible containerized integration gate before the M9 field
sweep. **No paid LLM.**

## Design Decisions

### DD-M8-1 — Host MLX as the benchmark LLM (deviation from WBS)

The WBS proposed a containerized `llm` service (OMLX/Ollama). Decided: **reuse host
MLX** instead. MLX is macOS-only and cannot be containerized; the host already runs
`Qwen3.5-9B-MLX-4bit` at `http://127.0.0.1:8000/v1`. Compose therefore has **two**
services (`engine-http`, `engine-mcp`) that reach MLX through `host.docker.internal`.

- **Win:** reuses the proven M7 transport (thinking-mode fix landed there); smaller
  compose/CI footprint; no extra model pull.
- **Lose:** the LLM is not part of the topology, so the integration gate is not fully
  portable to non-MLX hosts.
- **Mitigation:** containers configure the LLM purely via `PC_OMLX_BASE_URL` /
  `PC_OMLX_MODEL` — the same image runs against Ollama/vLLM later with zero code
  change. The M9 field sweep still exercises additional local-model runtimes.
- **CI:** because MLX cannot run on GitHub-hosted runners, the workflow is opt-in via
  `workflow_dispatch` (documented skip path), exactly as the WBS allows.

### DD-M8-2 — No new server framework; wrap existing sprint surfaces

M5/M6 already shipped transport-agnostic servers:
- HTTP: `PlannerCriticHTTPServer.handle_request()` + `create_fastapi_app()` factory
  (`src/planner_critic/server/http.py`).
- MCP: `handle_tool()` / `list_tools()` / `run_stdio()` (`src/planner_critic/server/mcp.py`),
  built to be wrapped by any transport (FastMCP, HTTP, gRPC).

For containers we add the minimal glue: a uvicorn entry point that mounts
`create_fastapi_app()` for `engine-http`, and a JSON-lines-over-HTTP MCP adapter that
exposes the existing `list_tools`/`handle_tool` logic for `engine-mcp`. No new HTTP/MCP
library dependency beyond what the core already uses (`httpx`, stdlib `http.server`).

### DD-M8-3 — Fail-closed on provider outage surfaces reason codes

The M7 truncation work established fail-closed semantics in the transport (non-`stop`
`finish_reason` → `ProviderTimeout`). The in-container HTTP/MCP paths must surface the
same faithful `reason_code` / `status` back to callers, and a stopped provider must not
produce a half-planned artifact anywhere in the loop.

## Container Topology

```
┌──────────────────────────── host ────────────────────────────┐
│  MLX server (Qwen3.5-9B-MLX-4bit) @ 127.0.0.1:8000/v1       │
└─────────────────────────────▲────────────────────────────────┘
                              │ host.docker.internal:8000/v1
              ┌───────────────┴────────────────┐
              │                                │
      ┌───────┴───────┐               ┌────────┴────────┐
      │  engine-http  │               │    engine-mcp   │
      │  :8080  FastAPI            │  :9090  JSON-lines │
      │  /healthz                 │  /healthz          │
      │  /plan /critique /explain │  tools/list…       │
      │  /escalations /plans*       │  handle_tool…      │
      └───────────────┘               └──────────────────┘
```

- `engine-http` env: `PC_OMLX_BASE_URL=http://host.docker.internal:8000/v1`,
  `PC_OMLX_MODEL=Qwen3.5-9B-MLX-4bit`, store path `/data/plans.db` (mounted volume).
- `engine-mcp` env: same LLM wiring; store path `/data/plans.db`.
- Healthchecks: `curl -f http://localhost:PORT/healthz`; `depends_on` + healthy gating,
  `extra_hosts: ["host.docker.internal:host-gateway"]`.

## Dockerfile (multi-stage)

| Stage  | Base | Does |
|--------|------|------|
| builder | `python:3.12` | `pip install hatchling`, `pip wheel . -w /wheels` |
| runtime | `python:3.12-slim` | copy wheel, `pip install`, non-root `nobody`, no secrets, entrypoint script |

Guards: `plancritic` on `$PATH`; container runs as non-root; no env-secret baking.

## Delivery-Surface Tests (`tests/docker/`)

All are pytest modules that skip cleanly with a clear reason when compose/LLM is
unreachable, so the hermetic suite stays green on hosts without Docker or MLX.

| File | Covers | Assert |
|------|--------|--------|
| `test_cli_smoke.py` | `docker run` image: `--version`, `init`, `providers add`, `plan`, `critique` | exit 0; seeded goal planned+critiqued |
| `test_http_integration.py` | `/plan` `/critique` `/explain`, escalation, graph endpoints | reason codes; findings; fail-closed status on provider outage |
| `test_mcp_integration.py` | MCP client → `tools/list` + `plan`/`critique`/`escalate_list` round-trip | typed plan/findings over the wire |
| `test_loop_real_llm.py` | full loop in `heuristic-only` / `deterministic-first` / `llm-every-revision` vs host MLX | seeded critical-risk plan escalated/blocked, never approved |

The real-LLM loop is the containerized twin of the M9 #74–#76 field sweep.

## CI

`.github/workflows/docker-integration.yml`:

- `workflow_dispatch` opt-in (MLX host required; hosted runners cannot run MLX).
- On a self-hosted/MLX-capable runner: `docker compose up --build -d` → run
  `make integration` → `docker compose down`.
- Hermetic-safe: no paid LLM, no API key (MLX needs none).

## Runner + Docs

- `make integration`: builds image, starts compose, runs `tests/docker/`, tears down.
- `docs/field-test/docker-integration.md`: topology, host-LLM caveats, repro steps,
  CI opt-in note.

## Exit Gate Checklist

- [ ] Dockerfile + compose reviewed; multi-stage; non-root; no secrets
- [ ] Coverage > 95% (no regression, hermetic suite)
- [ ] Lint clean (ruff + mypy strict)
- [ ] CLI smoke + HTTP + MCP integration pass vs host MLX
- [ ] Real-LLM loop passes in all three critique modes
- [ ] CI workflow green (or documented opt-in)
- [ ] D13 DD-13/DD-14 recorded