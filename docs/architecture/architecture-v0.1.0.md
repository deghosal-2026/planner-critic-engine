# D1 — Architecture v0.1.0

> **Authored in:** M1 (Core Engine) — finalized in M10 · **WBS:** D1 ·
> **Refs:** [PRD §2.3 component diagram](../design/prd/02-architecture.md#23-component-diagram), §2.4 LLM provider, §2.5 critique engine

This is the high-level architecture: the §2.3 component diagram with each milestone's
built surface marked, and the module map for the currently shipped package. It was written
during M1 and finalized in M10 as the remaining subsystems landed.

## 1. Component diagram — M1 scope annotated

Reproduces [PRD §2.3](../design/prd/02-architecture.md#23-component-diagram) with each
component tagged **M1 · built**, **M2–M9 · later**, or **M10 · finalize**:

```
                      ┌─────────────────────────────────────────────┐
   Goal ─────────────►│            CORE ENGINE (agnostic)            │
   constraints        │                                             │
   risk_tolerance     │  ┌──────────┐    ┌────────────────────────┐ │
   budget             │  │ Planner  │◄──►│ Loop Controller         │ │ M1 · built
                      │  │ (LLM)    │    │  revise/approve/escalate│ │  (role protocol)
   ┌──────────────┐   │  └────┬─────┘    └────┬───────────────────┘ │
   │ LLM PROVIDER │   │       │draft         │revise/approve/escalate│
   │  LAYER       │   │       ▼              │                      │
   │  - registry  │   │  ┌──────────────┐    │                      │
   │  - transport │ -- │  │ Critic      │◄───┘                      │
   │  (OpenAI-    │   │  │ (det + LLM)  │                          │
   │   compatible)│   │  └────┬─────────┘                          │
   └──────┬───────┘   │       │ findings                            │
          │  M2       │       ▼                                     │
          ▼           │  ┌────────────────┐   ┌──────────────────┐  │
   (planner + critic  │  │ Escalation     │   │ Plan Store       │  │
    use configured    │  │ Manager        │   │ (SQLite/Postgres)│  │
    providers/models) │  └───────┬────────┘   └────────┬─────────┘  │
                      └──────────┼─────────────────────┼────────────┘
                                 │                     │  M2
                      approved plan│           re-gate + trace       │
                      ┌─────────────────┐
                      │ FRAMEWORK       │  raw Python / LangGraph /
                      │ ADAPTERS (6)    │  PydanticAI / CrewAI /
                      └─────────────────┘  OpenAI SDK / MCP   M3
              ┌──────────────────────────────────────────────────┐
              ▼                                                   │
        CLI · MCP server · HTTP service · (web UI v0.2)     M5/M6 │
```

Legend:

| Component | M1 state |
|-----------|----------|
| **Goal / constraints / budget** | Built — `Goal` schema with `constraints.budget` (M1 stubs; M3 enforces fully) |
| **Loop Controller** | Built — revise/approve/escalate; cap/convergence/regression; budget stub; TTL |
| **Critic (deterministic gates)** | Built — the six §2.5.2 gates as code + `parallel_safety` |
| **Critic (LLM)** | Not built — the `CriticRole` protocol seam exists; a real model critic is M2+ |
| **Planner (LLM)** | Not built — `PlannerRole` protocol seam exists; model-backed planner is M2+ |
| **Approval threshold** | Built — `severity threshold` resolves strict/balanced per findings |
| **Escalation Manager** | Loop-side escalation in code — standalone manager/UI is **M2** |
| **Plan Store** | Not built — M2 |
| **LLM Provider Layer** | Not built — M2; core owns protocol seams only |
| **Framework Adapters** | Not built — M5 |
| **CLI / MCP / HTTP / UI** | CLI `plancritic --version` placeholder (M1); full CLI is M6 |

## Module map (shipped surface, src/planner_critic)

| Module | Role |
|--------|------|
| `engine.py` | `Engine` facade — binds roles + config, `plan(goal)` |
| `roles.py` | `PlannerRole.decompose` / `CriticRole.audit` protocol seams |
| `schema/` | `goal.py` (`Goal`), `plan.py` (`PlanVersion`/`Task`/`Branch`/`Dependency`/`VerificationStep`/`RollbackStep`) |
| `gates/` | deterministic gates (M1): `schema_valid`, `dep_cycles`, `ordering`, `parallel_safety`, `verification`, `rollback`, `preconditions` + `base.py` |
| `loop/` | controller (`_controller.py`) + `convergence`, `regression`, `budget`, `ttl` |
| `approval.py` | `ApprovedPlan` wrapper + strict/balanced threshold |
| `types.py` | `Finding`, `Escalation`, `ExecutionTrace`, `PlanComplexity`, `ApprovedPlan`, `PlanningError` |
| `reason_codes.py` | F-77 stable reason-code catalog |
| `_cli.py` | M1 `plancritic --version` placeholder; full CLI is M6 |

## M10 finalization checklist

- [ ] Fold in the M2 provider layer + registry
- [ ] Fold in the M2 plan store + versioning
- [ ] Fold in the M3 diff-critique + escalation UI
- [ ] Finalize component diagram with real transport/approvals
- [ ] Promote to spec — this doc is replaceable by `spec-v0.1.0.md` convergence