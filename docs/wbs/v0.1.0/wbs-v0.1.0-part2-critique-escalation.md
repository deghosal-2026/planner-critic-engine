# WBS — PlannerCritic Engine v0.1.0 Part 2: Critique Engine + Escalation, Forensics, Replan

> **Milestones covered:** M3 (Critique Engine + Loop Semantics) + M4 (Escalation, Forensics, Replan, Viz)
> **PRD covering these milestones:** [02-architecture](../../design/prd/02-architecture.md) (§2.5, §2.5.1, §2.5.3, §2.6, §2.7, §2.7b, §2.7c, §2.7d, §2.7e) · [05-features](../../design/prd/05-features.md) (§5.1, §5.3, §5.5, §5.7) · [07-success-metrics](../../design/prd/07-success-metrics.md) (§7.1)

---

## Milestone 3: Critique Engine + Loop Semantics

**Objective:** Make the engine *actually careful*: the six-heuristic LLM critic, dual critique modes (`deterministic-first` default, `llm-every-revision` option), diff-aware re-audit, per-goal budget enforcement, the deterministic complexity/cost estimate, shadow mode (`dry_run`), and approval expiry (TTL). The full loop now runs end-to-end with real provider-backed critique.

**PRD coverage:** F-04, F-10, F-11, F-13, F-14, F-17, F-18, F-78
**CUJs covered:** CUJ 2 (aha — critic catches real flaw), CUJ 3 (deterministic-first), CUJ 13 (shadow mode)

### M3 Design Documents

- **D6 — Critique engine design** (`docs/design/critique-engine-design.md`): six heuristic families (§2.5.1), dual-mode gate logic, diff-aware scope, budget enforcement mechanism.
- **D13 — Design decisions:** DD-07 (deterministic-first default rationale), DD-08 (diff-aware scope — changed-tasks-only tradeoff).

### M3 Key Items (explicitly called out)

