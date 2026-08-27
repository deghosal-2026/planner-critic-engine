# WBS — PlannerCritic Engine v0.2.2-M1: Foundation Corrections

> Part of the v0.2.2 release. See [index](wbs-v0.2.2-index.md) for milestone overview and dependency graph.
>
> **Branch:** `rel-0.2.2` · **Milestone:** [v0.2.2-M1 Foundation Corrections](https://github.com/deghosal-2026/planner-critic-engine/milestone/15)
>
> **Scope:** Docs fixes, test-infrastructure corrections, and quick patches to v0.2.1 release artifacts. No new behavior, no schema changes.

---

## Overview

M1 is the foundation layer of v0.2.2. Every issue here is a correction to something that shipped in v0.2.1 — documentation contradictions, test infrastructure issues, and missing analysis frameworks. No new features, no behavioral changes.

| Issue | Title | Area | Complexity |
|-------|-------|------|------------|
| #246 | "Zero True Failures" prose contradiction | docs | trivial |
| #247 | Oscillation count inconsistency (3 vs 5) | docs | trivial |
| #248 | 75 pytest-cov artifacts committed under src/ | testing | trivial |
| #263 | 1294/1295 test count discrepancy on release commit | testing | medium |
| #264 | Failure-origin taxonomy | field-test | medium |

---

## #246 — [Docs] field-test-results-0.2.1.md prose claims "Zero true failures" while its own Scorecard B records True Fail = 1

**Problem:** The v0.2.1 field test results document states "Zero true failures" in the prose summary, but Scorecard B in the same document records `True Fail = 1`. This is a contradiction that undermines trust in the document.

**Root cause:** The "Zero true failures" claim refers to the field-test-found bugs (0 issues found by the LLM sweep), while Scorecard B's `True Fail = 1` refers to an engine-level failure (a plan that was approved but should not have been). These are different measurements conflated in the prose.

**Fix:**
- Update the prose to say "Zero field-test-found bugs" or similar qualifying language
- Add a footnote explaining the distinction between field-test-found bugs and engine-level true failures
- Verify Scorecard B is accurate and the True Fail = 1 is documented with attribution

**Completion checklist:**
- [ ] Prose updated to reflect accurate claim (e.g., "Zero field-test-found issues")
- [ ] Distinction between field-test-found bugs and engine-level true failures documented
- [ ] Scorecard B verified accurate
- [ ] True Fail = 1 attributed to a specific goal and reason
- [ ] Regression: no new contradictions introduced

---

## #247 — [Docs] plan_oscillation_detected count inconsistent between release doc (3 goals) and results artifact (5)

**Problem:** The v0.2.1 release documentation states `plan_oscillation_detected` fired for 3 goals, but the detailed results artifact shows 5 goals. The numbers must be reconciled.

**Root cause:** Likely a counting discrepancy between the release notes (written from memory or intermediate data) and the final results artifact (generated from the actual run data).

**Fix:**
- Determine the correct count from the stored traces
- Update the release doc to match the results artifact
- If the discrepancy reveals a real issue (e.g., the detector fired on goals it shouldn't have), document and fix

**Completion checklist:**
- [ ] Correct count verified from stored traces
- [ ] Release doc updated to match results artifact
- [ ] If discrepancy reveals a real issue, root cause documented
- [ ] Regression: no new counting discrepancies introduced

---

## #248 — [Repo] 75 pytest-cov artifacts (*.py,cover) are committed under src/planner_critic/

**Problem:** pytest-cov generates `.py,cover` files during coverage measurement. 75 of these artifacts are committed to the repository under `src/planner_critic/`. They should be ignored by git.

**Fix:**
- Add `*.py,cover` to `.gitignore`
- Remove all committed `.py,cover` artifacts from the repository
- Verify no new coverage artifacts appear in `git status` after a test run

**Completion checklist:**
- [ ] `.gitignore` updated with `*.py,cover` pattern
- [ ] All 75 artifacts removed from the repository
- [ ] `git status` clean after `pytest --cov=src/`
- [ ] CI pipeline does not regenerate committed artifacts

---

## #263 — [v0.2.2] 1294/1295 test count discrepancy on v0.2.1 release commit — CI shows 1 failed test not documented

**Problem:** The v0.2.1 release notes claim "1295/1295 deterministic tests passing with 14 Docker-gated skips." However, independent verification by Juan Gonzalez (taiwildlab) showed the public CI run on the release commit reports **1294 passed, 1 failed, 14 skipped**.

**Root cause:** Unknown — must be investigated. Possible causes:
1. Transient/flaky test that passed in local runs but failed in CI
2. Real regression that was not caught before release
3. Environment-specific issue (e.g., dependency version mismatch)
4. Test count calculated differently between local and CI

**Fix:**
- Identify which test failed on the v0.2.1 release commit CI run
- Determine the failure reason (transient, real regression, environment-specific)
- If transient: add to flaky test registry, update docs with caveat
- If real regression: open a bug and fix
- If environment-specific: isolate with Docker marker or document
- Add a CI-check step to the release checklist: "verify test count matches documentation"

**Completion checklist:**
- [ ] Root cause of the 1 CI failure identified
- [ ] Fix applied (flaky test isolation, regression fix, or docs update)
- [ ] CI run on a clean checkout shows documented test count
- [ ] Release checklist updated to verify test count against CI output
- [ ] #263 closed with evidence of the fix

---

## #264 — [v0.2.2] Failure-origin taxonomy — track how each field-test defect was first detectable

**Problem:** Currently, the field test results report the verdict (pass/fail) and the blocker family, but they do not track **how the failure was first detectable**. This makes it harder to:
- Identify which detection layer is most effective for each defect type
- Build a migration path from expensive field-test discovery to cheap deterministic detection
- Show the ROI of code review vs. harness invariants vs. live-model runs vs. production-like inputs

**Proposed by:** Russlan Ramdowar (dev.to article 4 comments)

**Fix:**
1. Define a failure-origin taxonomy with layers: code review, harness invariant, deterministic gate, unit test, live-model variance, production-like input
2. Tag each of the 41 bugs found across v0.1.0–v0.2.1 with its first-detectable layer
3. Publish the resulting heatmap in the next release notes

**Completion checklist:**
- [ ] Failure-origin taxonomy defined and documented (at least 6 layers)
- [ ] All 41 bugs from v0.1.0–v0.2.1 retrofitted with first-detectable layer
- [ ] Heatmap published in release notes or failure-mode register
- [ ] If the heatmap shows a pattern (e.g., "80% of field-test failures were first detectable by code review"), document the migration path

---

## M1 Closure Gate

Before M1 closes, the following must be true:

### Standard milestone exit gate
- [x] **Code review**: all M1 changes reviewed, no P1/P2 findings
- [x] **Lint clean**: `ruff check src/ tests/` + `ruff format --check` 0 errors
- [x] **Type check**: `mypy --strict src/ tests/` 0 errors
- [x] **Test coverage**: `pytest --cov=src/ --cov-report=term` reports >90% (91.50%)
- [x] **Documents updated**: all docs affected by M1 changes are current
- [x] **Clean checkin**: no debug code, no print statements, no TODOs, no .py,cover artifacts

### M1-specific closure
- [x] All 5 issues closed with evidence
- [x] No v0.2.1 release docs remain contradictory
- [x] `.gitignore` prevents future coverage artifact commits
- [x] Test count discrepancy resolved and documented
- [x] Failure-origin taxonomy ready for use in M5 field test results
- [x] Full test suite passes on `rel-0.2.2` after M1 merge