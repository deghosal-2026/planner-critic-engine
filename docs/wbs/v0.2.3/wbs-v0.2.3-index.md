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
| **M1** | Corrections + Features | v0.2.3-M1 | [#278](https://github.com/deghosal-2026/planner-critic-engine/issues/278), [#279](https://github.com/deghosal-2026/planner-critic-engine/issues/279), [#296](https://github.com/deghosal-2026/planner-critic-engine/issues/296), [#297](https://github.com/deghosal-2026/planner-critic-engine/issues/297), [#298](https://github.com/deghosal-2026/planner-critic-engine/issues/298) | Planned |
| **M2** | Field Test | v0.2.3-M2 | [#281–#289](https://github.com/deghosal-2026/planner-critic-engine/issues/281) | Planned |
| **M3** | Release Readiness | v0.2.3-M3 | [#290–#295](https://github.com/deghosal-2026/planner-critic-engine/issues/290) | Planned |

## 2. Dependency Graph

```
M1 (Corrections + Features)  ── fixes F-20, F-14, DecisionContext + Gate Canary
  └──► M2 (Field Test)      ── needs M1 merged; runs 183-goal sweep
        └──► M3 (Release)   ── quality gate + docs + packaging + ship
```

## 3. M1 — Corrections + Features (#278, #279, #296, #297, #298)

Scope: three community-raised correction issues from the dev.to series, plus the planned Gate Canary and Frozen-Claim Protocol. Each ships with tests.

| Issue | Title | Deliverable | Success Criterion | Source |
|-------|-------|-------------|-------------------|--------|
| [#278](https://github.com/deghosal-2026/planner-critic-engine/issues/278) | Deterministic Gate Canary | Per-gate health check for each blocker class | `plancritic gates canary --check` exits 1 on any silent regression; 10 canary fixtures; integrated into eval sweep | [Artjoms Stukans](https://dev.to/artyomsv/comment/3dlpo) |
| [#279](https://github.com/deghosal-2026/planner-critic-engine/issues/279) | Extended Frozen-Claim Protocol | Denominator completeness, artifact selection, determinism boundaries | Documentation complete; protocol extended per spec | — |
| [#296](https://github.com/deghosal-2026/planner-critic-engine/issues/296) | F-20 — Deterministic-corruption blind spot | Transit-integrity check; redaction layer validated | Output JSON fields match pre-redaction values modulo known patterns; failure register updated | [Antonio Lopes Correia](https://dev.to/tonal/comment/3dmlo) |
| [#297](https://github.com/deghosal-2026/planner-critic-engine/issues/297) | F-14 regression — approving_authority dormant on all shipped surfaces | approving_authority bound from stored AcceptanceContract on all 3 surfaces; MCP server passes principal | PermissionError fires from CLI/HTTP/MCP; F-14 status back to Closed | [Antonio Lopes Correia](https://dev.to/tonal/comment/3dmll) |
| [#298](https://github.com/deghosal-2026/planner-critic-engine/issues/298) | DecisionContext metadata not populated | DecisionContext populated with real values from registry/transport | Trial records have model_id, version, temperature, prompt hash, tool-schema hash; convention documented | [Peter](https://dev.to/peterbuildssecure/comment/3dml0) |

## 4. M2 — Field Test (#281–#289)

Execution order: #281 plan → #282 download corpus → #283 write scripts → #284 execute sweep → #285 fix issues → #286 capture learnings → #287 update report → #288 closure.

| Issue | Scope | Gate to close |
|-------|-------|---------------|
| [#281](https://github.com/deghosal-2026/planner-critic-engine/issues/281) | Field test plan — scope, corpus, pass/fail criteria | Plan published; scope includes 183 goals + Gate Canary verification |
| [#282](https://github.com/deghosal-2026/planner-critic-engine/issues/282) | Download corpus for field test | Corpus downloaded; all 183 goals available locally |
| [#283](https://github.com/deghosal-2026/planner-critic-engine/issues/283) | Write field test scripts | `bench_gate_canary`, `bench_release_verify` written; runners updated |
| [#284](https://github.com/deghosal-2026/planner-critic-engine/issues/284) | Execute field test sweep | 183 goals complete; Gate Canary passes; release verification green |
| [#285](https://github.com/deghosal-2026/planner-critic-engine/issues/285) | Fix issues found during field test | All regression issues fixed; root causes documented |
| [#286](https://github.com/deghosal-2026/planner-critic-engine/issues/286) | Capture learnings from field test | Learnings documented in `docs/field-test/v0.2.3/learnings.md` |
| [#287](https://github.com/deghosal-2026/planner-critic-engine/issues/287) | Update field test report | Report committed to `docs/field-test/v0.2.3/` |
| [#288](https://github.com/deghosal-2026/planner-critic-engine/issues/288) | Closure | All tests pass; lint strict; field test complete |

## 5. M3 — Release Readiness (#290–#295)

Strict sequential order: #290 docs → #291 packaging → #292 tags → #293 quality gate → #294 security → #295 tests.

| Issue | Scope | Gate to close |
|-------|-------|---------------|
| [#290](https://github.com/deghosal-2026/planner-critic-engine/issues/290) | Docs sweep | README, CHANGELOG, release notes, API reference, learnings all updated |
| [#291](https://github.com/deghosal-2026/planner-critic-engine/issues/291) | Packaging & PyPI release | Dist builds clean; Dockerfile pinned; PyPI v0.2.3 live |
| [#292](https://github.com/deghosal-2026/planner-critic-engine/issues/292) | Release tags and milestone closure | Git tag v0.2.3; GitHub release published; all milestones closed |
| [#293](https://github.com/deghosal-2026/planner-critic-engine/issues/293) | Closure — final quality gate | Code review; lint strict; coverage > 90%; merge to main |
| [#294](https://github.com/deghosal-2026/planner-critic-engine/issues/294) | Security scan | truffleHog clean; dependency audit clean; secret detection pass |
| [#295](https://github.com/deghosal-2026/planner-critic-engine/issues/295) | All tests passing | Full deterministic suite green; field test confirmed green |

## 6. Version Bump Checklist (applied by #291)

| Location | Change |
|----------|--------|
| `pyproject.toml` | `version = "0.2.2"` → `"0.2.3"` |
| `src/planner_critic/__init__.py` | `__version__ = "0.2.2"` → `"0.2.3"` |
| `Dockerfile` | pinned wheel filename `planner_critic-0.2.2` → `0.2.3` |
| `README.md` | PyPI badge + status line |
| `CHANGELOG.md` | new `## v0.2.3` entry |
| `docs/reference/release-notes-v0.2.3.md` | new file, following v0.2.2 structure |