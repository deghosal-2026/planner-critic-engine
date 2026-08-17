# D5 — Provider Layer Design

> **Authored in:** M2 (Plan Store + LLM Provider Layer) · **Status:** Current baseline · **WBS:** D5 ·
> **Refs:** [PRD §2.4 provider layer](../design/prd/02-architecture.md#24-llm-provider-layer-built-registry-first), [§2.5 critique dual-mode](../design/prd/02-architecture.md#25-critique-engine-dual-mode), [D1 architecture](../architecture/architecture-v0.1.0.md)

## Goal

A config-driven, transport-agnostic provider seam: **providers in config, not
code**. The engine never imports a concrete model SDK; it talks to the
:class:`LLMProvider` protocol, and the registry materializes whatever the
config file says. Registry-first means the OpenAI-compatible transport is the
first concrete implementation *on top of* the registry (PRD §2.4), not instead
of it.

## Architecture

```
   engine / roles
        │  planner & critic each call a StructuredEnforcer
        ▼
   StructuredEnforcer (llm/structured.py)      ── F-24: validate + bounded retry
        │
        ▼
   LLMProvider protocol (llm/base.py)          ── F-20: complete(messages, tools)
        │
        ├── OpenAICompatibleProvider (llm/transport_openai.py)  ── F-22
        └── (future: Anthropic/Gemini transports on the same protocol)

   ProviderRegistry (llm/registry.py)          ── F-21/F-23: TOML config + role map
        │  read/write plancritic.toml
        ▼
   plancritic providers add/list/rm            ── CLI surface
```

## Key decisions

### Registry-first (F-21, DD-04)

Providers are defined in a TOML file (`plancritic.toml` by default):

```toml
[roles]
planner = "local"
critic = "local"

[providers."local"]
transport = "openai-compatible"
base_url = "http://localhost:11434/v1"
model = "llama3.2"
```

The registry loads this on demand; a missing file yields an **empty registry**
(roles unbound → `PlanningError`), never a crash. `plancritic providers
add/list/rm` mutates and persists it. This is the "cheap by design" wedge:
the default config points at local/cheap endpoints (OMLX, Ollama, vLLM), and a
paid provider is only used when explicitly registered (§2.4 cost control).

### Distinct planner vs. critic providers (F-23)

`[roles]` maps each role to a provider name, so planner and critic can use
different models — and a different *family* for the critic is recommended per
the blind-spot research. The engine resolves the provider per role through
`ProviderRegistry.get_provider(role)`.

### Thin protocol (F-20)

`LLMProvider` exposes one method — `complete(messages, tool_schemas)` →
`Completion(content, finish_reason)`. Content is a JSON string the enforcer
parses and re-validates; there is no transport-specific payload in the core.
Protocol is `@runtime_checkable` so a fake provider in tests is structurally
recognized without inheriting.

### Fail-closed error taxonomy (F-70)

| Error | Meaning | Loop result |
|-------|---------|-------------|
| `ProviderTimeout` | timeout / transport / HTTP error | `planning_unavailable` |
| `BadJSONError` | unparseable content | `planning_unavailable` (after retries) |
| `SchemaMismatchError` | content fails schema validation | retried; then `planning_unavailable` |
| `PlanningError` | persistent mismatch / unbound role | `planning_unavailable` |

A provider failure produces a distinct `planning_unavailable` per role (§7.2)
— no "guess and continue" path.

## Determinism & cost

- The loop is deterministic on identical inputs; the LLM is advisory and its
  output is **schema-revalidated** before it can influence a decision (§7.2).
- JSON mode (`response_format: {"type": "json_object"}`) is requested on the
  transport, but the enforcer never trusts it — schema validation is the
  gate, JSON mode is just an optimization.
- CI never calls a paid LLM: the hermetic gate is deterministic-only, and the
  provider tests use fake/mocked transports.

## Out of scope (M2)

- Non-OpenAI transports (Anthropic/Gemini) — same protocol, later milestones.
- Streaming / tool-calling orchestration — tool schemas are accepted by the
  protocol but not orchestrated by the core in M2.
- Cost telemetry per call — the loop budget (F-06) is enforced by the loop
  controller; per-call spend recording is M3+.
