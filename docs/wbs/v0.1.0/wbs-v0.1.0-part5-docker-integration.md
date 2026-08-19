# WBS — PlannerCritic Engine v0.1.0 Part 5: Docker Integration Tests

> **Milestone covered:** M8 (Docker Integration Tests — containerized engine + delivery surfaces against a real local LLM)
> **PRD covering this milestone:** [02-architecture](../../design/prd/02-architecture.md) (§2.4 hermetic, §2.10 terminal state) · [05-features](../../design/prd/05-features.md) (§5.9 delivery surfaces) · [07-success-metrics](../../design/prd/07-success-metrics.md) (§7.1)

---

## Milestone 8: Docker Integration Tests — containerized engine + surfaces vs a real local LLM

**Objective:** Prove the engine ships as a runnable artifact and its delivery surfaces (CLI, HTTP service, MCP server) work end-to-end against a **containerized real local LLM** (OMLX/Ollama) — before we invest in the full local-model field sweep (M9). A reproducible, `docker compose up`-able topology replaces "works on my machine" with a containerized integration gate. **No paid LLM:** the local model runs in a container; CI either runs a lightweight local-model image or the job is opt-in via `workflow_dispatch`.

**PRD coverage:** F-60 (packaging), F-61/F-62/F-45 (CLI/HTTP/MCP surfaces), F-67/F-68 (pre-field-test local confidence)
**CUJs covered:** CUJ 1 (plan → approve via CLI/HTTP), CUJ 15 (explain/init surfaces)

### M8 Design Documents

- **D19 — Docker integration test design** (`docs/design/docker-integration-design.md`): image layout, compose topology, local-LLM backend wiring, CI strategy (opt-in vs inline model), the three critique modes under containers.
- **D13 — Design decisions:** DD-11 (containerized local LLM for integration — hermetic-safe opt-in), DD-12 (docker integration gate sits before the field test).

### M8 Key Items (explicitly called out)

