# WBS — PlannerCritic Engine v0.2.3 (Index)

> Work breakdown for the **v0.2.3 patch release** — fixes three community-raised correction issues (F-20 deterministic-corruption, F-14 regression, DecisionContext) alongside the planned Gate Canary and Frozen-Claim Protocol. All work lands on branch **`feature-v0.2.3`** until release.
>
> **Author:** Debashish Ghosal · **Date:** 2026-08-29 · **Status:** Planned (issues filed)
>
> **GitHub milestones:** [v0.2.3-M1](https://github.com/deghosal-2026/planner-critic-engine/milestone/35) · [v0.2.3-M2](https://github.com/deghosal-2026/planner-critic-engine/milestone/36) · [v0.2.3-M3](https://github.com/deghosal-2026/planner-critic-engine/milestone/37). Issue bodies carry full context; this index carries only the tracking checklists and success criteria.

---

## 1. Milestone Overview

> **Sequencing rationale:** M1 combines the 3 community-raised corrections with the planned v0.2.3 features. M2 runs the field test sweep after M1 is merged. M3 is the final release readiness gate.

| M# | Name | GitHub milestone | Issues | Status |
|----|------|------------------|--------|--------|
| **M1** | Corrections + Features | v0.2.3-M1 | [#278](https://github.com/deghosal-2026/planner-critic-engine/issues/278), [#279](https://github.com/deghosal-2026/planner-critic-engine/issues/279), [#296](https://github.com/deghosal-2026/planner-critic-engine/issues/296), [#297](https://github.com/deghosal-2026/planner-critic-engine/issues/297), [#298](https://github.com/deghosal-2026/planner-critic-engine/issues/298) | ✅ Complete |
| **M2** | Field Test | v0.2.3-M2 | [#281–#289](https://github.com/deghosal-2026/planner-critic-engine/issues/281) | ✅ Complete |
| **M3** | Release Readiness | v0.2.3-M3 | [#290–#295](https://github.com/deghosal-2026/planner-critic-engine/issues/290) | 🔄 In progress |

## 2. Dependency Graph

```
M1 (Corrections + Features)  ── fixes F-20, F-14, DecisionContext + Gate Canary
  └──► M2 (Field Test)      ── needs M1 merged; runs 183-goal sweep
        └──► M3 (Release)   ── quality gate + docs + packaging + ship
```

## 3. M1 — Corrections + Features (#278, #279, #296, #297, #298)

Scope: three community-raised correction issues from the dev.to series, plus the planned Gate Canary and Frozen-Claim Protocol. Each ships with tests.

### #278 — Deterministic Gate Canary

| Dimension | Details |
|-----------|---------|
| **Tests needed** | 10 canary `(good_plan, bad_plan)` fixtures in `tests/canary/` (one per gate class); `test_canary_check.py` — verifies `--check` exits 1 on deliberate gate break; `test_canary_report.py` — verifies `--report` JSON format; `test_canary_integration.py` — verifies eval sweep appends canary results; `test_canary_ci.py` — regression-detection precision test (break each gate, confirm canary catches it); CI integration test for canary fixture rot detection |
| **Docs to update** | `docs/reference/cli.md` — `plancritic gates canary` subcommand; `docs/field-test/v0.2.3/field-test-results.md` — canary results format; `CHANGELOG.md`; `docs/reference/release-notes-v0.2.3.md` |
| **Source** | [Artjoms Stukans](https://dev.to/artyomsv/comment/3dlpo) |

### #279 — Extended Frozen-Claim Protocol

| Dimension | Details |
|-----------|---------|
| **Tests needed** | `test_release_verify_strict.py` — validates denominator completeness, artifact selection freeze, determinism boundary annotations; test that existing frozen-claim protocol backward-compatible; test that `plancritic release verify --strict` rejects missing determinism annotation |
| **Docs to update** | `docs/release/release-protocol.md` — denominator completeness requirement, artifact selection freeze, determinism boundary documentation; `docs/field-test/v0.2.3/field-test-plan.md` — updated template sections; `CHANGELOG.md` |

### #296 — F-20 Deterministic-Corruption Blind Spot

| Dimension | Details |
|-----------|---------|
| **Tests needed** | `test_transit_integrity.py` — boundary evaluator transit-integrity check; test that redaction does not corrupt numeric JSON fields; test that output JSON fields match pre-redaction values modulo known redaction patterns; test that redaction touching a wrong field causes evaluator failure |
| **Docs to update** | `docs/reference/failure-modes.md` (already done — F-20 row added); design note in `docs/design/` — deterministic silence vs non-deterministic noise failure class distinction; `CHANGELOG.md` |
| **Source** | [Antonio Lopes Correia](https://dev.to/tonal/comment/3dmlo) |

### #297 — F-14 Regression (approving_authority)

| Dimension | Details |
|-----------|---------|
| **Tests needed** | `test_authority_cli.py` — end-to-end PermissionError from CLI entry point; `test_authority_http.py` — end-to-end PermissionError from HTTP entry point; `test_authority_mcp.py` — end-to-end PermissionError from MCP entry point (both mcp_tools and mcp.py wrapper); `test_shared_escalation_manager.py` — shared helper function routes approving_authority correctly; `test_mcp_principal.py` — MCP tool schemas include principal and handlers forward it |
| **Docs to update** | `docs/reference/failure-modes.md` — F-14 status back to Closed; `docs/reference/api.md` — approving_authority documented on CLI/HTTP/MCP surfaces; `CHANGELOG.md` |
| **Source** | [Antonio Lopes Correia](https://dev.to/tonal/comment/3dmll) |

### #298 — DecisionContext Not Populated

| Dimension | Details |
|-----------|---------|
| **Tests needed** | `test_decision_context_populated.py` — stub critic test verifying DecisionContext in trial record comes from harness call parameters, not from critic response; test that when provider transport records model info in response, it's stored as separate `response_model_id` field |
| **Docs to update** | `docs/design/decision-context.md` — convention documentation that DecisionContext fields must be sourced from harness's own call parameters; `docs/reference/api.md` — DecisionContext parameters on boundary evaluator; `CHANGELOG.md` |
| **Source** | [Peter](https://dev.to/peterbuildssecure/comment/3dml0) |

### M1 Issue Summary

| Issue | Title | Parent | Tests | Docs | Status |
|-------|-------|--------|-------|------|--------|
| [#278](https://github.com/deghosal-2026/planner-critic-engine/issues/278) | Deterministic Gate Canary | — | 10 canary fixtures + 4 test files | CLI docs + field test report | 🔄 Open |
| [#299](https://github.com/deghosal-2026/planner-critic-engine/issues/299) | Tests — Gate Canary fixtures and integration | #278 | 4 test files | — | 🔄 Open |
| [#304](https://github.com/deghosal-2026/planner-critic-engine/issues/304) | Docs — CLI reference for Gate Canary | #278 | — | cli.md | 🔄 Open |
| [#279](https://github.com/deghosal-2026/planner-critic-engine/issues/279) | Extended Frozen-Claim Protocol | — | 3 test files | Release protocol + field test plan | 🔄 Open |
| [#303](https://github.com/deghosal-2026/planner-critic-engine/issues/303) | Tests — Frozen-Claim Protocol strict mode | #279 | 1 test file | — | 🔄 Open |
| [#308](https://github.com/deghosal-2026/planner-critic-engine/issues/308) | Docs — release protocol additions | #279 | — | release-protocol.md | 🔄 Open |
| [#296](https://github.com/deghosal-2026/planner-critic-engine/issues/296) | F-20 — Deterministic-corruption | — | 3 test files | Failure-mode register + design note | 🔄 Open |
| [#300](https://github.com/deghosal-2026/planner-critic-engine/issues/300) | Tests — F-20 transit-integrity check | #296 | 1 test file | — | 🔄 Open |
| [#305](https://github.com/deghosal-2026/planner-critic-engine/issues/305) | Docs — deterministic silence design note | #296 | — | design note | 🔄 Open |
| [#297](https://github.com/deghosal-2026/planner-critic-engine/issues/297) | F-14 regression — approving_authority | — | 5 test files | Failure-mode register + API docs | 🔄 Open |
| [#301](https://github.com/deghosal-2026/planner-critic-engine/issues/301) | Tests — F-14 enforcement on all surfaces | #297 | 5 test files | — | 🔄 Open |
| [#307](https://github.com/deghosal-2026/planner-critic-engine/issues/307) | Docs — API reference updates | #297, #298 | — | api.md | 🔄 Open |
| [#298](https://github.com/deghosal-2026/planner-critic-engine/issues/298) | DecisionContext population | — | 2 test files | Design convention doc + API docs | 🔄 Open |
| [#302](https://github.com/deghosal-2026/planner-critic-engine/issues/302) | Tests — DecisionContext population | #298 | 1 test file | — | 🔄 Open |
| [#306](https://github.com/deghosal-2026/planner-critic-engine/issues/306) | Docs — DecisionContext sourcing convention | #298 | — | design/decision-context.md | 🔄 Open |

### M1 Exit Gate

- [ ] All 15 issues closed (5 parent + 10 sub-tasks)
- [ ] 17+ new tests passing (all deterministic, zero LLM calls)
- [ ] Full deterministic test suite green
- [ ] Docker integration tests pass (if applicable)
- [ ] Ruff clean, mypy strict clean
- [ ] Test coverage > 90%
- [ ] All 6 docs files updated (failure-modes, CLI, API, release-protocol, design note, CHANGELOG)
- [ ] Code review completed
- [ ] Merged to `feature-v0.2.3`

## 4. M2 — Field Test (#281–#285, #288, #309–#316)

> **What changed from v0.2.2:** Four new verification dimensions. (1) Gate Canary — run `plancritic gates canary --check` before/after sweep; assert all 10 gates fire. (2) Transit-integrity check — verify redaction does not corrupt numeric JSON in boundary evaluator. (3) Frozen-Claim Protocol extended — `plancritic release verify --strict` with denominator completeness, artifact freeze, determinism boundaries. (4) DecisionContext population — verify trial records have populated metadata, not "unknown". (5) Comparison table and narrative documenting delta vs v0.2.2.

Execution order: #309 plan → #282 corpus → #310 fixtures → #311 scripts → #284 execute → #285 fix → #314 comparison → #315 conclusions → #316 report creation → #312 learnings → #288 closure.

| Issue | Title | Scope | New fixtures / scripts needed | Gate to close |
|-------|-------|-------|-------------------------------|---------------|
| [#309](https://github.com/deghosal-2026/planner-critic-engine/issues/309) | Write field test plan — scope, corpus, pass/fail criteria | Updated plan reflecting 4 new verification dimensions + comparison methodology | — | Plan published; pass/fail criteria include Gate Canary (10/10), transit-integrity (0 corruption), authority enforcement (3 surfaces), DecisionContext (0 unknown), comparison delta documented |
| [#282](https://github.com/deghosal-2026/planner-critic-engine/issues/282) | Download corpus for field test | 183-goal corpus download | — | Corpus available locally |
| [#310](https://github.com/deghosal-2026/planner-critic-engine/issues/310) | Create field test fixtures — Gate Canary, transit-integrity, authority | 10 gate canary pairs (tests/canary/), transit-integrity fixtures (3 cases), authority enforcement contracts, DecisionContext stubs | 10 canary fixtures, 3 transit-integrity fixtures, 3+ authority contracts, 1 stub critic | All fixtures created and validated |
| [#311](https://github.com/deghosal-2026/planner-critic-engine/issues/311) | Write bench scripts — bench_gate_canary, bench_release_verify, bench_transit_integrity | 3 new bench scripts + updates to existing runners | `bench_gate_canary.py`, `bench_release_verify.py`, `bench_transit_integrity.py`; updated `bench_live_boundary.py` with DecisionContext | All scripts written; seam assertions at new boundaries |
| [#284](https://github.com/deghosal-2026/planner-critic-engine/issues/284) | Execute field test sweep — 183 goals, Gate Canary, release verification | Full sweep with all new verification | — | 183 goals complete; Gate Canary 10/10; transit-integrity 0 events; verify --strict pass |
| [#285](https://github.com/deghosal-2026/planner-critic-engine/issues/285) | Fix issues found during field test execution | Regression fixes | — | All issues fixed; root causes documented |
| [#314](https://github.com/deghosal-2026/planner-critic-engine/issues/314) | Create comparison table — v0.2.3 vs v0.2.2 baseline | Per-metric delta table across all dimensions | — | Comparison table published; each delta has root cause documented |
| [#315](https://github.com/deghosal-2026/planner-critic-engine/issues/315) | Update field test report — conclusions and comparison narrative | Conclusion sections: executive summary, findings, regressions, improvements, new capabilities | — | Narrative written; honest assessment of better/worse/unchanged |
| [#316](https://github.com/deghosal-2026/planner-critic-engine/issues/316) | Create FIELD_TEST_REPORT.md and learnings.md for v0.2.3 | Full report document with all sections | — | Report committed to `docs/field-test/v0.2.3/` |
| [#312](https://github.com/deghosal-2026/planner-critic-engine/issues/312) | Capture learnings from field test | Learnings on Gate Canary, transit-integrity, authority, DecisionContext, comparison process | — | `docs/field-test/v0.2.3/learnings.md` written |
| [#288](https://github.com/deghosal-2026/planner-critic-engine/issues/288) | Closure — run all tests, lint strict, close field test | M2 exit gate | — | Full deterministic suite green; Docker tests pass; ruff + mypy strict clean; coverage > 90%; field test report complete; all M1 changes merged and verified |

### M2 Exit Gate

- [ ] All 11 issues closed
- [ ] All 4 new verification dimensions pass (Gate Canary 10/10, transit-integrity 0 events, authority 3 surfaces, DecisionContext 0 unknown)
- [ ] Comparison table published — every metric delta documented against v0.2.2
- [ ] Conclusion narrative written — honest better/worse/unchanged assessment
- [ ] 10 canary fixtures + 3 transit-integrity fixtures + 3 bench scripts committed
- [ ] Full deterministic test suite green
- [ ] Docker integration tests pass
- [ ] Ruff clean, mypy strict clean
- [ ] Test coverage > 90%
- [ ] Field test report published at `docs/field-test/v0.2.3/`
- [ ] Learnings documented
- [ ] Code review completed

## 5. M3 — Release Readiness (#290–#295, #317–#327)

> **Expanded from v0.2.2:** Security scans now include bandit + gitleaks + truffleHog + pip-audit. Coverage gate > 90%. Lint gate (ruff + mypy strict). Full docs sweep. Vault article updates and dev.to publishing for all unblocked articles.

Strict sequential order: security scans → tests + coverage + lint → docs sweep → vault/articles → packaging → release tags → merge.

| Issue | Title | Scope | Gate to close |
|-------|-------|-------|---------------|
| [#317](https://github.com/deghosal-2026/planner-critic-engine/issues/317) | Security scan — bandit static analysis | bandit on src/ and scripts/ | 0 new high-severity issues |
| [#318](https://github.com/deghosal-2026/planner-critic-engine/issues/318) | Security scan — gitleaks secret detection | gitleaks on repo (exclude results/) | 0 verified secrets in committed code |
| [#319](https://github.com/deghosal-2026/planner-critic-engine/issues/319) | Security scan — truffleHog, dependency audit | truffleHog filesystem + pip-audit | 0 verified secrets; 0 new dependency vulns |
| [#320](https://github.com/deghosal-2026/planner-critic-engine/issues/320) | All tests passing — deterministic, Docker, field test | Full test suite across all dimensions | 100% pass; Docker green; field test 0 true failures |
| [#321](https://github.com/deghosal-2026/planner-critic-engine/issues/321) | Coverage gate — test coverage > 90% | pytest-cov across src/ | > 90% line coverage; gap analysis if below |
| [#322](https://github.com/deghosal-2026/planner-critic-engine/issues/322) | Lint gate — ruff + mypy strict clean | ruff check + mypy strict | Zero errors on v0.2.3 changes |
| [#323](https://github.com/deghosal-2026/planner-critic-engine/issues/323) | Docs sweep — README, CHANGELOG, release notes, API, failure-modes, CLI | All 6 doc files updated | No stale contradictions; cross-references consistent |
| [#326](https://github.com/deghosal-2026/planner-critic-engine/issues/326) | Update published articles in vault and dev.to with v0.2.3 findings | 4 planner-critic articles unblocked; vault updated; dev.to banners added | PUBLISH BLOCKED notes removed; v0.2.3 banners added; vault committed to main |
| [#324](https://github.com/deghosal-2026/planner-critic-engine/issues/324) | Packaging & PyPI release — build, dist, Dockerfile pin, upload | sdist + wheel + Dockerfile + PyPI | pip install adversarial-debate==0.2.3 verified |
| [#325](https://github.com/deghosal-2026/planner-critic-engine/issues/325) | Release tags and milestone closure — git tag, GitHub release | git tag v0.2.3 + GitHub release + close milestones | All milestones closed; announcement drafted |
| [#327](https://github.com/deghosal-2026/planner-critic-engine/issues/327) | Closure — final quality gate: merge to main | code review + all checks + merge | feature-v0.2.3 merged to main; branch deleted |

### M3 Exit Gate

- [ ] All 11 issues closed
- [ ] All 4 security scans clean (bandit, gitleaks, truffleHog, pip-audit)
- [ ] All 3 test gates pass (deterministic 100%, Docker green, field test 0 true failures)
- [ ] Coverage > 90%
- [ ] Lint strict clean (ruff + mypy)
- [ ] All docs current (README, CHANGELOG, release notes, API, failure-modes, CLI)
- [ ] All 4 blocked articles updated and unblocked on dev.to
- [ ] Vault committed to main
- [ ] PyPI v0.2.3 live
- [ ] GitHub release v0.2.3 published
- [ ] feature-v0.2.3 merged to main
- [ ] feature-v0.2.3 branch deleted

## 6. Global Exit Gates (every milestone)

- [ ] Full deterministic test suite green (100% pass)
- [ ] Docker integration tests pass (if applicable)
- [ ] Ruff clean, mypy strict clean
- [ ] Test coverage > 90%
- [ ] All relevant docs updated (failure-modes, CLI, API, release-protocol, design notes, CHANGELOG)
- [ ] Code review completed on all new code
- [ ] Zero paid-LLM calls in CI (deterministic tests only)

## 7. Version Bump Checklist (applied by #291)

| Location | Change |
|----------|--------|
| `pyproject.toml` | `version = "0.2.2"` → `"0.2.3"` |
| `src/planner_critic/__init__.py` | `__version__ = "0.2.2"` → `"0.2.3"` |
| `Dockerfile` | pinned wheel filename `planner_critic-0.2.2` → `0.2.3` |
| `README.md` | PyPI badge + status line |
| `CHANGELOG.md` | new `## v0.2.3` entry |
| `docs/reference/release-notes-v0.2.3.md` | new file, following v0.2.2 structure |