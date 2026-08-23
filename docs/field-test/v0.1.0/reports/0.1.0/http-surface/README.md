# HTTP + MCP Surfaces — Field-Test Evidence (0.1.0, C6/C7/C26/C27)

> Dimensions: **http-surface**, **mcp-surface**, **mcp-http-surface**, **bootstrap** · Milestone: M1 (#86, 0.2.0) · Hermetic (no LLM, no docker) · Date: 2026-08-21

Closes the #86 gap where these surfaces lived only under `tests/docker/` (skipped without a compose stack) or were reported as "not run — Deferred to M10". All four are now verified hermetically.

## Capability-by-capability evidence

| Capability | Requirement (plan §5.1) | Hermetic verification | Result |
|------------|--------------------------|-----------------------|--------|
| C6 HTTP REST | plan/critique/plans/diff/graph/explain/escalations all 200; diff non-empty on multi-revision; explain structured | `tests/test_http_server.py` — full endpoint matrix via `PlannerCriticHTTPServer.handle_request`, FastAPI `/healthz` via ASGI transport | ✅ PASS |
| C7 MCP stdio | 6 tools; plan/critique/escalate_list/approve/deny | `tests/test_mcp_server.py`, `test_mcp_escalate.py` | ✅ PASS (existing) |
| C26 MCP-over-HTTP | /healthz /tools /rpc; output matches MCP stdio for identical input | `tests/test_mcp_http_surface.py` — real stdlib HTTP server + RPC parity with `handle_tool` | ✅ PASS |
| C27 HTTP config bootstrap | env-var TOML round-trips through ProviderRegistry | `tests/test_mcp_http_surface.py` — `bootstrap_config()` + defaults | ✅ PASS |

## New coverage added (this closure)

- `tests/test_mcp_http_surface.py` (8 tests): C26 endpoints (healthz/tools/rpc/unknown-route/unknown-tool), **stdio parity**, C27 bootstrap round-trip + defaults.
- `tests/test_http_server.py` (3 new tests): FastAPI `/healthz` live via ASGI transport, multi-revision diff non-empty, graph + explain structured output.

## Remaining (non-hermetic) scope for #86

- **C6/C7 against a real LLM** — the LLM-backed `plan`/`critique` endpoints need a live provider; hermetic coverage uses scripted roles (the same pattern as the rest of the 0.1.0 suite).
- **C26 byte-parity vs actual stdio subprocess** — the parity test compares HTTP `/rpc` to the transport-agnostic `handle_tool` result (the shared code path), which is the meaningful parity guarantee; a subprocess stdio round-trip is covered by `tests/test_mcp_server.py`.