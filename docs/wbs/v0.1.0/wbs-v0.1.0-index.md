# WBS — PlannerCritic Engine v0.1.0 (Index)

> The work breakdown for the **feature-rich first release** (see [PRD 09 — Roadmap](../../design/prd/09-roadmap.md)). Ten milestones (M1–M10) across seven part files. **Author:** Debashish Ghosal · **Date:** 2026-08-16 · **Status:** In Progress — M1 + M2 + M3 **COMPLETE** (merged), M4 next
>
> PRDs: [01-why](../../design/prd/01-why.md) · [02-architecture](../../design/prd/02-architecture.md) · [04-users-and-cujs](../../design/prd/04-users-and-cujs.md) · [05-features](../../design/prd/05-features.md) · [06-security](../../design/prd/06-security-baseline.md) · [07-success-metrics](../../design/prd/07-success-metrics.md) · [08-risks](../../design/prd/08-risks.md)

---

## 1. Milestone Overview

| M# | Name | Core features | CUJs | Issues | Part file | Status |
|----|------|---------------|------|--------|-----------|--------|
| **M1** | **Core Engine — schemas, gates, loop** | F-01, F-02, F-12, F-05, F-06, F-07, F-08, F-73, F-74, F-15(F-77) | CUJ 4 | [#1–#10](https://github.com/deghosal-2026/planner-critic-engine/issues/1) | [part1](wbs-v0.1.0-part1-engine-core.md) | **DONE** (commit `c1473bb`) |
| M2 | Plan Store + LLM Provider Layer | F-09, F-63, F-27, F-20, F-21, F-22, F-23, F-24, F-19, F-26 | CUJ 1, CUJ 6 | [#11–#19](https://github.com/deghosal-2026/planner-critic-engine/issues/11) | [part1](wbs-v0.1.0-part1-engine-core.md) | **DONE** (commit `a4cfe38`) |
| M3 | Critique Engine + Loop Semantics | F-04, F-10, F-11, F-13, F-14, F-17, F-18, F-78 | CUJ 2, CUJ 3, CUJ 13 | [#20–#29](https://github.com/deghosal-2026/planner-critic-engine/issues/20) | [part2](wbs-v0.1.0-part2-critique-escalation.md) | **DONE** (commit `bc1156a`) |
| **M4** | **Escalation + Forensics + Replan + Viz** | F-30, F-31, F-32, F-34, F-50, F-51, F-52, F-16, F-53, F-75, F-76 | CUJ 5, CUJ 7, CUJ 9, CUJ 10 | [#30–#39](https://github.com/deghosal-2026/planner-critic-engine/issues/30) | [part2](wbs-v0.1.0-part2-critique-escalation.md) | **DONE** (commit `e0495df`) |
| M5 | Framework Adapters (tooltrust six) + re-gate | F-40..F-45, F-46 | CUJ 8 | [#40–#47](https://github.com/deghosal-2026/planner-critic-engine/issues/40) | [part3](wbs-v0.1.0-part3-adapters-surfaces.md) |
| M6 | CLI + HTTP Service + Explain + Init | F-61, F-62, F-80, F-85 | CUJ 1, CUJ 15 | [#48–#54](https://github.com/deghosal-2026/planner-critic-engine/issues/48) | [part3](wbs-v0.1.0-part3-adapters-surfaces.md) |
| M7 | Demo Corpus + Demo Runner | F-65, F-66, F-86 | CUJ 14 | [#55–#58](https://github.com/deghosal-2026/planner-critic-engine/issues/55) | [part4](wbs-v0.1.0-part4-demo.md) |
| M8 | Docker Integration Tests — containerized engine + surfaces vs local LLM | F-60, F-61, F-62, F-45, F-67 | CUJ 1, CUJ 15 | [#77–#84](https://github.com/deghosal-2026/planner-critic-engine/issues/77) | [part5](wbs-v0.1.0-part5-docker-integration.md) |
| M9 | Field Test — hermetic CI + local-model sweep | F-67, F-68 | CUJ 11 | [#59–#64](https://github.com/deghosal-2026/planner-critic-engine/issues/59) | [part6](wbs-v0.1.0-part6-field-test.md) |
| M10 | Pre-Release + Release + Security + Docs | F-60, OWASP 6/10, OpenSSF Passing, Essential | all P0 | [#65–#71](https://github.com/deghosal-2026/planner-critic-engine/issues/65) | [part7](wbs-v0.1.0-part7-prerelease-release.md) |

**Deferred to v0.2.0 (P1):** web UI (F-33), Postgres store (F-64), Anthropic/Gemini transports (F-25), multi-critic (F-37), plan templates (F-87), export F-47/F-81, OTel (F-82), heuristic packs (F-79), property-based fuzzing. See [PRD 09 §9.2](../../design/prd/09-roadmap.md#92-v020-p1).

## 2. Dependency Graph

```
M1 (Core Engine)
  │  Goal/Plan schemas, deterministic gates, loop controller
  ▼
M2 (Store + Provider layer)
  │  SQLite store, provider registry, OpenAI-compat transport, EnvProbe
  ▼
M3 (Critique + Loop semantics)
  │  six-heuristic critic, dual mode, diff-aware, budget, complexity, shadow
  ▼
M4 (Escalation + Forensics + Replan + Viz)
  │  escalation manager, plan-exec link, replan semantics, graph/replay
  ├──────────────┬──────────────┐
  ▼              ▼              ▼
M5 (Adapters)   M6 (CLI+HTTP)   ── M5 and M6 parallel after M4
  │              │
  ├──────────────┤
  ▼              ▼
M7 (Demo corpus + runner)   ← needs M5 (adapters) + M6 (CLI)
  │
  ▼
M8 (Docker integration)   ← needs M5 (MCP) + M6 (CLI+HTTP) + M7 (corpus)
  │  containerized engine + surfaces vs a real local LLM
  ▼
M9 (Field test)   ← needs M7 (corpus) + M5 (adapters) + M8 (container gate)
  │
  ▼
M10 (Pre-release + release)   ← needs all preceding
```

**Hard ordering:** M1 → M2 → M3 → M4 → M7 → M8 → M9 → M10. **Parallel:** M5 and M6 (both consume M4; M7 needs both). M8 cannot start before M7 passes its gate; M9 (field test) cannot start before M8 (docker integration) passes its gate.

**Sequencing rationale** (per [PRD 08 — risks](../../design/prd/08-risks.md)): the v0.1.0 scope is large, so the WBS is sequenced *engine-first* — the core engine (M1–M3) is fully testable with fake providers before any breadth (adapters/surfaces) lands. Hermetic everything: zero paid LLM in CI.

## 3. GitHub Issue Ranges

> **Status: IN PROGRESS** — all issues are attached to the [**0.1.0 release**](https://github.com/deghosal-2026/planner-critic-engine/milestone/1) milestone. Each task row in the part files has a live issue link + checkbox — flip the checkbox when the issue is closed; milestone progress is visible in the GitHub milestone view. **Closed so far: M1 #1–10 (commit `c1473bb`), M2 #11–19 (commit `a4cfe38`), M3 #20–29 (commit `bc1156a`), M4 #30–39 (commit `e0495df`). Open: M5–M7 #40–58, Docker M8 #77–84, Field M9 #59–64 + #74–76, Release M10 #65–71.**

| Milestone | Issue range | API scope |
|-----------|-------------|-----------|
| M1 Core Engine | [#1–#10](https://github.com/deghosal-2026/planner-critic-engine/issues/1) | schemas, gates, loop |
| M2 Store + Provider | [#11–#19](https://github.com/deghosal-2026/planner-critic-engine/issues/11) | store, registry, transport, EnvProbe |
| M3 Critique + Loop | [#20–#29](https://github.com/deghosal-2026/planner-critic-engine/issues/20) | six-heuristic critic, dual mode, budget, shadow, TTL |
| M4 Escalation/Forensics/Replan | [#30–#39](https://github.com/deghosal-2026/planner-critic-engine/issues/30) | escalation, forensics, replan, viz |
| M5 Adapters + MCP | [#40–#47](https://github.com/deghosal-2026/planner-critic-engine/issues/40) | raw/LangGraph/PydanticAI/CrewAI/OpenAI/MCP, re-gate (next)
| M6 CLI + HTTP | [#48–#54](https://github.com/deghosal-2026/planner-critic-engine/issues/48) | CLI, HTTP, explain, init |
| M7 Demo | [#55–#58](https://github.com/deghosal-2026/planner-critic-engine/issues/55) | corpus, demo runner |
| M8 Docker Integration | [#77–#84](https://github.com/deghosal-2026/planner-critic-engine/issues/77) | Dockerfile, compose, CLI/HTTP/MCP vs local LLM, CI |
| M9 Field Test | [#59–#64](https://github.com/deghosal-2026/planner-critic-engine/issues/59) + [#74–#76](https://github.com/deghosal-2026/planner-critic-engine/issues/74) | hermetic gate, sweep, report, critique-mode sweep |
| M10 Pre-Release + Release | [#65–#71](https://github.com/deghosal-2026/planner-critic-engine/issues/65) | security, docs, packaging, ship |

## 4. Canonical Package Layout

The WBS task lists reference the following module paths. The layout mirrors the tooltrust structure: flat inside the package with sub-packages for related modules.

```
planner_critic/
  __init__.py                  # exports Engine, types, version
  types.py                     # Finding, Escalation, ExecutionTrace, PlanComplexity, ApprovedPlan, PlanningError
  reason_codes.py              # stable reason-code catalog (F-77)
  schema/
    goal.py                    # Goal model (F-01)
    plan.py                    # PlanVersion, Task, Branch, Dependency, VerificationStep, RollbackStep (F-02, F-15)
  roles.py                     # PlannerRole, CriticRole protocols (F-03, F-04 abstract)
  gates/
    __init__.py                # run_deterministic_gates(plan) -> list[Finding]
    schema_valid.py            # parses against typed schema
    dep_cycles.py              # DAG check
    ordering.py                # dependency-ordering sanity
    verification.py            # high-risk steps carry verification
    rollback.py                # high-risk steps carry rollback
    preconditions.py           # preconditions reference established facts
    parallel_safety.py         # unsafe parallelization (F-15)
  loop.py                      # run_loop() — revision cap, convergence, regression, budget, thresholds (F-05-08, F-13)
  loop/
    convergence.py             # convergence detection
    regression.py              # regression guard
    budget.py                  # spend-budget enforcement
    ttl.py                     # approval expiry (F-18)
  approval.py                  # ApprovedPlan wrapper, threshold resolver (F-08, F-73)
  estimate.py                  # PlanComplexity — deterministic step/branch/irreversible/cost estimate (F-17)
  shadow.py                    # dry_run path, mode:shadow recording (F-14)
  store/
    base.py                    # PlanStore protocol (F-09)
    sqlite.py                  # SQLite implementation (F-63)
    versions.py                # plan_schema_version + migrate (F-27)
    replan_trace.py            # sub-plan linkage for replans (F-53)
  llm/
    base.py                    # LLMProvider protocol (F-20)
    registry.py                # config-driven registry, role->provider mapping (F-21, F-23)
    transport_openai.py        # OpenAI-compatible transport (F-22)
    structured.py              # structured-output enforcement + retries (F-24)
  probe/
    base.py                    # EnvProbe protocol (F-19)
    env_var.py                 # env-var probe
    http_check.py              # HTTP-check probe
    db_query.py                # DB-query probe (stub)
    deploy_status.py           # deploy-status probe (stub)
  critique/
    critic.py                  # six-heuristic LLM critic (F-04)
    mode.py                    # deterministic-first | llm-every-revision (F-10, F-11)
    diff.py                    # diff-aware re-audit scope (F-78)
  escalation.py                # escalation manager + resolution (F-30, F-34)
  execution.py                 # plan-execution link + failure tagging (F-50, F-51, F-52)
  replan.py                    # patch/restart/abort policies (F-16)
  regate.py                    # execution-time re-gate (F-46)
  explain.py                   # loop-decision explain (F-80)
  adapters/
    python.py                  # raw Python (F-40)
    langgraph.py               # LangGraph (F-41)
    pydantic_ai.py             # PydanticAI (F-42)
    crewai.py                  # CrewAI (F-43)
    openai_agents.py           # OpenAI Agents SDK (F-44)
  server/
    mcp.py                     # MCP server + tools (F-45)
    http.py                    # FastAPI HTTP service (F-62)
  cli/
    __init__.py                # CLI entrypoint (Click/Typer)
    init.py                    # scaffold config + provider + example goal (F-85)
    plan.py                    # plan command + --dry-run
    critique.py                # critique command
    providers.py               # add/list/rm
    plans.py                   # list/show/diff --graph
    escalate.py                # list/approve/deny --patch
    replay.py                  # replay --step --format
    migrate.py                 # schema migration
    field_test.py              # field-test driver
  viz/
    graph.py                   # Mermaid + JSON DAG export (F-75)
    replay.py                  # trace walker (F-76)

tests/
  test_types.py, test_schema.py, test_gates.py, test_loop.py, test_store.py,
  test_llm.py, test_probe.py, test_critique.py, test_escalation.py,
  test_execution.py, test_replan.py, test_rogate.py, test_explain.py,
  test_adapters/, test_server/, test_cli/, test_viz/,
  fixtures/ (loop_matrix.yaml, seeded_goals/, adversarial_goal.yaml)
```

## 5. Design Documents to Author

We currently have zero design docs (the PRD is a requirements document, not an architecture/design spec). As each milestone builds the relevant subsystem, the implementer writes the design doc that captures the actual built behavior, the decisions made, and the rationale. All design docs go into `docs/design/` (or `docs/architecture/` for architecture/DB); the master list:

| # | Doc | Path | Authored in | Contents |
|---|-----|------|-------------|----------|
| D1 | Architecture v0.1.0 | `docs/architecture/architecture-v0.1.0.md` | M1 (seed) → M10 (finalize) | Component diagram, module map, data flow |
| D2 | Plan schema design | `docs/design/plan-schema-design.md` | M1 | Every typed field in Goal/PlanVersion/Task/Branch/Dependency, validation rules, serialization |
| D3 | Loop controller design | `docs/design/loop-controller-design.md` | M1 | Loop algorithm, termination semantics, determinism contract, convergence + regression logic |
| D4 | DB schema sketch | `docs/architecture/db-schema-sketch.md` | M2 | SQLite DDL, tables/columns/indices, migration versioning |
| D5 | Provider layer design | `docs/design/provider-layer-design.md` | M2 | Registry-first rationale, config format, transport contract, EnvProbe protocol |
| D6 | Critique engine design | `docs/design/critique-engine-design.md` | M3 | Six heuristic families per §2.5.1, dual-mode gate, diff-aware scope, budget enforcement |
| D7 | Escalation design | `docs/design/escalation-design.md` | M4 | Escalation manager, question-precision contract, resolution flow, patching |
| D8 | Replan + re-gate design | `docs/design/replan-regate-design.md` | M4 | patch/restart/abort policies, re-gate mechanics, EnvProbe interaction, lineage |
| D9 | Adapter design | `docs/design/adapters-design.md` | M5 | Six-adapters pattern, re-gate wiring per framework, audit-train interface |
| D10 | Explain engine design | `docs/design/explain-engine-design.md` | M6 | Reason-code → narrative mapping, template structure, actionability standard |
| D11 | Demo scenario | `docs/design/demo-scenario.md` | M7 | Walkthrough of `plannercritic-demo`, seeded drift, replan visible |
| D12 | Field test design | `docs/design/field-test-design.md` | M9 | Matrix design, hermetic-gate architecture, field-sweep harness |
| D13 | Design decisions | `docs/design/design-decisions.md` | M1–M10 | DD-01..N decision records (naming, contracts, defaults, deferrals) |
| D14 | API reference | `docs/reference/api.md` | M6 | CLI cheat-sheet, HTTP endpoints, MCP tools |
| D15 | Quickstart | `docs/reference/quickstart.md` | M10 | `pip install` → `init` → first approved plan |
| D16 | Release notes v0.1.0 | `docs/reference/release-notes-v0.1.0.md` | M10 | Changelog, breaking changes, upgrade path |
| D17 | Security posture | `SECURITY.md` + OWASP table | M10 | OWASP 6/10 mapping, Essential checklist |
| D18 | Contributing | `CONTRIBUTING.md` | M10 | tests/coverage/mypy gate, commit conventions |
| D19 | Docker integration test design | `docs/design/docker-integration-design.md` | M8 | Image layout, compose topology, local-LLM wiring, CI strategy, three modes under containers |

## 6. Standard Milestone Exit Gate

**Every milestone** closes with the same gate. The per-milestone part files may add extra checks but these four are non-negotiable:

- [ ] **Code review passed** — every `.py` file in the milestone reviewed; findings resolved
- [ ] **Test coverage > 95%** — `pytest --cov=planner_critic --cov-fail-under=95`
- [ ] **Lint clean** — `ruff check .` 0 errors AND `mypy --strict` 0 errors
- [ ] **Comments + docstrings in all code** — every `.py` file: module docstring, function/method docstrings (Args/Returns/Raises for public API), inline comments on non-obvious logic

Milestone-specific exit conditions (whether bit-gating contribute tests, demo-runner runs, etc.) are listed in each part file.

## 7. Cross-Cutting Contracts

- **Package:** import `planner_critic` — PyPI `planner-critic` — CLI `plancritic`.
- **Determinism (F-74):** loop controller deterministic on identical inputs (CI-asserted). LLM outputs are advisory; structured output is re-validated.
- **Fail-closed (F-73):** an unapproved plan can never reach an executor. Provider failure → distinct `planning_unavailable` per role.
- **Cheap by default:** deterministic gates are free; default config uses local/cheap endpoints (OMLX/Ollama/vLLM). CI never calls a paid LLM.
- **Injection-safety:** a deterministic-gate blocker can never be overridden by the LLM critic.
- **Plan store side-channel:** store failure → warn + continue in-memory; persisted when healthy.
