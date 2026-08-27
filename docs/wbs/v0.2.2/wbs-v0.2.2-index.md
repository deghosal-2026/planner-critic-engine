# WBS — PlannerCritic Engine v0.2.2 (Index)

> Work breakdown for the **v0.2.2 patch release** — community-driven hardening from the dev.to PlannerCritic series (Parts 4–9 comment threads, Aug 24–26), resolved across six milestones (M1–M6). All work lands on branch **`rel-0.2.2`** until release.
>
> **Author:** Debashish Ghosal · **Date:** 2026-08-26 · **Status:** Planned (issues filed)
>
> **GitHub milestones:** [M1 Foundation Corrections](https://github.com/deghosal-2026/planner-critic-engine/milestone/15) · [M2 Gate & Schema Hardening](https://github.com/deghosal-2026/planner-critic-engine/milestone/16) · [M3 Security & Injection Resistance](https://github.com/deghosal-2026/planner-critic-engine/milestone/17) · [M4 Operational & Audit](https://github.com/deghosal-2026/planner-critic-engine/milestone/18) · [M5 Field Test & Release](https://github.com/deghosal-2026/planner-critic-engine/milestone/19) · [M6 Release Readiness](https://github.com/deghosal-2026/planner-critic-engine/milestone/20). Issue bodies carry full context; this index carries only the tracking checklists and success criteria.

---

## 1. Milestone Overview

> **Sequencing rationale:** foundation-first, then gates, then security, then operational, then field test, then release. M1 fixes docs and test-infra issues from v0.2.1 before any new behavior lands. M2 and M3 are independent gate/schema/security work that can land in parallel after M1. M4 depends on M2's schema changes (finding contract, decision-context capture). M5 runs the full field test sweep only after M1–M4 are merged. M6 is the final release readiness gate.

| M# | Name | GitHub milestone | Issues | Status |
|----|------|------------------|--------|--------|
| **M1** | [Foundation Corrections](https://github.com/deghosal-2026/planner-critic-engine/milestone/15) | v0.2.2-M1 | [#246–#248](https://github.com/deghosal-2026/planner-critic-engine/issues/246), [#263](https://github.com/deghosal-2026/planner-critic-engine/issues/263), [#264](https://github.com/deghosal-2026/planner-critic-engine/issues/264) | Planned |
| **M2** | [Gate & Schema Hardening](https://github.com/deghosal-2026/planner-critic-engine/milestone/16) | v0.2.2-M2 | [#242–#245](https://github.com/deghosal-2026/planner-critic-engine/issues/242), [#255](https://github.com/deghosal-2026/planner-critic-engine/issues/255) | Planned |
| **M3** | [Security & Injection Resistance](https://github.com/deghosal-2026/planner-critic-engine/milestone/17) | v0.2.2-M3 | [#238](https://github.com/deghosal-2026/planner-critic-engine/issues/238), [#249](https://github.com/deghosal-2026/planner-critic-engine/issues/249), [#253](https://github.com/deghosal-2026/planner-critic-engine/issues/253), [#256](https://github.com/deghosal-2026/planner-critic-engine/issues/256), [#258](https://github.com/deghosal-2026/planner-critic-engine/issues/258), [#259](https://github.com/deghosal-2026/planner-critic-engine/issues/259), [#260](https://github.com/deghosal-2026/planner-critic-engine/issues/260) | Planned |
| **M4** | [Operational & Audit](https://github.com/deghosal-2026/planner-critic-engine/milestone/18) | v0.2.2-M4 | [#250](https://github.com/deghosal-2026/planner-critic-engine/issues/250), [#251](https://github.com/deghosal-2026/planner-critic-engine/issues/251), [#252](https://github.com/deghosal-2026/planner-critic-engine/issues/252), [#254](https://github.com/deghosal-2026/planner-critic-engine/issues/254), [#257](https://github.com/deghosal-2026/planner-critic-engine/issues/257), [#261](https://github.com/deghosal-2026/planner-critic-engine/issues/261), [#262](https://github.com/deghosal-2026/planner-critic-engine/issues/262) | Planned |
| **M5** | [Field Test & Release](https://github.com/deghosal-2026/planner-critic-engine/milestone/19) | v0.2.2-M5 | [#265–#271](https://github.com/deghosal-2026/planner-critic-engine/issues/265) | Planned |
| **M6** | [Release Readiness](https://github.com/deghosal-2026/planner-critic-engine/milestone/20) | v0.2.2-M6 | [#272–#277](https://github.com/deghosal-2026/planner-critic-engine/issues/272) | Planned |

## 2. Dependency Graph

```
M1 (Foundation Corrections)  ── docs + test-infra fixes; no behavior changes
  ├──► M2 (Gate & Schema)    ── independent gates and schema work
  ├──► M3 (Security)        ── independent injection/securitiy hardening
  │         └──► M4 (Operational)  ── needs M2 schema (finding contract, decision-context)
  └──► M5 (Field Test)      ── needs M1–M4 merged
        └──► M6 (Release)   ── quality gate + docs + packaging + ship
```

## 3. M1 — Foundation Corrections (#246–#248, #263, #264)

Scope rule: docs fixes, test-infrastructure corrections, and quick patches to v0.2.1 release artifacts. No new behavior, no schema changes.

| Issue | Deliverable | Closes when (success criterion) | Status |
|-------|-------------|----------------------------------|--------|
| [#246](https://github.com/deghosal-2026/planner-critic-engine/issues/246) | Fix "Zero True Failures" contradiction in v0.2.1 field test report | Scorecard B True Fail = 1 correctly reflected in prose; no contradiction between summary and detail | Planned |
| [#247](https://github.com/deghosal-2026/planner-critic-engine/issues/247) | Fix oscillation count inconsistency (3 vs 5) | Release doc and results artifact agree on `plan_oscillation_detected` count; root cause documented | Planned |
| [#248](https://github.com/deghosal-2026/planner-critic-engine/issues/248) | Remove 75 pytest-cov artifacts from src/ | Clean `git status` under `src/planner_critic/` — no `.py,cover` artifacts committed; `.gitignore` updated | Planned |
| [#263](https://github.com/deghosal-2026/planner-critic-engine/issues/263) | Fix 1294/1295 test count discrepancy | Root cause identified; CI run on clean checkout shows documented test count matching docs; flaky test isolated or fixed | Planned |
| [#264](https://github.com/deghosal-2026/planner-critic-engine/issues/264) | Failure-origin taxonomy | Taxonomy defined and documented; all 41 bugs from v0.1.0–v0.2.1 retrofitted with first-detectable layer; heatmap published | Planned |

## 4. M2 — Gate & Schema Hardening (#242–#245, #255)

Scope rule: deterministic gate improvements and schema evolution. Each ships with a regression test that fails on pre-fix code.

| Issue | Deliverable | Closes when (success criterion) | Status |
|-------|-------------|----------------------------------|--------|
| [#242](https://github.com/deghosal-2026/planner-critic-engine/issues/242) | Live-boundary runner decision-context capture | Every trial records model id, version, temperature, system-prompt hash, tool-schema hash; unsupported-evidence frequency reported as separate metric | Planned |
| [#243](https://github.com/deghosal-2026/planner-critic-engine/issues/243) | Machine-actionable finding contract | Findings carry edge-level targeting, observed-state field, evidence references, schema versioning; precondition snapshot retained for replay attribution | Planned |
| [#244](https://github.com/deghosal-2026/planner-critic-engine/issues/244) | Runtime precondition verification on by default | Gate ships as fail-closed (not probe-only); corpus regression green; migration path documented for existing deployments | Planned |
| [#245](https://github.com/deghosal-2026/planner-critic-engine/issues/245) | Typed rollback restoration contracts | RollbackStep carries declarative restored-state and restoration-evidence fields; gate consumes declaration when present, derives as today when absent; migration path from advisory to required | Planned |
| [#255](https://github.com/deghosal-2026/planner-critic-engine/issues/255) | Requirement-traceability gate | Every plan step traces back to an acceptance criterion; orphan tasks flagged as blockers; corpus regression with zero false positives on clean plans | Planned |

## 5. M3 — Security & Injection Resistance (#238, #249, #253, #256, #258, #259, #260)

Scope rule: adversarial and injection hardening. All injection tests must pass with 100% escalation rate.

| Issue | Deliverable | Closes when (success criterion) | Status |
|-------|-------------|----------------------------------|--------|
| [#238](https://github.com/deghosal-2026/planner-critic-engine/issues/238) | Wire approving_authority through CLI/HTTP/MCP | All three surfaces accept and forward `principal`; `PermissionError` reaches the caller; F-14 resolved | Planned |
| [#249](https://github.com/deghosal-2026/planner-critic-engine/issues/249) | Indirect-injection defense — typed tool-result provenance | Tool results carry typed provenance; deterministic policy gates block transitions from untrusted sources to sensitive state transitions | Planned |
| [#253](https://github.com/deghosal-2026/planner-critic-engine/issues/253) | Fix field_test_harness escalation auto-approve | Harness scopes `list_escalations()` to the current goal; rejection path exercised; no false approvals | Planned |
| [#256](https://github.com/deghosal-2026/planner-critic-engine/issues/256) | Compositional injection traps | At least 3 trap goals where each step is individually feasible but combination is harmful; compositional gate blocks all 3; results published | Planned |
| [#258](https://github.com/deghosal-2026/planner-critic-engine/issues/258) | Capability-scoped state transitions | Capability level hierarchy defined; each tool declares source capability; each transition requires minimum capability; gate blocks untrusted sources from sensitive transitions | Planned |
| [#259](https://github.com/deghosal-2026/planner-critic-engine/issues/259) | Well-formed malicious plan detection | Adversarial critic pass added; at least 3 well-formed malicious plans blocked; semantic-orphan detection added; false-positive rate measured on 170-goal corpus | Planned |
| [#260](https://github.com/deghosal-2026/planner-critic-engine/issues/260) | Benign-twin control for adversarial goals | Benign twin for each of 11 adversarial goals; twin strips injected text; comparison published; injection-resistance claim updated based on evidence | Planned |

## 6. M4 — Operational & Audit (#250–#252, #254, #257, #261, #262)

Scope rule: observability, operational improvements, and audit-trail integrity. All ship with before/after metrics.

| Issue | Deliverable | Closes when (success criterion) | Status |
|-------|-------------|----------------------------------|--------|
| [#250](https://github.com/deghosal-2026/planner-critic-engine/issues/250) | Downstream-error-rate measurement via partner-runner integration | Measurement spec published; required trace fields documented; integration point defined for runner partners | Planned |
| [#251](https://github.com/deghosal-2026/planner-critic-engine/issues/251) | Adaptive revision cap for strict goals | Strict goals detected automatically; revision cap reduced to 1 when appropriate; corpus regression green; cost savings measured | Planned |
| [#252](https://github.com/deghosal-2026/planner-critic-engine/issues/252) | Multi-model planner comparison | gpt-4o, claude-3.5, deepseek-v4 run against same 170-goal corpus; pass/fail rates, cost, and defect families compared; results published | Planned |
| [#254](https://github.com/deghosal-2026/planner-critic-engine/issues/254) | Critic satisfaction signals | When critic explicitly endorses a plan under strict mode, approval is allowed; signal defined and measured; corpus regression with zero under-claims | Planned |
| [#257](https://github.com/deghosal-2026/planner-critic-engine/issues/257) | Critic/planner capability tier split | Separate `planner.model` and `critic.model` config keys; benchmark across 3 tier combinations; cost and pass-rate comparison published | Planned |
| [#261](https://github.com/deghosal-2026/planner-critic-engine/issues/261) | Escalation audit trail — actor, explain, identity plumbing | `Escalation.resolved_by` field; `build_explain` returns accurate status after resolution; CLI/HTTP/MCP pass `principal`; tests pass | Planned |
| [#262](https://github.com/deghosal-2026/planner-critic-engine/issues/262) | Cost-vs-rigor guardrails — immutable gate config | `gates.required` config section; startup warning on disabled gates; engine refuses to start with all gates disabled; "simple" goal path still runs all gates | Planned |

## 7. M5 — Field Test & Release (#265–#271)

Execution order: #265 field test → #266 Docker → #267 operational benchmark → #268 boundary evaluator → #269 quality gate → #270 docs → #271 release coordination.

| Issue | Scope | Gate to close |
|-------|-------|---------------|
| [#265](https://github.com/deghosal-2026/planner-critic-engine/issues/265) | Field test results v0.2.2 + regression sweep | Hermetic CI green; 170/170 goals complete; 73/73 balanced approved; 97/97 strict escalated; 11/11 adversarial aborted; security oracle 7/7 + 35/35; all verdict deltas attributable vs v0.2.1; Scorecard A PASS |
| [#266](https://github.com/deghosal-2026/planner-critic-engine/issues/266) | Docker integration test | Docker image builds; full 170-goal field test runs inside container; verdicts match local run; Docker Compose integration passes; CI includes Docker step |
| [#267](https://github.com/deghosal-2026/planner-critic-engine/issues/267) | Operational benchmark vs v0.2.1 baseline | All 7 metrics measured and reported; regressions >10% flagged; script committed under `docs/field-test/v0.2.2/scripts/` |
| [#268](https://github.com/deghosal-2026/planner-critic-engine/issues/268) | Boundary-case evaluator with decision-context capture | All boundary cases run 5x; decision-context captured per trial; unsupported-evidence frequency reported; zero underclaim_approvals |
| [#269](https://github.com/deghosal-2026/planner-critic-engine/issues/269) | Final quality gate | Code review of all M1–M4 changes; ruff + mypy strict clean; coverage >91%; 1295+ deterministic tests pass; test count matches CI output |
| [#270](https://github.com/deghosal-2026/planner-critic-engine/issues/270) | Docs sweep | README, CHANGELOG, release notes, API reference, failure-mode register all updated; WBS index created; no stale-doc contradictions |
| [#271](https://github.com/deghosal-2026/planner-critic-engine/issues/271) | Release coordination | Tag v0.2.2; GitHub release published; all M1–M5 milestones closed; PyPI package live |

## 8. M6 — Release Readiness (#272–#277)

Strict sequential order: #272 security → #273 tests → #274 field test report → #275 docs → #276 packaging → #277 ship. Each issue closes only against the gate below.

| Issue | Scope | Gate to close |
|-------|-------|---------------|
| [#272](https://github.com/deghosal-2026/planner-critic-engine/issues/272) | Security scan — truffleHog, dependency audit, secret detection | truffleHog clean; dependency audit zero known vulnerabilities; SECURITY.md current; redaction verified on new surfaces |
| [#273](https://github.com/deghosal-2026/planner-critic-engine/issues/273) | All tests passing | Deterministic suite 100% pass (1295+); field test 0 true failures; Docker integration green; CI hermetic pass |
| [#274](https://github.com/deghosal-2026/planner-critic-engine/issues/274) | Field test report finalized | Results document published at `docs/field-test/v0.2.2/field-test-results-v0.2.2.md`; Scorecard A PASS; all verdict deltas attributable; operational benchmark metrics included |
| [#275](https://github.com/deghosal-2026/planner-critic-engine/issues/275) | Docs sweep | README, CHANGELOG, release notes, API reference, failure-mode register, WBS index all current; no stale-doc contradictions |
| [#276](https://github.com/deghosal-2026/planner-critic-engine/issues/276) | Packaging & PyPI | Dist builds clean; Dockerfile pinned; PyPI shows v0.2.2; fresh-venv install green |
| [#277](https://github.com/deghosal-2026/planner-critic-engine/issues/277) | Release tags and milestone closure | Git tag v0.2.2 created and pushed; GitHub release published; all M1–M6 milestones closed; no open issues remain in v0.2.2 scope |

**Pre-release aggregate gate — all must be green before #277 tags:** code review clean on the full diff · all testcases green · lint clean (ruff + mypy strict) · security scans clean · field test green with intended-deltas-only regression diff · docker tests green · coverage >91% · docs complete and consistent.

## 9. Version Bump Checklist (applied by #276)

| Location | Change |
|----------|--------|
| `pyproject.toml:3` | `version = "0.2.1"` → `"0.2.2"` |
| `src/planner_critic/__init__.py:32` | `__version__ = "0.2.1"` → `"0.2.2"` |
| `Dockerfile:16` | pinned wheel filename `planner_critic-0.2.1-py3-none-any.whl` → `0.2.2` |
| `README.md:7,20` | PyPI badge + status line |
| `docs/reference/quickstart.md:1` | header version |
| `CHANGELOG.md` | new `## v0.2.2` entry (Corrections / Gates / Security / Operational / Field Test) |
| `docs/reference/release-notes-v0.2.2.md` | new file, following v0.2.1 structure |

## 10. Open Decisions

- [ ] Confirm M2 and M3 can land in parallel (no file conflicts identified).
- [ ] Decide whether #252 (multi-model comparison) runs pre-tag or ships as spec-only.
- [ ] Confirm M6 security scan tooling (truffleHog available in CI or needs local run).