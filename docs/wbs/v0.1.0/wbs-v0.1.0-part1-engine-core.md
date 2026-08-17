# WBS — PlannerCritic Engine v0.1.0 Part 1: Core Engine + Store & Provider Layer

> **Milestones covered:** M1 (Core Engine) + M2 (Plan Store + LLM Provider Layer)
> **PRD covering these milestones:** [02-architecture](../../design/prd/02-architecture.md) (§2.1, §2.3, §2.4, §2.8) · [05-features](../../design/prd/05-features.md) (§5.1, §5.2) · [07-success-metrics](../../design/prd/07-success-metrics.md) (§7.1) · [08-risks](../../design/prd/08-risks.md)

---

## Milestone 1: Core Engine — schemas, deterministic gates, loop controller

**Objective:** Stand up the model- and framework-agnostic core, fully testable with **fake providers** — no LLM required: the typed Goal/Plan schemas (with parallel/branch semantics), the six deterministic critique gates, and the loop controller (revision cap, convergence, regression guard, approval threshold, fail-closed). Determinism CI-asserted.

**PRD coverage:** F-01, F-02, F-12, F-05, F-06, F-07, F-08, F-15(schema), F-73, F-74, F-77
**CUJs covered:** CUJ 4 (loop converges/escalates), CUJ 6 (plan as versioned artifact — schema layer)

### M1 Design Documents (author during this milestone)

- **D1 — Architecture v0.1.0** (`docs/architecture/architecture-v0.1.0.md`): *seed* the component diagram (§2.3) + module map. Finalize in M10.
- **D2 — Plan schema design** (`docs/design/plan-schema-design.md`): every typed field, validation rule, serialization contract for `Goal`/`PlanVersion`/`Task`/`Branch`/`Dependency`/`VerificationStep`/`RollbackStep`.
- **D3 — Loop controller design** (`docs/design/loop-controller-design.md`): the loop algorithm (§2.6.1), termination semantics, determinism contract, convergence + regression rules.
- **D13 — Design decisions** (`docs/design/design-decisions.md`): DD-01 (repo/package/CLI naming — `planner-critic`/`planner_critic`/`plancritic`), DD-02 (fail-closed boundary — `ApprovedPlan` is the only executable type), DD-03 (determinism contract scope).

### M1 Key Items (explicitly called out)

