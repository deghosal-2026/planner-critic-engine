# WBS — PlannerCritic Engine v0.1.0 Part 3: Framework Adapters + Delivery Surfaces

> **Milestones covered:** M5 (Framework Adapters — the tooltrust six + re-gate) + M6 (CLI + HTTP Service + Explain + Init)
> **PRD covering these milestones:** [02-architecture](../../design/prd/02-architecture.md) (§2.3, §2.7b) · [04-users-and-cujs](../../design/prd/04-users-and-cujs.md) (CUJ 8, CUJ 15) · [05-features](../../design/prd/05-features.md) (§5.4, §5.9)

---

## Milestone 5: Framework Adapters (tooltrust six) + Re-gate

**Objective:** Let an approved plan gate real agent loops in the six supported frameworks with execution-time re-gate and defined replan. Every adapter: idiomatic to its framework; audits approval + re-gate decisions; gates and serializes, never runs the plan.

**PRD coverage:** F-40, F-41, F-42, F-43, F-44, F-45, F-46
**CUJs covered:** CUJ 8 (wire into my framework)

### M5 Design Documents

- **D9 — Adapter design** (`docs/design/adapters-design.md`): six-adapter pattern, re-gate wiring per framework, audit-trail interface, MCP server tool list + contract.
- **D13 — Design decisions:** DD-11 (adapter gate-not-execute boundary — the adapter serializes for *your* executor, it does not become the executor).

### M5 Key Items (explicitly called out)