- **Six heuristic families** ([§2.5.1](../../design/prd/02-architecture.md#251-the-six-critique-heuristic-families)): feasibility, risk, missing steps, unsafe sequencing (incl. **unsafe parallelization** — two prod writes in one `parallel_group`), unverified dependencies, weak rollback. Each finding: family, severity, task ref, reason code, message, suggested fix.
- **Dual critique mode** ([§2.5](../../design/prd/02-architecture.md#25-critique-engine-dual-mode)): `critic.mode=deterministic-first` (gates free first, LLM only on surviving drafts) and `critic.mode=llm-every-revision` (full every revision). One config knob, same engine.
- **Injection-safety** ([§2.5.1](../../design/prd/02-architecture.md#251-the-six-critique-heuristic-families)): a deterministic-gate blocker can **never** be overridden by the LLM critic.
- **Diff-aware critique** (F-78, [§2.5.3](../../design/prd/02-architecture.md#253-diff-aware-critique-cost-optimization)): on revision N>1, compute changed-task set from plan diff + their dependents; re-audit only those.
- **Budget enforcement** (F-13, [§2.4](../../design/prd/02-architecture.md#24-llm-provider-layer-built-registry-first)): `constraints.budget{max_tokens, max_calls, max_revisions}` — loop controller enforces; hit → escalate, never overspend.
- **Complexity/cost estimate** (F-17, [§2.7d](../../design/prd/02-architecture.md#27d-plan-complexity--cost-estimate-deterministic-pre-approval)): step count, parallel-branch count, irreversible-op count, est. LLM calls/tokens. Deterministic, zero LLM cost. Within ±20% of actual on corpus goals.
- **Shadow mode** (F-14, [§2.7c](../../design/prd/02-architecture.md#27c-shadow-mode-the-adoption-wedge)): `dry_run` → full loop, decisions logged `mode: shadow`, no gating.
- **Approval expiry** (F-18, [§2.7e](../../design/prd/02-architecture.md#27e-approval-expiry--stale-plan)): `approval_ttl` (default ∞); expired approval → forced replan.

### M3 Task Checklist

| # | Task | Build (files) | Behavior + edge cases | Feature | Verify | Status |
|---|------|---------------|----------------------|---------|--------|--------|
| 1 | LLM critic role | Create `planner_critic/critique/critic.py` | six-heuristic prompt + structured findings; severity grading; reason codes mapped to the catalog | F-04 | fake-provider test: seeded-flaw goal → correct blocker surfaced | [#20](https://github.com/deghosal-2026/planner-critic-engine/issues/20) · [x] |
| 2 | Dual critique mode | Create `planner_critic/critique/mode.py` | `deterministic-first` vs `llm-every-revision` toggled by `critic.mode` config; gate integration | F-10, F-11 | same goal, both modes; deterministic-first skips LLM when gates block | [#21](https://github.com/deghosal-2026/planner-critic-engine/issues/21) · [x] |
| 3 | Diff-aware critique | Create `planner_critic/critique/diff.py` | compute changed-task set from plan diff; re-audit changed + dependents only on N>1 | F-78 | diff decreases audit scope; `llm-every-revision` does full | [#22](https://github.com/deghosal-2026/planner-critic-engine/issues/22) · [x] |
| 4 | Budget enforcement | Create `planner_critic/loop/budget.py` | track per-run tokens/calls/revisions against `budget`; budget-hit → escalate; 0 runs exceed their budget | F-13 | CI budget-audit test; escalation on budget hit | [#23](https://github.com/deghosal-2026/planner-critic-engine/issues/23) · [x] |
| 5 | Complexity estimate | Create `planner_critic/estimate.py` | deterministic summary per §2.7d; zero LLM cost | F-17 | estimated calls/tokens within 20% of actual on fixtures | [#24](https://github.com/deghosal-2026/planner-critic-engine/issues/24) · [x] |
| 6 | Shadow mode | Create `planner_critic/shadow.py` | `dry_run` flag; full loop decisions stored `mode:shadow`; shadow vs live diffable via store | F-14 | `--dry-run` does not gate; store distinguishes shadow | [#25](https://github.com/deghosal-2026/planner-critic-engine/issues/25) · [x] |
| 7 | Approval expiry | Create `planner_critic/loop/ttl.py` | `approval_ttl` enforcement on approved plans; expired → forced replan per `replan_policy` | F-18 | TTL set → replan fires; ∞ default → no expiry | [#26](https://github.com/deghosal-2026/planner-critic-engine/issues/26) · [x] |
| 8 | Injection-safety test | Create `tests/fixtures/adversarial_goal.yaml` + test | adversarial goal tries to suppress a blocker; deterministic gates hold (LLM cannot override) | F-12, F-04 | adversarial fixture green in CI (hermetic) | [#27](https://github.com/deghosal-2026/planner-critic-engine/issues/27) · [x] |
| 9 | Critique acceptance tests | Create `tests/fixtures/seeded_goals/` + `tests/test_critique.py` | each heuristic family catches its seeded case; inject fake LLM output that simulates a successful critique | F-04 | ≥90% seeded flaws surfaced (target 100%) | [#28](https://github.com/deghosal-2026/planner-critic-engine/issues/28) · [x] |
| 10 | End-to-end loop test | Create `tests/test_e2e_loop.py` | Full loop run with fake providers: plan → gates → critique → revise → approve; all termination paths exercised | F-05, F-10 | e2e green on fake providers | [#29](https://github.com/deghosal-2026/planner-critic-engine/issues/29) · [x] |

### M3 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| Blocker detection | ≥90% seeded flaws surfaced (100% target on fixtures) | Critique acceptance suite |
| Diff-aware correctness | same catch with reduced scope | diff tests |
| Budget integrity | 0 runs exceed declared budget | CI audit |
| Determinism preserved | same inputs → same decisions (M1 property retained) | determinism test |
| Coverage | >95% | `--cov-fail-under=95` |
| Lint | 0 ruff + 0 mypy strict | `ruff` + `mypy` |

### M3 Exit Gate

- [x] Code review passed
- [x] Coverage > 95% (97.64%)
- [x] Lint clean (ruff + mypy strict)
- [x] Comments + docstrings in all code
- [x] Seeded-flaw critique acceptance suite green (6/6 families); injection-safety fixture green
- [x] `deterministic-first` skips LLM on gate-blocked drafts; `llm-every-revision` fully loads
- [x] Budget + shadow mode + TTL behaviors verified in CI (hermetic)
- [x] **Design docs authored:** D6 (critique engine) + D13 (DD-07/08)

> **M3 status: COMPLETE** — built on `feat/m3-critique-engine`; issues #20–29. 230 tests pass; 97.64% coverage; ruff + strict mypy clean (exit-gate review fixed a shadowed duplicate e2e test name + a line-too-long in `_controller.py`). Three critique modes (`heuristic-only` / `deterministic-first` / `llm-every-revision`); six-heuristic LLM critic via structured-output enforcer; diff-aware re-audit (F-78); budget + cost estimate (F-13/F-17); shadow mode (F-14); approval TTL (F-18); injection-safety + adversarial fixture. Field-test plan for the three modes against local OMLX tracked in issues #74–76 / WBS M9 rows 7–9 (the containerized twin lives in M8 Docker T6).

**Dependency:** M1 + M2 (types, gates, loop, store, providers, EnvProbe). **Produces for M4+:** six-heuristic critic, dual-mode critique, diff-aware audit, budget enforcement, complexity estimate, shadow mode, TTL.

---

## Milestone 4: Escalation + Forensics + Replan + Viz

**Objective:** Close the human-in-the-loop and the explainability loop: escalation manager with minimal precise questions, plan↔execution linkage with `planning`/`execution` failure tagging, missed-critique records + suggested deterministic checks, defined replan semantics (`patch`/`restart`/`abort`) with full plan-history lineage, plan-graph export (Mermaid + JSON), and trace replay.

**PRD coverage:** F-30, F-31, F-32, F-34, F-50, F-51, F-52, F-16, F-53, F-75, F-76
**CUJs covered:** CUJ 5 (escalate/resolve), CUJ 7 (replay), CUJ 9 (re-gate → replan), CUJ 10 (diagnose a failed run)

### M4 Design Documents

- **D7 — Escalation design** (`docs/design/escalation-design.md`): escalation manager, question-precision contract (single resolvable question), resolution flow, patching semantics.
- **D8 — Replan + re-gate design** (`docs/design/replan-regate-design.md`): `patch`/`restart`/`abort` policies, re-gate mechanics, EnvProbe interaction, lineage recording.
- **D13 — Design decisions:** DD-09 (replan policy defaults — `patch`), DD-10 (escalation precision contract).

### M4 Key Items (explicitly called out)

- **Escalation manager** (F-30, [§2.1](../../design/prd/02-architecture.md#21-core-value)): minimal precise single question; shows goal + current plan + blocker + critique trail + revision history; **direct plan patching** before approval. Single-question precision audited in tests.
- **Escalation CLI + patch** (F-31, F-34): `escalate list/approve/deny [--patch ...]`; patched plans re-submitted to the critic.
- **Escalation MCP tools** (F-32): `escalate_list/approve/deny` tools.
- **Replan semantics** (F-16, [§2.7b](../../design/prd/02-architecture.md#27b-replan-semantics-mid-execution)): `patch` (default — revise remaining steps, sub-plan linked to parent), `restart` (full re-decompose, archive prior), `abort` (stop → human). Per-goal `replan_policy`.
- **Replan trace** (F-53): sub-plan linked into same history; partial execution preserved → full lineage reconstructable.
- **Plan–execution link** (F-50): execution linked to approved plan + task; outcome tagged `planning`/`execution`.
- **Missed-critique + suggested check** (F-51, F-52): on failure the critic missed → record with critique snapshot + auto-suggest a deterministic check.
- **Plan-graph export** (F-75): task DAG → Mermaid + JSON.
- **Trace replay** (F-76): `plancritic replay <plan_id>` walks history; `--step`, `--format json`.

### M4 Task Checklist

| # | Task | Build (files) | Behavior + edge cases | Feature | Verify | Status |
|---|------|---------------|----------------------|---------|--------|--------|
| 1 | Escalation manager | Create `planner_critic/escalation.py` | create/list/resolve; single-question design; resolution recorded in plan history | F-30, F-34 | escalation question precision test (one resolvable question) | [#30](https://github.com/deghosal-2026/planner-critic-engine/issues/30) · [x] |
| 2 | Escalation CLI + patch | Modify `planner_critic/cli/escalate.py` | list/approve/deny `[--patch ...]`; patched plan re-submitted to critic | F-31, F-34 | CLI round-trip; patched plan re-critiqued | [#31](https://github.com/deghosal-2026/planner-critic-engine/issues/31) · [x] |
| 3 | Escalation MCP tools | Create `planner_critic/server/mcp_tools_escalate.py` | `escalate_list/approve/deny` tools | F-32 | MCP tool tests (server wiring in M5) | [#32](https://github.com/deghosal-2026/planner-critic-engine/issues/32) · [x] |
| 4 | Replan semantics | Create `planner_critic/replan.py` | `patch`/`restart`/`abort` per §2.7b; per-goal `replan_policy` | F-16 | per-policy fixtures: correct policy fires; lineage reconstructable | [#33](https://github.com/deghosal-2026/planner-critic-engine/issues/33) · [x] |
| 5 | Replan trace | Create `planner_critic/store/replan_trace.py` | link sub-plan into same history; partial execution preserved | F-53 | full lineage: original → partial → replan → completion | [#34](https://github.com/deghosal-2026/planner-critic-engine/issues/34) · [x] |
| 6 | Execution link + tagging | Create `planner_critic/execution.py` | bind execution to ApprovedPlan; per-task outcome; `failure_class` | F-50 | trace stored; classification recorded for failure | [#35](https://github.com/deghosal-2026/planner-critic-engine/issues/35) · [x] |
| 7 | Missed-critique + suggested check | Create `planner_critic/forensics.py` | planning failure critic missed → record with critique snapshot + surfaced suggested deterministic check | F-51, F-52 | missed-critique fixture → record + suggested check generated | [#36](https://github.com/deghosal-2026/planner-critic-engine/issues/36) · [x] |
| 8 | Plan-graph export | Create `planner_critic/viz/graph.py` | DAG → Mermaid + JSON | F-75 | Mermaid + JSON from any stored plan | [#37](https://github.com/deghosal-2026/planner-critic-engine/issues/37) · [x] |
| 9 | Trace replay | Create `planner_critic/viz/replay.py`, `planner_critic/cli/replay.py` | walk version history; `--step <n>`, `--format json` | F-76 | replay reproduces loop trace | [#38](https://github.com/deghosal-2026/planner-critic-engine/issues/38) · [x] |
| 10 | Integration test | End-to-end scenario in `tests/test_e2e_m4.py` | escalate → human patches → re-critique → approve → execute → failure → tag → missed-critique | F-30, F-16, F-50 | full arc green on fake provider | [#39](https://github.com/deghosal-2026/planner-critic-engine/issues/39) · [x] |

### M4 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| Escalation precision | each escalation resolvable with one decision | precision tests |
| Replan correctness | correct policy fires per goal | replan fixtures |
| Forensics value | failure classification + missed-critique queryable | forensics tests |
| Viz | graph + replay work on any stored plan | viz tests |
| Coverage | >95% | `--cov-fail-under=95` |
| Lint | 0 ruff + 0 mypy strict | `ruff` + `mypy` |

### M4 Exit Gate

- [x] Code review passed
- [x] Coverage > 95% (96.06%)
- [x] Lint clean (ruff + mypy strict)
- [x] Comments + docstrings in all code
- [x] Escalation round-trip (CLI); patched plan re-critiqued
- [x] Replan policies `patch`/`restart`/`abort` behave per §2.7b; lineage reconstructable
- [x] Missed-critique → suggested check recorded + queryable
- [x] Plan graph + replay work end-to-end
- [x] **Design docs authored:** D7 (escalation), D8 (replan+regate), D13 (DD-09/10)

> **M4 status: COMPLETE** — built on `feat/m4-escalation-forensics-replan-viz`; issues #30–39 closed. 300 tests pass; 96.06% coverage; ruff + strict mypy clean. Escalation manager with precision contract, CLI (`escalate list/approve/deny --patch`), MCP tools, replan (patch/restart/abort) with trace, execution recorder + failure tagging, forensics (missed-critique → suggested deterministic check), plan-graph export (Mermaid + JSON), and trace replay (CLI `replay --step --format`). Full end-to-end arc green. Design docs D7/D8/D13 authored.

**Dependency:** M1–M3. **Produces for M5+:** escalation manager + CLI/MCP tools, replan semantics + trace, forensics, graph export, replay.