- **Goal schema** ([§2.8](../../design/prd/02-architecture.md#28-plan-schema-typed-sketch)): `id`, `description`, `constraints{budget{max_tokens,max_calls,max_revisions}, time, environment, tools[]}`, `risk_tolerance{strict|balanced}`, `replan_policy{patch|restart|abort}`, `approval_ttl` (seconds, default ∞), `metadata`.
- **Plan schema** ([§2.8](../../design/prd/02-architecture.md#28-plan-schema-typed-sketch), F-15): `PlanVersion` (immutable once stored: `id`, `goal_id`, `plan_schema_version` semver, `version`, `parent_version`, `created_at`), `Task` (`parallel_group`, `preconditions[]`, `verification`, `rollback`, `risk_class`, `blast_radius`), `Branch{fan_out|fan_in, join{all|any|quorum}}`, `Dependency{hard|soft, reason}`, `VerificationStep{what,how,expected}`, `RollbackStep{trigger,action,safety_guard}`.
- **Finding type** ([§2.8](../../design/prd/02-architecture.md#28-plan-schema-typed-sketch)): `heuristic_family`, `severity{blocker|warning|info}`, `reason_code`, `message`, `task_id`, `version`, `suggested_fix`.
- **Deterministic gates** ([§2.5.2](../../design/prd/02-architecture.md#252-deterministic-gates-the-free-layer)): exactly `schema_valid`, `no_dep_cycles`, `ordering_sane`, `verification_present`, `rollback_present`, `preconditions_referenced`. **Code, not model output** — injection-immune. Each returns findings with its reason code.
- **Loop controller** ([§2.6.1](../../design/prd/02-architecture.md#261-loop-controller-algorithm-pseudocode)): implement the pseudocode verbatim. Terminations: approve / revision cap (default 3, configurable) / convergence / regression guard / budget (M1 stubs; M3 enforces fully).
- **Approval threshold** ([§2.6](../../design/prd/02-architecture.md#26-approval--loop-semantics)): `strict` = zero warnings; `balanced` = warnings acknowledged; no blockers ever remain.
- **Fail-closed** (F-73): an unapproved plan cannot be handed to an executor.
- **Reason-code catalog** (F-77): stable machine-readable `reason_code` per gate + loop decision.

### M1 Task Checklist

> Each task lists the files it creates/modifies (Build), the behavior it must produce, and the edge cases it must survive. Status checkboxes track progress; the exit gate at the bottom is the milestone's completion bar.

| # | Task | Build (files) | Behavior + edge cases | Feature | Verify | Status |
|---|------|---------------|----------------------|---------|--------|--------|
| 1 | Package scaffold | Create `pyproject.toml` (src layout), `planner_critic/__init__.py` (exports `Engine`, `__version__`), pytest/ruff/mypy/coverage config | `pip install -e .` works; `plancritic --version` placeholder; ruff+mypy strict+coverage 95 preconfigured | F-60(partial) | clean venv install + import | [#1](https://github.com/deghosal-2026/planner-critic-engine/issues/1) · [x] |
| 2 | Goal schema | Create `planner_critic/schema/goal.py` | Pydantic v2 model per §2.8; strict enums; `budget` optional; `approval_ttl` default ∞ | F-01 | valid/invalid fixtures; bad enum → `ValidationError` | [#2](https://github.com/deghosal-2026/planner-critic-engine/issues/2) · [x] |
| 3 | Plan schema | Create `planner_critic/schema/plan.py` | `PlanVersion`, `Task`, `Branch`, `Dependency`, `VerificationStep`, `RollbackStep`; immutability; `to_dict`/`from_dict`; `plan_schema_version`; `parallel_group` + branch validation | F-02, F-15 | JSON round-trip; immutable-once-stored; branch join enum; parallel_group validity | [#3](https://github.com/deghosal-2026/planner-critic-engine/issues/3) · [x] |
| 4 | Types + reason codes | Create `planner_critic/types.py`, `planner_critic/reason_codes.py` | `Finding`, `Escalation`, `ExecutionTrace`, `PlanComplexity`, `ApprovedPlan`, `PlanningError`; catalog in `reason_codes.py` | F-77 | every gate + loop decision maps to a stable code | [#4](https://github.com/deghosal-2026/planner-critic-engine/issues/4) · [x] |
| 5 | Role protocols | Create `planner_critic/roles.py` | `PlannerRole.decompose(goal)->PlanVersion`, `CriticRole.audit(plan)->list[Finding]` abstract | F-03, F-04 | fake roles usable in tests | [#5](https://github.com/deghosal-2026/planner-critic-engine/issues/5) · [x] |
| 6 | Deterministic gates | Create `planner_critic/gates/` (7 modules: `__init__`, `schema_valid`, `dep_cycles`, `ordering`, `verification`, `rollback`, `preconditions`, `parallel_safety`) | 6 gate functions per §2.5.2 + `parallel_safety` (F-15 unsafe-parallel audit); **return findings, never raise** on malformed input; injection-immune | F-12, F-15 | each gate flags its seeded-flaw fixture; malformed input → finding not exception | [#6](https://github.com/deghosal-2026/planner-critic-engine/issues/6) · [x] |
| 7 | Loop controller | Create `planner_critic/loop.py`, `planner_critic/loop/{convergence,regression,budget,ttl}.py` | §2.6.1 pseudocode; revision cap 3 (configurable); convergence (circling blockers / near-zero diff); regression guard (new blocker); approval threshold; determinism | F-05, F-06, F-07, F-08, F-74 | fake-provider matrix (converge/cap/thrash/regress) + **identical inputs → identical decisions** | [#7](https://github.com/deghosal-2026/planner-critic-engine/issues/7) · [x] |
| 8 | Approval + fail-closed | Create `planner_critic/approval.py` | `ApprovedPlan` wrapper; threshold resolver; no execute path except via `ApprovedPlan` | F-08, F-73 | strict/balanced matrices; non-approved plan cannot construct executor input | [#8](https://github.com/deghosal-2026/planner-critic-engine/issues/8) · [x] |
| 9 | Unit + integration tests | Create `tests/` (test_types, test_schema, test_gates, test_loop, fixtures/loop_matrix.yaml) | cover schemas, gates, loop, approval; end-to-end loop with fake roles | — | >95% coverage on `planner_critic` | [#9](https://github.com/deghosal-2026/planner-critic-engine/issues/9) · [x] |
| 10 | Acceptance matrix | Create `tests/fixtures/loop_matrix.yaml` + runner | Goal × fake-role-output × expected termination | — | 100% matrix cells pass in CI | [#10](https://github.com/deghosal-2026/planner-critic-engine/issues/10) · [x] |

### M1 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| Loop determinism | Identical inputs → identical decisions 100% | CI test |
| Loop correctness | Every matrix cell terminates correctly | `test_loop_matrix.py` |
| Fail-closed | 0 paths non-approved → executor | type-level + unit tests |
| Reason coverage | every gate + loop decision has a reason code | catalog test |
| Coverage | >95% | `--cov-fail-under=95` |
| Lint | 0 ruff, 0 mypy strict | `ruff check .` + `mypy --strict` |

### M1 Exit Gate

- [x] Code review passed
- [x] Coverage > 95%
- [x] Lint clean (ruff + mypy strict)
- [x] Comments + docstrings in all code
- [x] Loop matrix 100% green; determinism CI-asserted
- [x] **Design docs authored:** D1 (architecture seed), D2 (plan-schema), D3 (loop-controller), D13 (DD-01/02/03)

> **M1 status: COMPLETE** — closed in commit `c1473bb` (feat/m1-core-engine); issues #1–10 closed. 94 tests pass; 96.81% coverage; ruff + strict mypy clean. **Exit-gate code review (Aug 16, 2026) found and fixed 4 issues** (uncommitted until reviewed here): loop off-by-one (escalation pointed at an un-audited `r{cap+1}` with empty findings), per-revision `created_at` copied from the parent, preconditions gate accepting forward/self task references, and a redundant mode branch + missing budget check on the deterministic-first blocker path.

**Dependency:** none. **Produces for M2+:** `Goal`, `PlanVersion`, `Finding`, `Escalation`, `ExecutionTrace`, `PlanComplexity`, `ApprovedPlan`, role protocols, loop controller, reason codes.

---

## Milestone 2: Plan Store + LLM Provider Layer

**Objective:** The pluggable plan store (SQLite default, Postgres-ready interface, schema versioning + migrate) and the config-driven LLM provider layer (protocol → registry → OpenAI-compatible transport), plus the read-only `EnvProbe` protocol. CI-complete with zero paid LLM.

**PRD coverage:** F-09, F-63, F-27, F-20, F-21, F-22, F-23, F-24, F-19, F-26, F-70(partial)
**CUJs covered:** CUJ 1 (register provider — registry/transport half), CUJ 6 (versioned artifact — store half)

### M2 Design Documents

- **D4 — DB schema sketch** (`docs/architecture/db-schema-sketch.md`): SQLite DDL — tables/columns/indices for `plan_versions`, `findings`, `escalations`, `execution_traces`; migration versioning table.
- **D5 — Provider layer design** (`docs/design/provider-layer-design.md`): registry-first rationale, config file format (settle TOML), transport contract, EnvProbe protocol contract.
- **D13 — Design decisions**: DD-04 (config format TOML), DD-05 (store side-channel — continue in-memory), DD-06 (EnvProbe read-only contract).

### M2 Key Items (explicitly called out)

- **Store protocol** ([§2.1](../../design/prd/02-architecture.md#21-core-value)): `put_plan_version`, `put_findings`, `get_plan`, `list_plans`, `diff(v1,v2)`, escalation + execution-trace put/get, `link`. **Side-channel:** store down → warn + continue in-memory ([§7.2](../../design/prd/07-success-metrics.md#72-reliability--support)).
- **SQLite store** (F-63): default behind the interface.
- **Schema versioning + migrate** (F-27, [§2.8](../../design/prd/02-architecture.md#28-plan-schema-typed-sketch)): `plan_schema_version` on every row; reversible migration registry; old versions remain readable.
- **Provider protocol** (F-20, [§2.4](../../design/prd/02-architecture.md#24-llm-provider-layer-built-registry-first)): `complete(messages, tool_schemas)` → structured output; `name`, `base_url`, `model`, `transport`, optional `api_key`.
- **Registry-first** (F-21): providers in config, not code — `plancritic providers add/list/rm`; engine loads whatever is configured.
- **OpenAI-compatible transport** (F-22): first concrete impl *on top of* the registry; OMLX/Ollama/vLLM/OpenRouter/OpenAI.
- **Separate planner vs critic providers** (F-23): distinct provider/model per role; different family for critic recommended.
- **Structured-output enforcement** (F-24): re-validate against typed schema; bounded retries then failure.
- **EnvProbe** (F-19, F-26, [§2.8](../../design/prd/02-architecture.md#28-plan-schema-typed-sketch)): `kind{env_var,db_query,http_check,deploy_status}`, `query`, `expected`; read-only by contract; result recorded in trace; deterministic gates never depend on a probe.
- **Provider failure** (F-70 partial): timeout/error → deterministic `planning_unavailable` per role, fail-closed.

### M2 Task Checklist

| # | Task | Build (files) | Behavior + edge cases | Feature | Verify | Status |
|---|------|---------------|----------------------|---------|--------|--------|
| 1 | Store protocol | Create `planner_critic/store/base.py` | `PlanStore` ABC per §2.1; side-channel warning behavior; in-memory impl for tests | F-09 | fake-store protocol tests; store-down → warn + continue | [#11](https://github.com/deghosal-2026/planner-critic-engine/issues/11) · [x] |
| 2 | SQLite store | Create `planner_critic/store/sqlite.py` | DDL + CRUD + `diff` + execution-trace link | F-63, F-09 | CRUD + diff round-trip on temp DB | [#12](https://github.com/deghosal-2026/planner-critic-engine/issues/12) · [x] |
| 3 | Schema versioning + migrate | Create `planner_critic/store/versions.py`, `planner_critic/cli/migrate.py` | `plan_schema_version` tracked; reversible migration registry; old versions readable | F-27 | migrate up/down; old data still readable | [#13](https://github.com/deghosal-2026/planner-critic-engine/issues/13) · [x] |
| 4 | Provider protocol | Create `planner_critic/llm/base.py` | protocol + structured-output envelope; error types (timeout, bad JSON, schema mismatch) | F-20 | fake provider conforms; error types raised | [#14](https://github.com/deghosal-2026/planner-critic-engine/issues/14) · [x] |
| 5 | Provider registry | Create `planner_critic/llm/registry.py`, `planner_critic/cli/providers.py` | config file (TOML) load/save; role→provider mapping; CLI add/list/rm | F-21, F-23 | registry round-trip; role mapping; CLI persists | [#15](https://github.com/deghosal-2026/planner-critic-engine/issues/15) · [x] |
| 6 | OpenAI-compat transport | Create `planner_critic/llm/transport_openai.py` | Chat Completions + JSON mode; base_url override; optional api_key | F-22 | httpx-mocked tests: request/response shape, base_url | [#16](https://github.com/deghosal-2026/planner-critic-engine/issues/16) · [x] |
| 7 | Structured-output enforcement | Create `planner_critic/llm/structured.py` | validate against Goal/Plan/Finding schemas; bounded retries then `planning_unavailable` | F-24, F-70 | mismatch→retry→success; persistent mismatch→failure mode | [#17](https://github.com/deghosal-2026/planner-critic-engine/issues/17) · [x] |
| 8 | EnvProbe | Create `planner_critic/probe/` (base, env_var, http_check, db_query stub, deploy_status stub) | read-only by contract; result recorder; deterministic gates never depend on probe | F-19, F-26 | probe result recorded; never mutates | [#18](https://github.com/deghosal-2026/planner-critic-engine/issues/18) · [x] |
| 9 | Integration test | Create `tests/test_store.py`, `tests/test_llm.py`, `tests/test_probe.py` | store + provider against fake transport; full store round-trip of a loop run | — | end-to-end with zero network | [#19](https://github.com/deghosal-2026/planner-critic-engine/issues/19) · [x] |

### M2 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| Store correctness | 100% CRUD + diff round-trip on SQLite | store suite |
| Migration safety | old schemas readable; migrate reversible | migration tests |
| Registry persistence | config loads on restart; role mapping correct | registry tests |
| Transport fidelity | OpenAI-compat shape correct on mock | httpx mock tests |
| Structured-output | 100% responses validated; bounded retries honored | mismatch tests |
| EnvProbe read-only | 0 mutation; results recorded | probe tests |
| Coverage | >95% | `--cov-fail-under=95` |
| Lint | 0 ruff, 0 mypy strict | `ruff` + `mypy` |

### M2 Exit Gate

- [x] Code review passed
- [x] Coverage > 95% (97.88%)
- [x] Lint clean (ruff + mypy strict)
- [x] Comments + docstrings in all code
- [x] Side-channel contract verified (store down → warn + continue)
- [x] `plancritic providers add/list/rm` functional, zero paid LLM
- [x] **Design docs authored:** D4 (DB schema), D5 (provider layer), D13 (DD-04/05/06)

> **M2 status: COMPLETE** — closed on `feat/m2-store-provider`; issues #11–19 built. 184 tests pass; 97.88% coverage; ruff + strict mypy clean. **Exit-gate code review found and fixed 2 issues**: (1) `ProviderRegistry._from_dict` documented "skip malformed entries" but crashed on a non-table provider spec — now skips with a warning; (2) `InMemoryStore.list_plans` and `SQLiteStore.list_plans` disagreed on global ordering (id desc vs id asc) — aligned to `(plan_id asc, version desc)` and locked with a cross-implementation test. CLI verified end-to-end: `--version`, `migrate`, `providers add/list/rm`.

**Dependency:** M1. **Produces for M3+:** `PlanStore` (+ SQLite), schema versioning, `LLMProvider` + registry, OpenAI-compat transport, `EnvProbe`, provider failure modes.