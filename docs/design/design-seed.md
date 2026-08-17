# M1 Design Seed

> **Authored in:** M1 (Core Engine) · **Status:** Current baseline · **Refs:** [PRD 05 §2.6 verify-shrink loop](../design/prd/05-features.md), [Architecture v0.1.0 (D1)](../architecture/architecture-v0.1.0.md)

## What M1 Built

M1 delivered the **core engine**: the typed schema, deterministic critique gates, the revise-until-approved loop controller, the approval threshold, and the public `Engine` facade — all model- and framework-agnostic (no LLM transport, no store, no adapters shipped in M1).

## Product Vision (unchanged instrument)

> **PlannerCritic Engine — Hierarchical task planning with an independent LLM critic.**
> A planner decomposes a goal into a typed plan; a critic audits every subtask;
> the loop revises until approved or escalates to a human with one precise question.
> Planning is the weakest part of agent systems — single-pass planning is blind;
> a model reviewing its own plan is agreement with extra steps (64.5% blind-spot rate).
> The critic is a separate model so a plan survives an independent adversarial pass
> before anything executes.

## Tenets

1. **Plan as a first-class, versioned artifact.** Typed schema, every revision immutable, parent-linked, diffable. The loop never mutates a plan — it produces the next version.
2. **Deterministic first.** Free, injection-immune gates (schema, ordering, dep-cycles, parallel-safety, verification, rollback, preconditions) run before any model cost. The LLM critic only sees what the gates could not resolve.
3. **Fail closed.** `strict` risk tolerance means zero warnings; `balanced` means warnings are acknowledged. A malformed plan is a blocker, not a note.
4. **Bounded spend.** Every loop respects a revision cap and, when set, token/call/plan budgets. Escalation is the exit hatch, not an error.
5. **Criticism, not generation.** The critic audits; it cannot edit. Guardrails reject malformed findings instead of silently proceeding.
6. **Model- and framework-agnostic.** The core speaks plain typed JSON through protocol seams; providers/adapters bolt on and are never imported by the core.
7. **Human escalation with a sharp question.** On convergence, regression, budget, or cap, the loop escalates with the blockers listed and a concrete question — never a wall of raw findings.

## M1 Scope Carved Out (for later milestones)

| Not in M1 | Rationale |
|---|---|
| LLM provider registry + OpenAI-compatible transport | M2; core only owns protocol seams |
| Plan store (SQLite/Postgres) + versioning/migration | M2 |
| Framework adapters (PydanticAI, LangGraph, CrewAI, toolsix) | M2+ |
| Deterministic complexity/cost estimate pre-approval | M2 |
| Diff-aware critique on revisions N>1 | deterministic gates are revision-stable; diff-critique is M2 |
| Escalation UI (AIDE-style), HTTP/MCP servers | M2 |
| Demo corpus + `plancritic-demo` runner, field tests | M3 |
| OTel export, LessonExtractor, forensics tagging | M3 |

## M1 Exit Criteria — Met

- [x] `plancritic` CLI reports version; package imports safely (`planner_critic`)
- [x] Goal → PlanVersion schema with strict validation + immutability
- [x] 8 deterministic gates run under `run_deterministic_gates`
- [x] Loop controller: approve / escalate / capped, with convergence + regression guards
- [x] Approval threshold (strict/balanced) resolved per findings
- [x] `Engine` facade wraps the loop end-to-end
- [x] Tests: 84 passing, 95.21% coverage (≥ 95% required), ruff + strict mypy clean
- [x] Acceptance matrix (lo): 13 scenarios green incl. regression_thrashing

## M2 Exit Criteria — Met

- [x] `PlanStore` protocol (in-memory + SQLite) with structural `diff`
- [x] Schema versioning + reversible migrations (`migrate` up/down), old data readable
- [x] `LLMProvider` protocol + structured-output envelope + fail-closed error types
- [x] Config-driven registry (TOML) + `plancritic providers add/list/rm`, distinct planner/critic roles
- [x] OpenAI-compatible transport with `base_url` override, zero paid LLM in CI
- [x] Structured-output enforcer with bounded retries then `planning_unavailable`
- [x] `EnvProbe` read-only built-ins (`env_var`, `http_check` real; `db_query`, `deploy_status` stubs)
- [x] Tests: 178 passing, 97.98% coverage (≥ 95% required), ruff + strict mypy clean

## Open Questions for M3

1. Diff-aware critique — how do we represent "what changed" to the critic without leaking the planner's prompt? (Candidate: emit the union of `id`s of new/changed tasks into the critique context.)
2. Complexity estimate — deterministic proxy (task count × fan-out × blast radius) before M3's real heuristic cost model lands.
3. Deterministic-first mode — should gate findings be *merged* into the critic's findings or kept separate for audit? (M1 merges; revisit in M3 with diff-critique.)