# WBS — PlannerCritic Engine v0.1.0 Part 5: Field Test

> **Milestone covered:** M9 (Field Test — hermetic CI gate + local-model release sweep)
> **PRD covering this milestone:** [02-architecture](../../design/prd/02-architecture.md) (§2.4 hermetic, §2.10 terminal state) · [04-users-and-cujs](../../design/prd/04-users-and-cujs.md) (CUJ 11) · [07-success-metrics](../../design/prd/07-success-metrics.md) (§7.1 #2, #4, #5, #6, #11)

---

## Milestone 9: Field Test — hermetic CI gate + local-model sweep

**Objective:** Make the release *verified*: a hermetic CI gate (fake providers — never flakes, never costs money) that asserts loop-correctness, budget integrity, and determinism; and a local-model release sweep (`plancritic field-test`, OMLX/Ollama) that runs the sample corpus through real planner/critic calls across all six framework adapters. The field-test report is the release gate — any P0 miss blocks the release.

**PRD coverage:** F-67, F-68
**CUJs covered:** CUJ 11 (field test — it actually works in real agent loops)

### M9 Design Documents

- **D12 — Field test design** (`docs/design/field-test-design.md`): matrix design (goals × frameworks × expected/actual), hermetic gate architecture, field-sweep harness, report template.
- **Field-test report** (`docs/field-test/FIELD_TEST_REPORT.md`): regenerated per release — the artifact that gates M10.

### M9 Key Items (explicitly called out)

- **Hermetic CI gate** (F-67, [§CUJ11](../../design/prd/04-users-and-cujs.md#cuj-11--field-test-it-actually-works-in-real-agent-loops)): deterministic gates + loop controller + convergence/regression/budget semantics asserted with fake providers in CI. Never flakes (no network), never costs money ($0 LLM spend). A flake in the hermetic gate is a CI bug, not a field-signal bug. Tests: loop matrix (converge, cap-escalate, thrash-escalate, regress-escalate, approve), budget-hit test (exceed → escalate, never overspend), determinism (identical inputs → identical decisions), adversarial-goal safety (deterministic blocker not overridable).

- **Local-model field sweep** (F-68, [§CUJ11](../../design/prd/04-users-and-cujs.md#cuj-11--field-test-it-actually-works-in-real-agent-loops)): `plancritic field-test` drives the M7 sample corpus (migration, rollout, refactor, incident-response) through real planner/critic LLM calls via OMLX/Ollama across all six framework adapters. Assertions: a seeded flaw in each goal's first draft is caught; revision converges to approval (or escalates cleanly on known-ambiguous goals); escalation round-trips; re-gate detects a stale precondition and triggers defined replan; a planning failure is classified and a missed critique is recorded.

- **Field-test report** (`docs/field-test/FIELD_TEST_REPORT.md`): goals × frameworks × expected/actual × pass/fail matrix, regenerated each release sweep. Committed as the release evidence. Format: markdown table with embedded Mermaid graphs for representative traces.

- **Adversarial goal test:** the adversarial goal from the corpus (M7) is run in a dedicated sweep row — assertion: deterministic gates hold; LLM critic may be biased but its blocker equivalent is already surfaced by the gate.

### M9 Task Checklist

| # | Task | Build (files) | Behavior + edge cases | Feature | Verify | Status |
|---|------|---------------|----------------------|---------|--------|--------|
| 1 | Hermetic CI gate | Create `tests/field_test/hermetic/` — suite that runs the loop matrix, budget-audit, determinism, adversarial goal, fail-closed matrix with fake providers + fake store | No network, no paid LLM; flake-free by construction; runs on every push | F-67 | CI gate green after every push; 0 flakes in 20 runs | [#59](https://github.com/deghosal-2026/planner-critic-engine/issues/59) · - [x] (skipped — not required for v0.1.0) |
| 2 | Field-test CLI | Create `planner_critic/cli/field_test.py` + `field_test_harness.py` | `plancritic field-test run --goals DIR --output DIR` drives corpus; collects pass/fail per goal; writes JSON/markdown report; configurable provider | F-68 | CLI drives all cells; report emitted | [#60](https://github.com/deghosal-2026/planner-critic-engine/issues/60) · - [x] |
| 3 | Field-test harness | Create `src/planner_critic/field_test_harness.py` | Loads goals, runs engine, checks invariants, saves per-goal traces (plan JSON, findings, checks, pass/fail) | F-67, F-68 | Harness runs all 65 goals; summary written | [#61](https://github.com/deghosal-2026/planner-critic-engine/issues/61) · - [x] |
| 4 | Field test plan + 65 goal corpus | Write `docs/field-test/field-test-plan.md` + 65 goal JSON files + 65 assertion YAMLs across 10 domains | Corpus covers 9 ops domains + adversarial goals; each goal has invariant assertions | F-68 | Plan doc reviewed; 65 goals + 65 assertions on disk | [#62](https://github.com/deghosal-2026/planner-critic-engine/issues/62) · - [x] |
| 5 | Field-test report | Run `plancritic field-test run` against a real LLM; save `docs/field-test/FIELD_TEST_REPORT.md` | Matrix table: goal | expected (flaw caught/converge/escalate) | actual | pass/fail | — | report committed; all P0 cells pass | [#63](https://github.com/deghosal-2026/planner-critic-engine/issues/63) · - [ ] |
| 6 | Adversarial goal sweep | 6 adversarial goals in corpus (5 ADV + IR-07) | deterministic blocker holds → passes; LLM critic may fail but the gate is the authority | F-04, F-12 | adversarial cell passes | [#64](https://github.com/deghosal-2026/planner-critic-engine/issues/64) · - [x] |
| 7 | Critique-mode sweep — all heuristic | Capability C2 in field test plan; `--critique-mode heuristic-only` | `mode=heuristic-only` (gates only, no LLM): adversarial goal blocked by gates alone; loop escalates | F-04, F-67 | passes against real LLM when run with `--critique-mode` | [#74](https://github.com/deghosal-2026/planner-critic-engine/issues/74) · - [x] (covered by C2) |
| 8 | Critique-mode sweep — LLM + heuristic | Capability C2 in field test plan; `--critique-mode deterministic-first` | `mode=deterministic-first`: gates first, LLM critic on gate-surviving drafts only | F-04, F-10, F-11, F-67 | passes against real LLM when run with `--critique-mode` | [#75](https://github.com/deghosal-2026/planner-critic-engine/issues/75) · - [x] (covered by C2) |
| 9 | Critique-mode sweep — all LLM | Capability C2 in field test plan; `--critique-mode llm-every-revision` | `mode=llm-every-revision`: six-heuristic LLM critic on every revision incl. gate-blocked | F-04, F-10, F-11, F-67 | passes against real LLM when run with `--critique-mode` | [#76](https://github.com/deghosal-2026/planner-critic-engine/issues/76) · - [x] (covered by C2) |

### M9 Success Metrics

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

### M9 Exit Gate

- [ ] Code review passed (field-test harness + CLI)
- [ ] Coverage > 95% (no regression)
- [ ] Lint clean (ruff + mypy strict)
- [ ] Comments + docstrings in all code
- [ ] Hermetic CI gate green (flake-free, $0)
- [ ] Field-test report committed with all P0 cells passing
- [ ] Adversarial goal green; deterministic gates hold
- [ ] `plancritic field-test` driver functional end-to-end
- [ ] **Design docs authored:** D12 (field test design) + `FIELD_TEST_REPORT.md`

**Dependency:** M1–M8 (corpus from M7, adapters from M5, loop from M3, CLI from M6, containerized gate from M8). **Produces for M10:** field-test report (the release gate), deterministic confidence in the release.