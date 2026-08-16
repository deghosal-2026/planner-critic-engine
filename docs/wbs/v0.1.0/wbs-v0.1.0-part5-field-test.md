# WBS — PlannerCritic Engine v0.1.0 Part 5: Field Test

> **Milestone covered:** M8 (Field Test — hermetic CI gate + local-model release sweep)
> **PRD covering this milestone:** [02-architecture](../../design/prd/02-architecture.md) (§2.4 hermetic, §2.10 terminal state) · [04-users-and-cujs](../../design/prd/04-users-and-cujs.md) (CUJ 11) · [07-success-metrics](../../design/prd/07-success-metrics.md) (§7.1 #2, #4, #5, #6, #11)

---

## Milestone 8: Field Test — hermetic CI gate + local-model sweep

**Objective:** Make the release *verified*: a hermetic CI gate (fake providers — never flakes, never costs money) that asserts loop-correctness, budget integrity, and determinism; and a local-model release sweep (`plancritic field-test`, OMLX/Ollama) that runs the sample corpus through real planner/critic calls across all six framework adapters. The field-test report is the release gate — any P0 miss blocks the release.

**PRD coverage:** F-67, F-68
**CUJs covered:** CUJ 11 (field test — it actually works in real agent loops)

### M8 Design Documents

- **D12 — Field test design** (`docs/design/field-test-design.md`): matrix design (goals × frameworks × expected/actual), hermetic gate architecture, field-sweep harness, report template.
- **Field-test report** (`docs/field-test/FIELD_TEST_REPORT.md`): regenerated per release — the artifact that gates M9.

### M8 Key Items (explicitly called out)

- **Hermetic CI gate** (F-67, [§CUJ11](../../design/prd/04-users-and-cujs.md#cuj-11--field-test-it-actually-works-in-real-agent-loops)): deterministic gates + loop controller + convergence/regression/budget semantics asserted with fake providers in CI. Never flakes (no network), never costs money ($0 LLM spend). A flake in the hermetic gate is a CI bug, not a field-signal bug. Tests: loop matrix (converge, cap-escalate, thrash-escalate, regress-escalate, approve), budget-hit test (exceed → escalate, never overspend), determinism (identical inputs → identical decisions), adversarial-goal safety (deterministic blocker not overridable).

- **Local-model field sweep** (F-68, [§CUJ11](../../design/prd/04-users-and-cujs.md#cuj-11--field-test-it-actually-works-in-real-agent-loops)): `plancritic field-test` drives the M7 sample corpus (migration, rollout, refactor, incident-response) through real planner/critic LLM calls via OMLX/Ollama across all six framework adapters. Assertions: a seeded flaw in each goal's first draft is caught; revision converges to approval (or escalates cleanly on known-ambiguous goals); escalation round-trips; re-gate detects a stale precondition and triggers defined replan; a planning failure is classified and a missed critique is recorded.

- **Field-test report** (`docs/field-test/FIELD_TEST_REPORT.md`): goals × frameworks × expected/actual × pass/fail matrix, regenerated each release sweep. Committed as the release evidence. Format: markdown table with embedded Mermaid graphs for representative traces.

- **Adversarial goal test:** the adversarial goal from the corpus (M7) is run in a dedicated sweep row — assertion: deterministic gates hold; LLM critic may be biased but its blocker equivalent is already surfaced by the gate.

### M8 Task Checklist

| # | Task | Build (files) | Behavior + edge cases | Feature | Verify | Status |
|---|------|---------------|----------------------|---------|--------|--------|
| 1 | Hermetic CI gate | Create `tests/field_test/hermetic/` — suite that runs the loop matrix, budget-audit, determinism, adversarial goal, fail-closed matrix with fake providers + fake store | No network, no paid LLM; flake-free by construction; runs on every push | F-67 | CI gate green after every push; 0 flakes in 20 runs | [#59](https://github.com/deghosal-2026/planner-critic-engine/issues/59) · - [ ] |
| 2 | Field-test CLI | Create `planner_critic/cli/field_test.py` | `plancritic field-test` drives corpus × 6 adapters; collects pass/fail per cell; writes report JSON/markdown; configurable provider (OMLX/Ollama env vars) | F-68 | CLI drives all cells; report emitted | [#60](https://github.com/deghosal-2026/planner-critic-engine/issues/60) · - [ ] |
| 3 | Field-test harness | Create `tests/field_test/` (or reuse `cli/field_test.py` + a test runner that mocks providers) | Deterministic cell matrix: goals × frameworks × assertions; run in CI with fake providers (hermetic) and optionally locally with real providers | F-67, F-68 | CI grid green (fake); local grid populated (real) | [#61](https://github.com/deghosal-2026/planner-critic-engine/issues/61) · - [ ] |
| 4 | Local-model sweep (manual gate) | Document config in `docs/field-test/README.md` — how to run the sweep with OMLX/Ollama | Corpus × 6-adapters matrix against local models; pass/fail per cell; blocked on P0 miss | F-68 | `FIELD_TEST_REPORT.md` populated + committed | [#62](https://github.com/deghosal-2026/planner-critic-engine/issues/62) · - [ ] |
| 5 | Field-test report | Create `docs/field-test/FIELD_TEST_REPORT.md` | Matrix table: goal | framework | expected (flaw caught/converge/escalate/re-gate/missed-critique) | actual | pass/fail; embedding representative Mermaid traces | — | report committed; all P0 cells pass | [#63](https://github.com/deghosal-2026/planner-critic-engine/issues/63) · - [ ] |
| 6 | Adversarial goal sweep | Dedicated test row for adversarial goal | deterministic blocker holds → passes; LLM critic may fail but the gate is the authority | F-04, F-12 | adversarial cell passes | [#64](https://github.com/deghosal-2026/planner-critic-engine/issues/64) · - [ ] |

### M8 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| Hermetic CI gate | 0 flakes; loop matrix 100%; determinism 100%; budget 100% | CI tests |
| Blocker-detection rate (live) | ≥90% of seeded flaws surfaced | field-test report |
| Loop correctness (live) | ≥95% converge or cleanly escalate | field-test report |
| Framework coverage | all six adapters exercised natively in the sweep | field-test report |
| Cost | $0 LLM spend in CI; live sweep on local model (no paid API) | CI config + report |
| Replan correctness (live) | seeded precondition drift → correct replan fires | field-test report cell |
| Coverage (existing) | no regression; >95% on all existing code | CI coverage gate |
| Lint | 0 ruff + 0 mypy strict | `ruff` + `mypy` |

### M8 Exit Gate

- [ ] Code review passed (field-test harness + CLI)
- [ ] Coverage > 95% (no regression)
- [ ] Lint clean (ruff + mypy strict)
- [ ] Comments + docstrings in all code
- [ ] Hermetic CI gate green (flake-free, $0)
- [ ] Field-test report committed with all P0 cells passing
- [ ] Adversarial goal green; deterministic gates hold
- [ ] `plancritic field-test` driver functional end-to-end
- [ ] **Design docs authored:** D12 (field test design) + `FIELD_TEST_REPORT.md`

**Dependency:** M1–M7 (corpus from M7, adapters from M5, loop from M3, CLI from M6). **Produces for M9:** field-test report (the release gate), deterministic confidence in the release.