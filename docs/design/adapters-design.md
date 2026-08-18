# D9 — Adapter Design

> **Authored in:** M5 (Framework Adapters) · **Status:** Current baseline · **WBS:** D9 ·
> **Refs:** [PRD §2.3 adapter architecture](../design/prd/02-architecture.md#23-adapter-architecture), [§2.7b re-gate](../design/prd/02-architecture.md#27b-replan-semantics-mid-execution), [DD-11 adapter gate-not-execute boundary](../design/design-decisions.md#m5--m6-entries), [D1 architecture](../architecture/architecture-v0.1.0.md)

## Goal

Let an approved plan gate real agent loops in the six supported frameworks without the framework owning the approval decision. Every adapter audits approval + re-gate decisions, gates and serializes, but never runs the plan itself.

## The six adapters

| Adapter | File | Pattern | Gate point |
|---------|------|---------|------------|
| Raw Python | `adapters/python.py` | `plan()` function + `PlannerCriticPlan` class | At call site |
| LangGraph | `adapters/langgraph.py` | Pre-execution node/callback via `ApprovalHook` | Before each graph node |
| PydanticAI | `adapters/pydantic_ai.py` | `ApprovalGuard` class with `guard(ctx)` | Before first tool call |
| CrewAI | `adapters/crewai.py` | `PlanAwareTaskInterceptor` | Before each task |
| OpenAI Agents SDK | `adapters/openai_agents.py` | `PlanGuardrail` with `check()` | Before each tool call |
| MCP server | `server/mcp.py` | 6 tools via `PlannerCriticMCPServer` | Tool dispatch |

## Architecture

```
   (user code) ──► adapter ──► Engine.plan(goal)
                                   │
                              ┌────┴────┐
                              │ approved │ escalated
                              └────┬────┘
                                   │
                              adapter gates execution
                                   │
                              ┌────┴────┐
                              │  pass   │ stale
                              └────┬────┘
                                   │ replan
                              re-gate.check_preconditions()
```

### Gate-not-execute boundary (DD-11)

Every adapter:
1. Calls `Engine.plan(goal)` — produces an `ApprovedPlan` or escalation.
2. Caches the approved plan (so re-gate checks are cheap).
3. Before each step/tool call, calls the re-gate (`check_preconditions`) to verify preconditions still hold.
4. If re-gate passes, lets the framework execute the step.
5. If re-gate fails, triggers a replan per the goal's `replan_policy`.
6. Records every decision in the shared `AuditTrail`.

The adapter **never** runs the plan itself — it serializes the approved plan for the framework's own executor.

### Audit trail

All adapters share `adapters/_audit.py`:

```python
@dataclass
class AuditEvent:
    adapter: str       # "raw" | "langgraph" | etc.
    event: str         # "plan_requested" | "plan_approved" | "re_gate_check" | "replan"
    plan_id: str | None
    details: dict

class AuditTrail:
    def record(self, event: AuditEvent): ...
    def get_events(self) -> list[AuditEvent]: ...
```

Every adapter integration test asserts the audit trail contains the expected events.

## Key decisions

### Adapters are thin, hermetic, and framework-agnostic

Each adapter is a single file with no framework dependency beyond what the user installs. Tests use fake roles (no LLM, no network). The adapter imports the framework types only when the user calls the adapter — import-time safety is the user's responsibility.

### Re-gate is advisory, not mandatory

The re-gate (`ReGateConfig.mode`) defaults to `off`. Users opt into pre-execution precondition checking by setting `mode="before-each-step"`. This keeps the default path cheap and simple.

### MCP server is transport-agnostic

`PlannerCriticMCPServer` provides `handle_tool(name, args)` and `list_tools()` — it doesn't depend on any MCP SDK. The `create_server()` factory can wrap it in FastMCP, stdio, or any transport. Six tools: `plan`, `critique`, `explain`, `escalate_list`, `escalate_approve`, `escalate_deny`.

## Out of scope (M5)

- Framework integration tests that actually run a model (deferred to M9 field test)
- Adapter-specific logging beyond the audit trail
- Automatic adapter discovery / plugin loading