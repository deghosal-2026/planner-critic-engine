# DecisionContext — Sourcing Convention

> Shipped in v0.2.3 ([#298](https://github.com/deghosal-2026/planner-critic-engine/issues/298)).
> Identified by Peter ([dev.to](https://dev.to/peterbuildssecure/comment/3dml0)).

## The Problem

`DecisionContext` captures per-trial metadata (model id, version, temperature, prompt hash, tool-schema hash) so label shifts in the boundary evaluator can be attributed to prompt changes, model version changes, or genuine stochasticity.

If metadata is read from the critic's own response, a critic that has already drifted (wrong tool binding, stale prompt) can misreport the metadata meant to explain the drift. The decision context inherits the same self-report problem the evaluator was built to escape.

## The Convention

**`DecisionContext` fields must be sourced from the harness's own call parameters — the request you sent, not anything in the response.**

| Field | Source | Example |
|-------|--------|---------|
| `model_id` | ProviderSpec.model or config | `"openai/gpt-4o-mini"` |
| `model_version` | ProviderSpec.model_version (optional TOML field) | `"2024-07-18"` |
| `temperature` | ProviderSpec.temperature (optional TOML field) | `0.0` |
| `system_prompt_hash` | SHA-256 of the prompt constant at call time | `"a1b2c3d4e5f6..."` |
| `tool_schema_hash` | SHA-256 of tool schemas (N/A for JSON mode) | `""` |
| `timestamp` | UTC timestamp from the caller | `"2026-08-29T12:00:00+00:00"` |

If the provider transport returns model info in the API response, that info is recorded as a **separate field** (`response_model_id`, `response_model_version`) so the two sources are independently auditable.