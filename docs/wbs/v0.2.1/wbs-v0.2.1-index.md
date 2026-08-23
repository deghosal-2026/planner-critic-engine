# WBS — PlannerCritic Engine v0.2.1 (Index)

> Work breakdown for the **v0.2.1 patch release** — fixes for defects discovered on v0.2.0 (**P1**) plus the community-review hardening set (**M11**, dev.to Parts 1–3 threads, Aug 21–23), closed out by release-readiness activities (**M12**). All work lands on branch **`0.2.1-m11`** until release.
>
> **Author:** Debashish Ghosal · **Date:** 2026-08-23 · **Status:** Planned (issues filed)
>
> **GitHub milestones:** [**0.2.1-M11 Community Review Hardening**](https://github.com/deghosal-2026/planner-critic-engine/milestone/13) · [**0.2.1-M12 Release Readiness**](https://github.com/deghosal-2026/planner-critic-engine/milestone/14). Issue bodies carry full context; this index carries only the tracking checklists and success criteria.

---

## 1. Milestone Overview

> **Sequencing rationale:** patch-first, then hardening, then release. The bug-fix sweep runs first because discovered defects may touch the same files as the M11 features (gates, loop controller, drift) and must not be masked by new behavior. M11 items are mutually independent and can land in any order. M12 runs only after both predecessors' exit gates pass.

| M# | Name | GitHub milestone | Issues | Status |
|----|------|------------------|--------|--------|
| **P1** | Bug-Fix Sweep of v0.2.0 | TBD (`0.2.1-P1` at triage) | TBD | Pending triage |
| **M11** | [Community Review Hardening](https://github.com/deghosal-2026/planner-critic-engine/milestone/13) | 0.2.1-M11 | [#215–221](https://github.com/deghosal-2026/planner-critic-engine/issues/215), alternation guard [#229](https://github.com/deghosal-2026/planner-critic-engine/issues/229), data-subject contract [#230](https://github.com/deghosal-2026/planner-critic-engine/issues/230), drift blind-spot contract [#231](https://github.com/deghosal-2026/planner-critic-engine/issues/231), closure gate [#228](https://github.com/deghosal-2026/planner-critic-engine/issues/228) | 🔨 In progress — #215–221 implemented; #229–231 next; #228 closure gate last |
| **M12** | [Release Readiness](https://github.com/deghosal-2026/planner-critic-engine/milestone/14) | 0.2.1-M12 | [#222–227](https://github.com/deghosal-2026/planner-critic-engine/issues/222) | Planned |

## 2. Dependency Graph

```
P1 (Bug-Fix Sweep)            ── no new behavior; stabilizes the base
  └─► M11 (Community Review)  ── independent items; may touch same subsystems
        └─► M12 (Release)     ── quality gate + regression sweep + docs + ship
```

## 3. P1 — Bug-Fix Sweep of v0.2.0 (pending triage)

Scope rule: fixes to shipped v0.2.0 behavior only; anything unfixable by gate ships as a documented caveat in the release notes, never silent. Titles follow the `[CodeReview] file: symptom` convention used for [#184–214](https://github.com/deghosal-2026/planner-critic-engine/issues/184).

- [ ] Triage discovered defects into a `0.2.1-P1` GitHub milestone with severity grouping (critical / important).
- [ ] Every filed defect names file + observable symptom + failing case or reproduction.
- [ ] Fixes land with a regression test that fails on pre-fix code.
- [ ] Anything deferred is classified and recorded as a caveat in #225's release notes.
- [ ] Patch invariant held: no plan-schema or store-schema changes introduced by fixes.

## 4. M11 — Community Review Hardening (#215–#221)

One deliverable per issue; issue bodies carry design detail. This table is the closure checklist: flip the ✅ when the issue closes against its success criterion.

| Issue | Deliverable | Closes when (success criterion) | Status |
|---|---|---|
| [#215](https://github.com/deghosal-2026/planner-critic-engine/issues/215) Frozen acceptance-criteria contract | `AcceptanceContract` artifact bound at run start; approval consumes only the bound contract | Mid-run Goal/config mutation does not alter approval decisions (test-proven); post-bind mutation creates a new contract version + audit event; wrong-principal escalation attempts rejected; contract hash stamped on every approval and rendered by `plans show` / `replay`; store migration green | ✅ Implemented |
| [#216](https://github.com/deghosal-2026/planner-critic-engine/issues/216) Rollback credibility gate | Deterministic `rollback_credible` gate: unreachable / self-dependent / inconsistent-state / post-consumed patterns | Each pattern caught via public gate entry point with its own reason code; twin fixture pair per pattern blocks exactly plan_b; critic labeling the defect advisory cannot prevent the BLOCKER; zero new findings on previously clean plans across the full corpus regression | ✅ Implemented |
| [#217](https://github.com/deghosal-2026/planner-critic-engine/issues/217) Family-histogram oscillation detection | Period-p cycling stall signal (companion to #183 stasis) | Synthetic period-2 cycler trips `FAMILY_HISTOGRAM_CYCLING` while F-06, structural oscillation, and #183 stasis all stay silent on the same trace; genuinely repairing sequences produce no signal; retrospective benchmark over stored traces committed (JSON per-goal); ship-default-on vs config-only decided by evidence (orthogonality ≥80%, false-positive rate ≤5%) | ✅ Implemented |
| [#218](https://github.com/deghosal-2026/planner-critic-engine/issues/218) Live-critic boundary-case runner | Repeated-trial evaluation of #171 fixtures against real critic models | All boundary cases + adversarial-wording variants × N trials executed; label-flip, family-migration, evidence-drift, and underclaim-approval metrics computed; explanations + claimed facts retained per trial; at least one seeded variant demonstrably lands advisory for the target model (blind spot made visible); JSON + markdown report committed under `docs/field-test/`; total spend ≤ $1 | ✅ Implemented |
| [#229](https://github.com/deghosal-2026/planner-critic-engine/issues/229) Legitimate-alternation guard for #217 | Synthetic bimodal fixture + `--self-test` benchmark scenario | Declining-mass legitimate-bimodal sequence stays silent through every prefix (progress guard shipped if current semantics fire); defective flat-mass cycler still fires; `bench_cycling.py --self-test` PASSes both scenarios; register row F-05 updated with the measured boundary; #217 default-on additionally gated on this scenario | 🔨 Next |
| [#230](https://github.com/deghosal-2026/planner-critic-engine/issues/230) Verification data-subject contract for #219 | Triplet fixture + subject-keyed semantics doc | Triplet members pass/block/pass exactly (pre-state-before pass; pre-state-after-raced blocked with `verification_after_consumer`; output-after pinned passing against `verification_ordering` explicitly); subject derivation rule documented in gate docstring + design note; v0.3.0 optional-`subject` evolution spec published; corpus regression green with zero FPs | 🔨 Queued |
| [#231](https://github.com/deghosal-2026/planner-critic-engine/issues/231) Drift-metric blind-spot contract | Annotate `critical_underclaims` + name the two measurement classes | Interpretation key present in `compute_drift_summary()` output; register F-06 split into critic-vs-guardrail vs critic-vs-reality rows with origin-misclassification row owned by #218; `live_boundary` docstring pairing explicit; annotation-only diff, suite green | 🔨 Queued |
| [#219](https://github.com/deghosal-2026/planner-critic-engine/issues/219) Verification-before-mutate ordering gate | Vacuous-verification-window detection + boundary fixture pair | verifies-before-mutate vs verifies-after-mutate twins behave correctly through `run_deterministic_gates()`; consumer inside the window yields `VERIFICATION_AFTER_CONSUMER` regardless of critic severity; parallel-group variant caught without double-reporting; zero false positives on corpus regression; placement semantics documented | ✅ Implemented |
| [#220](https://github.com/deghosal-2026/planner-critic-engine/issues/220) Failure-mode register | `docs/reference/failure-modes.md` — intentional vs needs-evidence assumptions register | ≥10 seeded rows spanning Known Gaps, ADRs, field-test findings, and M11 issues; every row carries class + evidence/rationale link + owner + last-verified date; README Known Gaps deduplicated to a pointer; all evidence links resolve | ✅ Implemented |
| [#221](https://github.com/deghosal-2026/planner-critic-engine/issues/221) Before/after operational benchmark | Latency, reviewer burden, operator workload vs critic-off baseline | Metrics derived from stored traces reconcile with published v0.2.0 totals; paired `heuristic-only` vs `deterministic-first` run over both corpora completed; headline before/after number stated per metric; downstream-error-rate measurement spec + required trace fields published; JSON artifacts committed | ✅ Implemented |

**M11 closure gate — mandatory, tracked by [#228](https://github.com/deghosal-2026/planner-critic-engine/issues/228):** before M11 closes, the full verification battery re-runs on the complete M11 diff:

- [ ] Code review of every #215–#221 commit; findings resolved or filed.
- [ ] **All testcases green** — complete `pytest` suite incl. every module M11 introduced; zero unexplained skips.
- [ ] **Lint clean** — `ruff check .` 0 errors; `mypy --strict` 0 errors.
- [ ] **Security scans** — secret scan clean on the diff; dependency audit clean vs v0.2.0; redaction spot-check on new output surfaces (live-critic runner logs/reports).
- [ ] Coverage regenerated for all new modules; evidence recorded for #222.

House standard applies throughout (docstrings, coverage gate, hermetic-by-default). Benchmark items may close on negative results if honestly documented — a negative result with evidence is a valid outcome, not a failure.

## 5. M12 — Release Readiness (#222–#227)

Execution order: #222 quality gate → #223 field test/regression/docker → #224 security → #225 docs → #226 packaging → #227 ship. Each issue closes only against the gate below; issue bodies carry full checklists.

| Issue | Scope | Gate to close |
|---|---|---|
| [#222](https://github.com/deghosal-2026/planner-critic-engine/issues/222) Final quality gate | Code review of combined release diff; lint/types/tests/coverage | Review findings resolved; **all testcases green** (full suite incl. P1 + M11 modules, zero unexplained skips); `ruff` 0 errors; `mypy --strict` 0 errors; coverage **>91%** incl. all new modules; docstrings complete; evidence recorded |
| [#223](https://github.com/deghosal-2026/planner-critic-engine/issues/223) Field test results v0.2.1 + regression sweep | Special field tests + docker tests | Hermetic CI green ($0 LLM); injection/gate-regression 100%; §7.1 criteria held (blocker detection ≥90%, median revisions ≤2, no uncaught `PlanningError`); every verdict delta attributable to a P1 fix or M11 feature; **docker integration suite green against the rebuilt 0.2.1 image** (`tests/docker/`: CLI smoke, containerized loop vs local-LLM, HTTP/MCP surfaces, compose healthchecks); results committed under `docs/field-test/v0.2.1/` |
| [#224](https://github.com/deghosal-2026/planner-critic-engine/issues/224) Security clean | Posture re-validation on changed surfaces | OpenSSF badge passing (or filed with mitigation); dependency audit clean; redaction verified end-to-end incl. new M11 outputs; no secret leaks in repo scan |
| [#225](https://github.com/deghosal-2026/planner-critic-engine/issues/225) Docs sweep | README, CHANGELOG, release notes, API reference, quickstart | `release-notes-v0.2.1.md` covers every P1 fix + M11 deliverable; breaking changes: none stated; quickstart runs end-to-end from fresh clone; API reference lists all new gates/reason codes/modules; no stale-doc contradictions |
| [#226](https://github.com/deghosal-2026/planner-critic-engine/issues/226) Packaging & PyPI | Dist build, wheel pins, publish | Fresh-venv install green (base + extras) at 0.2.1; dist builds under hatchling pin; Dockerfile wheel pin updated + image builds; PyPI shows 0.2.1 with release-notes link |
| [#227](https://github.com/deghosal-2026/planner-critic-engine/issues/227) Release coordination | Tag, announce, close | Schema-diff invariant verified clean; tag `v0.2.1` + GitHub release published from release notes; all 0.2.1 milestones closed with open issues == documented caveats; announcement crosslinks live (PyPI, GitHub, dev.to) |

**Pre-release aggregate gate — all must be green before #227 tags:** code review clean on the full diff · all testcases green · lint clean (ruff + mypy strict) · security scans clean · special field tests green with intended-deltas-only regression diff · docker tests green · coverage >91% · docs complete and consistent.

## 6. Version Bump Checklist (applied by [#226](https://github.com/deghosal-2026/planner-critic-engine/issues/226))

| Location | Change |
|---|---|
| `pyproject.toml:3` | `version = "0.2.0"` → `"0.2.1"` |
| `src/planner_critic/__init__.py:32` | `__version__ = "0.2.0"` → `"0.2.1"` |
| `Dockerfile:16` | pinned wheel filename `planner_critic-0.2.0-py3-none-any.whl` → `0.2.1` |
| `README.md:7,20` | PyPI badge + status line |
| `docs/reference/quickstart.md:1` | header version |
| `CHANGELOG.md` | new `## v0.2.1` entry (Bug Fixes / Hardening; Breaking Changes: none) |
| `docs/reference/release-notes-v0.2.1.md` | new file, mirroring `release-notes-v0.2.0.md` |

## 7. Open Decisions

- [ ] P1 triage: confirm the discovered-defect list and create the `0.2.1-P1` milestone.
- [ ] Confirm regression-only sweep suffices (no gate/loop-semantics fixes hiding in P1).
- [ ] Decide whether #221's paired live-model run executes pre-tag or ships as spec-only in this release.
