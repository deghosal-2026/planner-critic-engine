# WBS — PlannerCritic Engine v0.2.2-M5: Field Test & Release

> Part of the v0.2.2 release. See [index](wbs-v0.2.2-index.md) for milestone overview and dependency graph.
>
> **Branch:** `rel-0.2.2` · **Milestone:** [v0.2.2-M5 Field Test & Release](https://github.com/deghosal-2026/planner-critic-engine/milestone/19)
>
> **Scope:** Repeat the full 170-goal field test + Docker integration test across all goals and scenarios. Validate all M1-M4 fixes with a hermetic CI regression sweep, operational benchmark, boundary-case evaluator, security oracle regression, docs sweep, and release coordination.

---

## Overview

M5 runs the full field test sweep after all M1-M4 work is merged. It validates that no fix introduced a regression, that all new features produce the expected verdicts, and that the engine is ready for release.

| Issue | Title | Area | Complexity |
|-------|-------|------|------------|
| #265 | Field test results v0.2.2 + regression gate sweep — hermetic CI | field-test | high |
| #266 | Docker integration test — full pipeline across all goals and scenarios | testing | medium |
| #267 | Operational benchmark — latency, reviewer burden, operator workload vs v0.2.1 baseline | testing | medium |
| #268 | Boundary-case evaluator — live-critic non-determinism measurement with M4 decision-context capture | testing | medium |
| #269 | Final quality gate — code review, lint, mypy, coverage >91% | quality | high |
| #270 | Docs sweep — README, CHANGELOG, release notes, API reference, M1-M4 documentation | docs | medium |
| #271 | Release coordination — tag v0.2.2, announcement, milestone closure | release | low |

---

## #265 — [v0.2.2-M5] Field test results v0.2.2 + regression gate sweep — hermetic CI

**Problem:** All M1-M4 fixes must be validated against the full 170-goal corpus. The field test must confirm that no fix introduced a regression and that all new features produce the expected verdicts.

**Scope:**
- Re-run all 170 goals across 40 domains
- Compare every verdict against the published v0.2.1 baseline
- Zero unexplained verdict deltas (all deltas attributable to M1-M4 changes or LLM non-determinism)
- Verify all M1-M4 issues are closed and their fixes are exercised

**Completion checklist:**
- [ ] 170/170 goals complete (no skips, no provider errors except documented transients)
- [ ] Balanced goals approved: 73/73 (100%)
- [ ] Strict goals escalated: 97/97 (100%) (minus any attributed deltas)
- [ ] Adversarial goals aborted: 11/11 (100%)
- [ ] Security oracle: 7/7 correct plans pass, 35/35 flawed variants blocked
- [ ] All verdict deltas vs v0.2.1 are attributable — zero unexplained
- [ ] M1-M4 fixes are confirmed exercised by the sweep
- [ ] Scorecard A: PASS
- [ ] Results committed under `docs/field-test/v0.2.2/`

---

## #266 — [v0.2.2-M5] Docker integration test — infrastructure + health checks

**Problem:** The Docker integration test verifies the containerized engine builds, starts, and serves requests correctly.

**Scope:**
- Build Docker image from the v0.2.2 release branch
- Verify Docker Compose topology (engine-http + engine-mcp) starts healthy
- Test CLI smoke commands (version, providers, critique)
- Test healthz endpoints (HTTP + MCP)
- Test HTTP and MCP wiring (plan, critique, escalate endpoints)
- **Caveat:** LLM-dependent tests (plan_vs_mlx, critique_vs_mlx, adversarial_goal) are disabled — they require a live LLM provider and are covered by the M5 field test sweep ($0.49, 170 goals). The Docker tests cover infrastructure only.

**Results:**
- 13 passed / 6 skipped (5 LLM-dependent, 1 no-plan-from-run)
- Image build: ✅
- Compose health: ✅
- CLI smoke: ✅
- HTTP/healthz: ✅
- MCP tools: ✅
- Escalation round-trip: ✅

**Completion checklist:**
- [x] Docker image builds without errors
- [x] Docker Compose integration test passes (engine + store + MCP server)
- [x] CI pipeline includes Docker build and integration test step
- [x] Docker test results published alongside field test results
- [x] Caveat documented: LLM-dependent tests disabled in Docker, covered by field test sweep

---

## #267 — [v0.2.2-M5] Operational benchmark — latency, reviewer burden, operator workload vs v0.2.1 baseline

**Problem:** M1-M4 changes may affect operational characteristics (latency, blocker counts, escalation rates). The v0.2.1 operational benchmark established baselines; v0.2.2 must re-run the same benchmark and compare.

**Metrics to compare:**

| Metric | v0.2.1 baseline | Target |
|--------|----------------|--------|
| Latency (approved) p50 | 13.86s | <= 13.86s |
| Latency (escalated) p50 | 27.82s | <= 27.82s |
| Mean blockers per goal | 2.58 | <= 2.58 |
| Mean advisories per goal | 1.86 | <= 1.86 |
| Escalation decisions per 100 goals | 58.0 | <= 58.0 |
| Mean LLM calls per goal | 1.4 | <= 1.4 |
| Median revisions to resolution | 1.0 | <= 1.0 |

**Completion checklist:**
- [ ] All 7 metrics measured and reported
- [ ] Any regression >10% flagged and investigated
- [ ] Operational benchmark script added to `docs/field-test/v0.2.2/scripts/`
- [ ] Results published alongside field test results

---

## #268 — [v0.2.2-M5] Boundary-case evaluator — live-critic non-determinism measurement with M4 decision-context capture

**Problem:** The v0.2.1 boundary evaluator measured critic non-determinism (label_flip_rate=1.0, evidence_drift_rate=1.0). M2 #242 adds decision-context capture (model version, temperature, prompt hash, tool-schema hash) and unsupported-evidence frequency metric. The v0.2.2 boundary evaluator must exercise these new capabilities.

**Metrics:**

| Metric | v0.2.1 | v0.2.2 target |
|--------|--------|---------------|
| label_flip_rate | 1.000 | recorded |
| evidence_drift_rate | 1.000 | recorded |
| family_migration_rate | 0.000 | 0.000 |
| underclaim_approvals | 0 | 0 |
| unsupported_evidence_frequency | not measured | reported |
| decision_context captured | model only | model + prompt + schema + temperature |

**Completion checklist:**
- [ ] All boundary cases run 5x through live critic
- [ ] Decision-context capture included in every trial record
- [ ] Unsupported-evidence frequency reported
- [ ] No underclaim_approvals (critical safety invariant)
- [ ] Results published alongside field test results

---

## #269 — [v0.2.2-M5] Final quality gate — code review, lint, mypy, coverage >91%

**Problem:** Before shipping v0.2.2, all M1-M4 code must pass the standard quality gates: code review, lint, mypy, and coverage threshold.

**Scope:**
- Full code review of all M1-M4 changes
- Pre-commit hooks pass (ruff, mypy, pytest)
- Coverage >91% (matching v0.2.1 threshold)
- All 1295+ deterministic tests pass
- 0 regressions in the deterministic test suite

**Completion checklist:**
- [ ] Code review: all M1-M4 changes reviewed (no P1/P2 findings)
- [ ] Lint: `ruff check .` passes clean
- [ ] Type check: `mypy src/` passes clean
- [ ] Coverage: `pytest --cov=src/ --cov-report=term` reports >91%
- [ ] Deterministic suite: 1295+ tests pass (0 failures)
- [ ] Test count matches CI output (fix #263 discrepancy)

---

## #270 — [v0.2.2-M5] Docs sweep — README, CHANGELOG, release notes, API reference, M1-M4 documentation

**Problem:** New features in M1-M4 require documentation updates. The release notes must cover all changes, and the failure-mode register must be updated with new assumptions.

**Scope:**
- README: update version reference, add new features summary
- CHANGELOG: add v0.2.2 entry
- Release notes: create `docs/reference/release-notes-v0.2.2.md`
- API reference: update for any new/modified interfaces
- Failure-mode register: add new rows for M1-M4 intentional trade-offs
- Field test results: create `docs/field-test/v0.2.2/field-test-results-v0.2.2.md`
- Fix #246 and #247 in the process

**Completion checklist:**
- [ ] README points to v0.2.2
- [ ] CHANGELOG has v0.2.2 entry
- [ ] Release notes created and reviewed
- [ ] Failure-mode register updated
- [ ] Field test results document published
- [ ] #246 and #247 closed

---

## #271 — [v0.2.2-M5] Release coordination — tag v0.2.2, announcement, milestone closure

**Problem:** Coordinate the final release activities for v0.2.2: version bump, tag, PyPI release, and announcement.

**Prerequisites:**
- All M1-M4 issues are closed
- M5 field test passes
- Quality gate passes
- Docs sweep complete

**Completion checklist:**
- [ ] v0.2.2 tagged on GitHub
- [ ] v0.2.2 published on PyPI
- [ ] GitHub release created with release notes
- [ ] All v0.2.2 milestones closed
- [ ] Announcement published

---

## M5 Closure Gate

Before M5 closes, the following must be true:

### Standard milestone exit gate
- [ ] **Code review**: all M5 changes reviewed, no P1/P2 findings
- [ ] **Lint clean**: `ruff check src/ tests/` + `ruff format --check` 0 errors
- [ ] **Type check**: `mypy --strict src/ tests/` 0 errors
- [ ] **Test coverage**: `pytest --cov=src/ --cov-report=term` reports >90%
- [ ] **Documents updated**: all docs affected by M5 changes are current (field test results, benchmark scripts, release notes)
- [ ] **Clean checkin**: no debug code, no print statements, no TODOs

### M5-specific closure
- [ ] All 7 issues closed with evidence
- [ ] Field test green: 170/170 goals, 0 true failures, Scorecard A PASS
- [ ] Docker integration green
- [ ] Operational benchmark within 10% of v0.2.1 baselines
- [ ] Boundary-case evaluator: zero underclaim_approvals
- [ ] Quality gate: code review clean, lint clean, mypy clean, coverage >91%
- [ ] All docs current and consistent
- [ ] Release candidate ready for M6 final readiness gate