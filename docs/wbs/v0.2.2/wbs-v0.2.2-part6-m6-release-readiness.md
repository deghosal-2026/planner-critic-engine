# WBS — PlannerCritic Engine v0.2.2-M6: Release Readiness

> Part of the v0.2.2 release. See [index](wbs-v0.2.2-index.md) for milestone overview and dependency graph.
>
> **Branch:** `rel-0.2.2` · **Milestone:** [v0.2.2-M6 Release Readiness](https://github.com/deghosal-2026/planner-critic-engine/milestone/20)
>
> **Scope:** Final release readiness: security scan, all tests passing, field test report finalized, docs updated, PyPI release, tags updated, close all v0.2.2 milestones.

---

## Overview

M6 is the final release readiness gate. All issues are strictly sequential — each depends on the previous one completing successfully. No issue in M6 can close until the aggregate pre-release gate passes.

**Execution order:** #272 → #273 → #274 → #275 → #276 → #277

| Issue | Title | Area | Complexity |
|-------|-------|------|------------|
| #272 | Security scan — truffleHog, dependency audit, secret detection | security | low |
| #273 | All tests passing — full deterministic suite + field test confirmed green | testing | medium |
| #274 | Field test report finalized — results document, scorecards, verdict deltas | docs/field-test | medium |
| #275 | Docs sweep — README, CHANGELOG, release notes, API reference, failure-mode register | docs | medium |
| #276 | Packaging & PyPI release — build, dist, Dockerfile pin, upload | release | medium |
| #277 | Release tags and milestone closure — git tag, GitHub release, close all v0.2.2 milestones | release | low |

---

## #272 — [v0.2.2-M6] Security scan — truffleHog, dependency audit, secret detection

**Problem:** Before shipping v0.2.2, the release must pass a security scan. Any leaked secrets, vulnerable dependencies, or security regressions must be caught before the tag is created.

**Scope:**
- Run truffleHog across the entire repo to detect any committed secrets
- Run `pip-audit` or equivalent dependency vulnerability scanner
- Verify SECURITY.md is current and accurate
- Confirm no new secrets or credentials are committed in M1-M5 changes
- Run OpenSSF scorecard check (if applicable)

**Completion checklist:**
- [ ] truffleHog scan completes with zero findings (or documented false positives)
- [ ] Dependency audit shows zero known vulnerabilities in production dependencies
- [ ] SECURITY.md reviewed and updated if needed
- [ ] Any secrets found are removed and the commit history is cleaned
- [ ] Scan results published in the release notes
- [ ] OpenSSF badge passing (or regression filed with mitigation)

---

## #273 — [v0.2.2-M6] All tests passing — full deterministic suite + field test confirmed green

**Problem:** All code merged in M1-M5 must pass the full test suite. This includes the deterministic tests, the field test sweep, and the Docker integration test. No test failures are acceptable at release time.

**Scope:**
- Run full deterministic test suite: `pytest tests/ --cov=src/`
- Confirm 1295+ deterministic tests pass (fix #263 discrepancy)
- Confirm field test results from M5 show 0 true failures
- Confirm Docker integration test passes
- Verify no flaky tests are polluting results
- Run tests in CI (GitHub Actions) and confirm hermetic pass

**Completion checklist:**
- [ ] Deterministic suite: 100% pass (1295+ tests, 0 failures)
- [ ] Field test: 0 true failures, all 170 goals complete
- [ ] Docker integration: full pipeline passes inside container
- [ ] CI run: hermetic pass on GitHub Actions
- [ ] Test count: documented and matches CI output (fix #263)
- [ ] Coverage: >91% on all modules

---

## #274 — [v0.2.2-M6] Field test report finalized — results document, scorecards, verdict deltas

**Problem:** The M5 field test sweep produces raw results. These must be compiled into a finalized field test report document with scorecards, verdict delta analysis, and operational benchmark results.

**Scope:**
- Create `docs/field-test/v0.2.2/field-test-results-v0.2.2.md`
- Include Scorecard A (release gate) and Scorecard B (detailed results)
- Document all verdict deltas vs v0.2.1 with attribution
- Include operational benchmark results
- Include boundary-case evaluator results
- Include Docker integration test results
- Fix #246 (True Fail contradiction) and #247 (oscillation count inconsistency) in the process

**Completion checklist:**
- [ ] Field test results document published at `docs/field-test/v0.2.2/field-test-results-v0.2.2.md`
- [ ] Scorecard A: PASS
- [ ] All verdict deltas attributable
- [ ] Operational benchmark metrics reported
- [ ] Boundary-case metrics reported
- [ ] #246 and #247 closed

---

## #275 — [v0.2.2-M6] Docs sweep — README, CHANGELOG, release notes, API reference, failure-mode register

**Problem:** All documentation must be current for the v0.2.2 release. This includes the README, CHANGELOG, release notes, API reference, and failure-mode register.

**Scope:**
- README: update version from 0.2.1 to 0.2.2, add summary of new features
- CHANGELOG: add v0.2.2 entry with all M1-M5 changes
- Release notes: create `docs/reference/release-notes-v0.2.2.md`
- API reference: update for any new or modified interfaces
- Failure-mode register: add new rows for M1-M4 intentional trade-offs, update status of existing rows
- Field test results document: finalized (see #274)
- WBS index: already created at `docs/wbs/v0.2.2/wbs-v0.2.2-index.md`

**Completion checklist:**
- [x] README points to v0.2.2
- [x] CHANGELOG has complete v0.2.2 entry
- [x] Release notes published and reviewed
- [x] API reference matches current code
- [x] Failure-mode register updated with M1-M4 assumptions
- [x] WBS index created for v0.2.2
- [x] No stale-doc contradictions (grep sweep for "0.2.1-only" claims)

---

## #276 — [v0.2.2-M6] Packaging & PyPI release — build, dist, Dockerfile pin, upload

**Problem:** The v0.2.2 release must be packaged and published to PyPI. This includes building distribution artifacts, pinning the Dockerfile, and uploading to PyPI.

**Scope:**
- Build distribution artifacts: `python -m build`
- Verify dist artifacts are correct (check sdist and wheel)
- Update Dockerfile to pin v0.2.2
- Build and test Docker image locally
- Upload to PyPI: `twine upload dist/*`
- Verify PyPI package installs correctly: `pip install planner-critic==0.2.2`

**Version bump locations:**

| Location | Change |
|----------|--------|
| `pyproject.toml:3` | `version = "0.2.1"` → `"0.2.2"` |
| `src/planner_critic/__init__.py:32` | `__version__ = "0.2.1"` → `"0.2.2"` |
| `Dockerfile:16` | pinned wheel filename `planner_critic-0.2.1-py3-none-any.whl` → `0.2.2` |
| `README.md:7,20` | PyPI badge + status line |
| `docs/reference/quickstart.md:1` | header version |
| `CHANGELOG.md` | new `## v0.2.2` entry |
| `docs/reference/release-notes-v0.2.2.md` | new file |

**Completion checklist:**
- [ ] Version bumped at all 7 locations
- [ ] Distribution artifacts build cleanly (sdist + wheel)
- [ ] Dockerfile pinned to v0.2.2
- [ ] Docker image builds and runs correctly
- [ ] Package uploaded to PyPI
- [ ] Fresh install from PyPI works: `pip install planner-critic==0.2.2 && planner-critic --help`

---

## #277 — [v0.2.2-M6] Release tags and milestone closure — git tag, GitHub release, close all v0.2.2 milestones

**Problem:** The final step of the release process: create the git tag, publish the GitHub release, and close all v0.2.2 milestones (M1-M6).

**Prerequisites (all must be green before this issue starts):**
- [ ] #272 Security scan clean
- [ ] #273 All tests passing
- [ ] #274 Field test report finalized
- [ ] #275 Docs sweep complete
- [ ] #276 PyPI release published

**Completion checklist:**
- [ ] Git tag v0.2.2 created and pushed
- [ ] GitHub release published with release notes
- [ ] All v0.2.2 milestones closed (M1-M6)
- [ ] No open issues remain in v0.2.2 scope
- [ ] Deferred issues (v0.3.0) remain open with documented rationale
- [ ] Announcement ready (dev.to article or crosslinks)

---

## M6 Closure Gate

Before M6 closes, the following must be true:

### Standard milestone exit gate
- [ ] **Code review**: all M6 changes and the full release diff reviewed, no P1/P2 findings
- [ ] **Lint clean**: `ruff check src/ tests/` + `ruff format --check` 0 errors
- [ ] **Type check**: `mypy --strict src/ tests/` 0 errors
- [ ] **Test coverage**: `pytest --cov=src/ --cov-report=term` reports >90%
- [x] **Documents updated**: all docs reviewed and consistent for the release (README, CHANGELOG, release notes, API reference, failure-mode register, WBS index)
- [ ] **Clean checkin**: no debug code, no print statements, no TODOs

### Pre-Release Aggregate Gate (M6-specific)

**All of the following must be green before #277 tags:**

- [ ] **Code review**: clean on the full release diff
- [ ] **All testcases green**: full suite, zero unexplained skips
- [ ] **Lint clean**: `ruff check` + `ruff format --check` 0 errors
- [ ] **Type check**: `mypy --strict src/ tests/` 0 errors
- [ ] **Test coverage**: >90% on all modules (including all new modules)
- [ ] **Security scans**: truffleHog clean, dependency audit clean
- [ ] **Field test**: 170/170 goals, Scorecard A PASS, intended-deltas-only regression
- [ ] **Docker tests**: green against the rebuilt 0.2.2 image
- [x] **Docs**: complete and consistent, no stale-doc contradictions
- [ ] **PyPI**: v0.2.2 published with release-notes link

## Version Bump Checklist

| Location | Change | Done |
|----------|--------|------|
| `pyproject.toml:3` | `version = "0.2.1"` → `"0.2.2"` | [x] |
| `src/planner_critic/__init__.py:32` | `__version__ = "0.2.1"` → `"0.2.2"` | [x] |
| `Dockerfile:16` | pinned wheel filename `0.2.1` → `0.2.2` | [x] |
| `README.md:7,20` | PyPI badge + status line | [x] |
| `docs/reference/quickstart.md:1` | header version | [x] |
| `CHANGELOG.md` | new `## v0.2.2` entry | [x] |
| `docs/reference/release-notes-v0.2.2.md` | new file | [x] |

---

## Post-Release Checklist

- [ ] GitHub release published with release notes link
- [ ] PyPI page shows v0.2.2
- [ ] All v0.2.2 milestones closed (M1, M2, M3, M4, M5, M6)
- [ ] v0.3.0 deferred issues remain open with documented rationale
- [ ] `rel-0.2.2` branch merged into `main`
- [ ] Announcement published (dev.to, social, or internal)