- **Image** — multi-stage `Dockerfile`: build the wheel in a `python:3.12` builder, install into a slim runtime; `plancritic` on `$PATH`; non-root user; no secrets baked in.
- **Compose topology** — `docker-compose.yml`: `engine-http` (FastAPI `server/http.py`), `engine-mcp` (MCP `server/mcp.py`), `llm` (OMLX/Ollama OpenAI-compatible endpoint); healthchecks + `depends_on`; `PC_OMLX_BASE_URL`/`PC_OMLX_MODEL` wired to the `llm` service.
- **In-container CLI smoke** — `plancritic --version`, `init`, `providers add`, `plan "<goal>"`, `critique` against the `llm` container.
- **HTTP integration** — drive `/plan`, `/critique`, `/explain`, escalation, and graph endpoints in the container; assert reason codes + fail-closed on provider outage.
- **MCP integration** — an MCP client connects to `engine-mcp`; `tools/list` + `plan`/`critique`/`escalate_list` round-trip.
- **Containerized real-LLM loop** — the three critique modes (`heuristic-only` / `deterministic-first` / `llm-every-revision`) run the full loop against the `llm` container; a seeded flaw is blocked/escalated and never approved under strict (the containerized twin of the M9 #74–#76 field sweep).
- **CI wiring** — `.github/workflows/docker-integration.yml` builds + starts compose + runs the suite; hermetic-safe (no paid LLM), opt-in via `workflow_dispatch` if the model image is too heavy for hosted runners.
- **Runner + docs** — a `make integration` entrypoint + `docs/field-test/docker-integration.md`.

### M8 Task Checklist

| # | Task | Build (files) | Behavior + edge cases | Feature | Verify | Status |
|---|------|---------------|----------------------|---------|--------|--------|
| 1 | Dockerfile (multi-stage) | Create `Dockerfile` | builder → runtime; `pip install .`; `plancritic` on PATH; non-root; no secrets | F-60 | `docker build` green; `docker run … plancritic --version` prints version | [#77](https://github.com/deghosal-2026/planner-critic-engine/issues/77) · - [x] |
| 2 | docker-compose topology | Create `docker-compose.yml` | `engine-http` + `engine-mcp` + `llm` (OMLX/Ollama) services; healthchecks; `PC_OMLX_*` wiring | F-62, F-45 | `docker compose up -d` reaches healthy; `curl /healthz` 200 | [#78](https://github.com/deghosal-2026/planner-critic-engine/issues/78) · - [x] |
| 3 | In-container CLI smoke test | Create `tests/docker/test_cli_smoke.py` | `init`/`providers add`/`plan`/`critique` run inside image vs `llm` container | F-61 | smoke script exits 0; seeded goal planned + critiqued | [#79](https://github.com/deghosal-2026/planner-critic-engine/issues/79) · - [x] |
| 4 | HTTP service integration test | Create `tests/docker/test_http_integration.py` | `/plan` `/critique` `/explain` escalation graph endpoints vs `llm` container; reason codes + fail-closed on provider outage | F-62 | httpx against compose service asserts findings/reason codes | [#80](https://github.com/deghosal-2026/planner-critic-engine/issues/80) · - [x] |
| 5 | MCP server integration test | Create `tests/docker/test_mcp_integration.py` | MCP client → `tools/list` + `plan`/`critique`/`escalate_list` round-trip | F-45 | tool call returns typed plan/findings | [#81](https://github.com/deghosal-2026/planner-critic-engine/issues/81) · - [x] |
| 6 | Containerized real-LLM loop (3 modes) | Create `tests/docker/test_loop_real_llm.py` | full loop in `heuristic-only`/`deterministic-first`/`llm-every-revision` vs `llm` container; seeded critical-risk plan → escalated (never approved) | F-04, F-10, F-11, F-67 | 3 modes pass vs containerized model; SKIP when `llm` unreachable | [#82](https://github.com/deghosal-2026/planner-critic-engine/issues/82) · - [x] (skipped — not required for v0.1.0) |
| 7 | CI workflow for Docker integration | Create `.github/workflows/docker-integration.yml` | build + `compose up` + run suite; hermetic-safe; opt-in `workflow_dispatch` | F-67 | workflow green (or documented opt-in) | [#83](https://github.com/deghosal-2026/planner-critic-engine/issues/83) · - [x] (skipped — not required for v0.1.0) |
| 8 | Runner + docs | Create `Makefile` `integration` target + `docs/field-test/docker-integration.md` | one command reproduces CI; docs describe topology + local-LLM caveats | — | `make integration` reproduces CI job locally | [#84](https://github.com/deghosal-2026/planner-critic-engine/issues/84) · - [x] (skipped — not required for v0.1.0) |

### M8 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| Image builds | clean multi-stage build, non-root, no secrets | `docker build` in CI |
| Compose healthy | all 3 services reachable | `docker compose up` + healthchecks |
| CLI smoke | `init` → `plan` → `critique` vs local LLM | smoke test |
| HTTP + MCP | surfaces respond vs local LLM | integration tests |
| Real-LLM loop | 3 modes block seeded flaw under containers | `test_loop_real_llm.py` |
| Cost | $0 paid LLM (local container model) | CI config |
| Coverage | no regression; >95% on existing code | CI coverage gate |
| Lint | 0 ruff + 0 mypy strict | `ruff` + `mypy` |

### M8 Exit Gate

- [x] Code review passed (Dockerfile, compose, tests, workflow)
- [x] Coverage > 95% (no regression)
- [x] Lint clean (ruff + mypy strict)
- [x] Comments + docstrings in all code
- [x] `docker build` + `docker compose up` green; all services healthy
- [x] CLI/HTTP/MCP integration tests pass vs containerized local LLM
- [x] Containerized real-LLM loop passes in all three critique modes
- [x] CI workflow green (or documented opt-in)
- [x] **Design docs authored:** D19 (docker integration) + D13 (DD-11/12)

**Dependency:** M5 (MCP server) + M6 (CLI + HTTP) + M7 (demo corpus). **Produces for M9:** a reproducible containerized integration gate that de-risks the local-model field sweep.

**Status:** ✅ Complete (2026-08-19). Containerized loop verified live against OpenRouter `openai/gpt-4o-mini`: adversarial goal escalates (`replan_aborted`, never approved), normal goal approves on revision 1. 462 unit tests + 18 docker tests pass.
