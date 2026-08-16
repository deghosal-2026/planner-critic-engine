# D13 — Design Decision Log

> **Authored in:** M1 (Core Engine) · **Status:** Active · **WBS:** D13 · **Refs:** [PRD 05 §2.4 design-decision log](../../design/prd/05-features.md)

Log every design decision with status (Accepted / Proposed / Rejected), context, drivers, the alternate considered, the outcome, and consequences. New entries are appended; statuses change in place.

## M1 Entries

### DD-01 — The core engine is fully model- and framework-agnostic

- **Status:** Accepted
- **Context:** The system must serve raw Python, LangGraph, PydanticAI, CrewAI, OpenAI Agents SDK, and MCP (the tooltrust six), and be testable without any model provider.
- **Drivers:** testability (hermetic CI, no paid LLM); portability across 6 adapter surfaces; the core justifies its existence by owning mechanics, not brands.
- **Alternative considered:** Build the core inside one framework (e.g. only PydanticAI). Rejected: an engine married to one adaptation layer can only ever serve that layer.
- **Outcome:** `roles.py` defines `PlannerRole` / `CriticRole` protocols with plain typed JSON I/O. The core (`schema`, `gates`, `loop`) imports **no** LLM SDK, no framework adapter, no store. M1 ships no provider or adapter at all.
- **Consequences:** Providers/adapters are strictly opt-in M2 modules; the hermetic test suite runs green with fully scripted roles.

### DD-02 — Fail-closed determinism before any model spend

- **Status:** Accepted
- **Context:** §2.6 requires deterministic checks to precede the LLM critic so free, injection-immune checks resolve as much as possible before spend; approval must fail closed (a malformed plan is a blocker).
- **Drivers:** cost discipline (don't pay a model to re-find a schema error); injection-immunity (a gate cannot be prompted); fail-closed semantics for a planning engine.
- **Alternative considered:** LLM-first critique with gates as advisory. Rejected: advisory gates reintroduce exactly the blind-spot the project exists to fix.
- **Outcome:** `run_deterministic_gates` runs 8 gates on every revision before the critic; `strict` tolerance defers on any warning, `balanced` on any blocker. Malformed critic output is dropped and logged, never trusted.
- **Consequences:** Every M1 acceptance scenario is deterministic and fully scripted; the LLM critic is a drop-in, not a dependency of the core's correctness.

### DD-03 — Immutable, versioned, parent-linked plans + allocation-stable findings

- **Status:** Accepted
- **Context:** Revisions must be diffable for forensics and loop convergence must be computable deterministically; findings that panic/regress must be comparable across revisions.
- **Drivers:** replay must show *which critique drove which change* (parent chain); regression guard needs stable identity `(reason_code, task_id)`; `strict/frozen` models guarantee an approved plan is a stable value.
- **Alternative considered:** Mutable plan objects with in-place fixes. Rejected: mutation destroys the audit trail and makes convergence detection unsound.
- **Outcome:** `PlanVersion` is a frozen Pydantic model; new revisions get `id`, incremented `version`, and `parent_version`. Task allocations are stable — `findings` carry `task_id` — so `regression_detected` and `circling_blockers` compare the same identity space across revisions.
- **Consequences:** The plan is a first-class versioned artifact per PRD; M2 diff-aware critique will emit changed-task unions into the critique context on the same identity space.