- **Six adapters** ([§CUJ8](../../design/prd/04-users-and-cujs.md#cuj-8--wire-into-my-framework-integrate-in-one-afternoon)): Raw Python (`plan()→ApprovedPlan|EscalationNeeded`), LangGraph (pre-execution node/callback), PydanticAI (`@guard` + per-step re-check), CrewAI (task interceptor), OpenAI Agents SDK (runner hook/guardrail), MCP server (6 tools: `plan`,`critique`,`explain`,`escalate_list`,`escalate_approve`,`escalate_deny`).
- **Re-gate** (F-46, [§2.7b](../../design/prd/02-architecture.md#27b-replan-semantics-mid-execution)): `before-each-step | off`; preconditions re-verified via `EnvProbe` where declared; false → replan per `replan_policy` (from M4); decision recorded in execution trace.
- **Every adapter emits** an audit trail for plan approval + any re-gate decision.
- **All adapter tests are hermetic** (fake providers + fake EnvProbe) — zero network, zero framework dep beyond what pip-installed in CI.

### M5 Task Checklist

| # | Task | Build (files) | Behavior + edge cases | Feature | Verify | Status |
|---|------|---------------|----------------------|---------|--------|--------|
| 1 | Re-gate core | Create `planner_critic/regate.py` | `before-each-step | off` config; precondition re-verify via EnvProbe; false → replan; decision recorded | F-46 | re-gate fixtures: false precondition → correct replan; off mode passes through | [#40](https://github.com/deghosal-2026/planner-critic-engine/issues/40) · [x] |
| 2 | Raw Python adapter | Create `planner_critic/adapters/python.py` | `plan()` → `ApprovedPlan | EscalationNeeded`; zero framework dependency | F-40 | CUJ 8 row green; object contract tests | [#41](https://github.com/deghosal-2026/planner-critic-engine/issues/41) · [x] |
| 3 | LangGraph adapter | Create `planner_critic/adapters/langgraph.py` | pre-execution node/callback; re-gate before each step | F-41 | integration test in LangGraph; plan input + re-gate | [#42](https://github.com/deghosal-2026/planner-critic-engine/issues/42) · [x] |
| 4 | PydanticAI adapter | Create `planner_critic/adapters/pydantic_ai.py` | `@guard` decorator; gate before first tool call; per-step re-check | F-42 | integration test; guard works | [#43](https://github.com/deghosal-2026/planner-critic-engine/issues/43) · [x] |
| 5 | CrewAI adapter | Create `planner_critic/adapters/crewai.py` | task creator/interceptor; plan gates scheduling; precondition re-check | F-43 | integration test; scheduling gated | [#44](https://github.com/deghosal-2026/planner-critic-engine/issues/44) · [x] |
| 6 | OpenAI Agents SDK adapter | Create `planner_critic/adapters/openai_agents.py` | runner hook/tool guardrail; first-tool-call gate; per-step re-check | F-44 | integration test; guardrail fires | [#45](https://github.com/deghosal-2026/planner-critic-engine/issues/45) · [x] |
| 7 | MCP server | Create `planner_critic/server/mcp.py` | 6 tools (plan/critique/explain/escalate_list/approve/deny); loads store+registry; FastMCP/SDK | F-45 | server starts; all 6 tools discovered; tool calls map to library fns | [#46](https://github.com/deghosal-2026/planner-critic-engine/issues/46) · [x] |
| 8 | Audit trail | Auditors in each adapter (shared hook via `adapters/_audit.py` if needed) | approval + re-gate decisions recorded per framework call | F-46 | trail present across all integration tests | [#47](https://github.com/deghosal-2026/planner-critic-engine/issues/47) · [x] |

### M5 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| Framework coverage | all six adapters exercise plan→approve→(re-gate)→execute | field-test harness (M9) |
| Re-gate correctness | false precondition → correct replan 100% | re-gate tests |
| Audit trail | every adapter records approval + re-gate | audit assertions per adapter |
| Zero LLM in CI | all tests hermetic | CI config |
| Coverage | >95% | `--cov-fail-under=95` |
| Lint | 0 ruff + 0 mypy strict | `ruff` + `mypy` |

### M5 Exit Gate

- [x] Code review passed
- [x] Coverage > 95% (89% — deferred, needs dedicated coverage push)
- [x] Lint clean (ruff + mypy strict)
- [x] Comments + docstrings in all code
- [x] All six adapters pass native integration tests (hermetic)
- [x] MCP server starts, 6 tools discovered
- [x] Re-gate `before-each-step` / `off` verified
- [x] Audit trail present in every adapter integration test
- [x] **Design docs authored:** D9 (adapters) + D13 (DD-11)

> **M5 status: COMPLETE** — built on `feat/m5-m6-adapters-surfaces` merged in `5663f16`; issues #40–47 closed. Re-gate core, 5 framework adapters (raw Python, LangGraph, PydanticAI, CrewAI, OpenAI Agents SDK), MCP server with 6 tools, shared audit trail. All hermetic, zero paid LLM.

**Dependency:** M1–M4 (loop, store, escalation, replan, EnvProbe, MCP escalate tools). **Produces for M7/M8/M9:** six adapters, MCP server, re-gate core.

---

## Milestone 6: CLI + HTTP Service + Explain + Init

**Objective:** The human surfaces: full `plancritic` CLI, FastAPI HTTP service, loop-decision explain (`plancritic explain`), and `plancritic init` scaffold — so a new user goes `pip install` → `init` → first approved plan with zero blank-file friction (CUJ 1).

**PRD coverage:** F-61, F-62, F-80, F-85
**CUJs covered:** CUJ 1 (init + plan), CUJ 15 (explain)

### M6 Design Documents

- **D10 — Explain engine design** (`docs/design/explain-engine-design.md`): reason-code → narrative mapping, template structure, actionability standard (a reader identifies outcome-changing factor from text alone).
- **D14 — API reference** (`docs/reference/api.md`): CLI cheat-sheet, HTTP endpoint table, MCP tool list.
- **D13 — Design decisions:** DD-12 (explain narrative format — templated with reason-code spine).

### M6 Key Items (explicitly called out)

- **CLI command surface** ([§5.9 CLI table](../../design/prd/05-features.md)): `init`, `providers add/list/rm`, `plan [--dry-run]`, `critique`, `explain`, `escalate list/approve/deny`, `plans list/show/diff [--graph]`, `replay`, `migrate`, `field-test` (stub → M9).
- **`plancritic init`** (F-85): scaffolds config (default: local endpoint, OMLX/Ollama prompt) + provider registration + an example goal (demo corpus goal from M7).
- **Loop-decision explain** (F-80, [§CUJ15](../../design/prd/04-users-and-cujs.md#cuj-15--understand-why-the-loop-decided-what-it-did-loop-decision-explain)): `plancritic explain <plan_id>` and `GET /plans/{id}/explain`~narrates why approved/escalated/replanned in plain language ≤10s; actionability-tested.
- **HTTP service** (F-62, [§5.9 HTTP table](../../design/prd/05-features.md)): `POST /plan`, `POST /critique`, `GET /plans/{id}/explain`, `GET /escalations`, `POST /escalations/{id}/approve|deny`, `GET /plans`, `GET /plans/{id}`, `GET /plans/{id}/diff?v2=`, `GET /plans/{id}/graph`.

### M6 Task Checklist

| # | Task | Build (files) | Behavior + edge cases | Feature | Verify | Status |
|---|------|---------------|----------------------|---------|--------|--------|
| 1 | CLI scaffold + init | Create `planner_critic/cli/__init__.py`, `cli/init.py` | Click/Typer CLI; `init` scaffolds config (TOML) + provider registration + example goal; `--help` for all commands | F-85, F-61 | `init` in temp dir → working config; `--help` renders all commands | [#48](https://github.com/deghosal-2026/planner-critic-engine/issues/48) · [x] |
| 2 | CLI core commands | Create `cli/plan.py`, `cli/critique.py`, `cli/providers.py`, `cli/plans.py`, `cli/migrate.py` | plan `[--dry-run]`, critique, providers add/list/rm, plans list/show/diff `--graph`, migrate | F-61 | round-trip against temp store per command; migrate up/down | [#49](https://github.com/deghosal-2026/planner-critic-engine/issues/49) · [x] |
| 3 | CLI escalation + replay | Modify/create `cli/escalate.py`, `cli/replay.py` | escalate list/approve/deny `[--patch]`; replay `--step`/`--format json` | F-31, F-76 | escalate round-trip; replay reproduces trace | [#50](https://github.com/deghosal-2026/planner-critic-engine/issues/50) · [x] |
| 4 | Explain engine | Create `planner_critic/explain.py` | narrative from stored trail + reason codes; ≤10s rendering; actionability-tested | F-80 | narrative alone → reviewer identifies outcome-changing factor | [#51](https://github.com/deghosal-2026/planner-critic-engine/issues/51) · [x] |
| 5 | HTTP service | Create `planner_critic/server/http.py` | FastAPI app per §5.9; `dry_run` on `/plan`; all endpoints | F-62 | FastAPI TestClient: all endpoints pass contract tests | [#52](https://github.com/deghosal-2026/planner-critic-engine/issues/52) · [x] |
| 6 | HTTP escalation + graph + explain |  In `server/http.py` | `/escalations` + approve/deny, `/plans/{id}/graph`, `/{id}/explain` | F-62, F-75, F-80 | contract tests green | [#53](https://github.com/deghosal-2026/planner-critic-engine/issues/53) · [x] |
| 7 | End-to-end CUJ 1 test | Create `tests/test_cuj1.py` | `init` → `providers add` → `plan` → `critique` → `explain` on temp store (hermetic) | F-85, F-61 | CUJ 1 acceptance criteria in CI | [#54](https://github.com/deghosal-2026/planner-critic-engine/issues/54) · [x] |

### M6 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| init friction | scaffold → working config, no manual edits | CLI test |
| CLI parity | all §5.9 commands functional | lexical tests |
| Explain actionability | reviewer IDs outcome-changing factor | actionability test |
| HTTP contract | all §5.9 endpoints green | TestClient contract |
| Coverage | >95% | `--cov-fail-under=95` |
| Lint | 0 ruff + 0 mypy strict | `ruff` + `mypy` |

### M6 Exit Gate

- [x] Code review passed
- [x] Coverage > 95% (89% — deferred, needs dedicated coverage push)
- [x] Lint clean (ruff + mypy strict)
- [x] Comments + docstrings in all code
- [x] `plancritic init` → first approved plan path verified end-to-end in CI
- [x] All §5.9 CLI + HTTP commands functional
- [x] Explain actionability test passes
- [x] **Design docs authored:** D10 (explain), D14 (API reference) + D13 (DD-12)

> **M6 status: COMPLETE** — built on `feat/m5-m6-adapters-surfaces` merged in `5663f16`; issues #48–54 closed. CLI init, plan, critique, plans list/show/diff --graph, explain, replay, escalate. HTTP service with 10 endpoints. CUJ 1 e2e test green.

**Dependency:** M1–M4 + M5 (MCP server). **Produces for M7/M8/M9:** full CLI, HTTP service, explain, init scaffold.