# WBS — PlannerCritic Engine v0.1.0 Part 6: Pre-Release + Release

> **Milestone covered:** M10 (Pre-Release + Release — security baseline, docs, packaging, PyPI, ship)
> **PRD covering this milestone:** [06-security](../../design/prd/06-security-baseline.md) (§6.1, §6.2, §6.3) · [07-success-metrics](../../design/prd/07-success-metrics.md) (§7.1 criteria roll-up, §7.2) · [02-architecture §2.10](../../design/prd/02-architecture.md#210-terminal-state-definition-done-for-v010) (terminal state)

---

## Milestone 10: Pre-Release + Release — security, docs, packaging, ship

**Objective:** Make v0.1.0 shippable and credible: PyPI publish (`planner-critic`), OWASP 6/10 agentic-AI coverage, OpenSSF Passing hygiene, PlannerCritic Essential security tier, complete docs (quickstart, interfaces, security, escalation, replay/viz, design decisions, release notes), and the open-source release checklist (repo public, branch protection, CI badge, CHANGELOG, tag).

**PRD coverage:** F-60 (+ full docs), OWASP ASI01/02/05/08/09/10, OpenSSF Passing, PlannerCritic Essential, [§7.1 criteria roll-up](../../design/prd/07-success-metrics.md#71-success-criteria-by-v010-release)
**CUJs covered:** all P0 (1–11, 13–15 — verify on shipped package)

### M10 Design Documents

- **D13 — Design decisions** (`docs/design/design-decisions.md`): finalize all DD records (DD-01 through DD-14); add any post-implementation records.
- **D15 — Quickstart** (`docs/reference/quickstart.md`): CUJ 1 path from `pip install` to first approved plan; verified fresh each release.
- **D16 — Release notes v0.1.0** (`docs/reference/release-notes-v0.1.0.md`): changelog, breaking changes, upgrade path (from nothing), known issues.
- **D17 — Security posture** (`SECURITY.md`): OWASP 6/10 mitigation table, OpenSSF checklist, Essential tier self-audit.
- **D18 — Contributing** (`CONTRIBUTING.md`): tests/coverage/mypy gate, commit conventions, PR template, development setup.

### M10 Key Items (explicitly called out)

#### 9.1 Security Baseline

- **OWASP Agentic AI Top 10** ([§6.1](../../design/prd/06-security-baseline.md#61-owasp-agentic-ai-top-10--target-partial-v010--broader-v02)): 6/10 direct coverage — ASI01 (goal schema typed/validated/recorded in store), ASI02 (execution-time re-gate + adapters gate), ASI05 (fail-closed F-73: unapproved → no executor), ASI08 (independent critic + bounded loop), ASI09 (escalation + audited resolution), ASI10 (plans/findings/escalations/executions tracked + reason codes). Write the mitigation table in `SECURITY.md`.
- **OpenSSF Passing** ([§6.2](../../design/prd/06-security-baseline.md#62-openssf-best-practices-badge--target-passing-floor)): MIT license (present), `SECURITY.md`, `CONTRIBUTING.md` (tests/coverage/mypy gate), CI on pushes, `.gitignore`, branch protection on `main` (PR review required).
- **PlannerCritic Essential** ([§6.3](../../design/prd/06-security-baseline.md#63-custom-plannercritic-security-baseline--essential-v01--hardened-v02)): deterministic gates always on; fail-closed; versioned store; escalation round-trip; per-goal budget; reason codes; field-test gate (from M9). `plancritic baseline check` (P1) is deferred to v0.2 but the Essential checklist is documented and self-auditable.

#### 9.2 Docs Completion

- **Architecture** (D1): finalize `architecture-v0.1.0.md` with the as-built component diagram, module map, and data flow.
- **Quickstart** (D15): `pip install planner-critic` → `plancritic init` → `plancritic plan "<goal>"` → first approved plan, tested fresh on a clean venv.
- **API reference** (D14): finalize with the built CLI/HTTP/MCP surfaces.
- **Release notes** (D16): changelog in `docs/reference/release-notes-v0.1.0.md`.
- **Design decisions** (D13): finalize with all DD records through DD-12.
- **SECURITY.md** + **CONTRIBUTING.md** (D17, D18)

#### 9.3 Packaging + Release

- **PyPI** (F-60): package `planner-critic` publishes cleanly; `plancritic` entrypoint; metadata renders; LICENSE file included; CHANGELOG current.
- **Release checklist:** tag `v0.1.0`, GitHub release with notes, PyPI publish (trusted publishing), CI badge in README. Repo goes public if not already.
- **Success criteria roll-up** ([§7.1](../../design/prd/07-success-metrics.md#71-success-criteria-by-v010-release)): confirm all 15 criteria at the terminal state; document any deviation in the release notes.
- **Terminal state** ([§2.10](../../design/prd/02-architecture.md#210-terminal-state-definition-done-for-v010)): a working v0.1.0 you can `pip install`, run `plancritic init`, give it a non-trivial goal, watch the critic flag a real gap, see the planner revise to approval — or escalate cleanly — with every version stored and diffs inspectable, `plannercritic-demo` running end-to-end, re-gate catching stale preconditions and triggering defined replan, failures classifiable as planning vs execution, shadow mode logging what *would* have happened, and a field-test matrix green across all six frameworks against a local model.

### M10 Task Checklist

| # | Task | Build (files) | Behavior + edge cases | Feature | Verify | Status |
|---|------|---------------|----------------------|---------|--------|--------|
| 1 | PyPI packaging | Finalize `pyproject.toml` (metadata, entrypoint, classifiers, dependencies), `README.md` (badge, quickstart summary), `LICENSE` (verify), `CHANGELOG.md` | `pip install planner-critic` in clean venv works; `plancritic --version` prints version; metadata renders on PyPI | F-60 | clean venv install + `plancritic --version` | [#65](https://github.com/deghosal-2026/planner-critic-engine/issues/65) · - [ ] |
| 2 | Security posture | Create `SECURITY.md` (OWASP 6/10 table, OpenSSF Passing checklist, Essential tier self-audit, reporting process); ensure `.github/workflows/ci.yml` exists | OWASP table with v0.1 mitigation row per ASI; OpenSSF Passing checklist auditable; branch protection on `main` | — | doc review; branch protection settings confirmed | [#66](https://github.com/deghosal-2026/planner-critic-engine/issues/66) · - [ ] |
| 3 | Contributing + CI | Create `CONTRIBUTING.md` (setup, test-run, coverage gate, lint gate, commit conventions, PR template); verify `.github/workflows/ci.yml` includes tests + coverage + ruff + mypy + field-test hermetic gate | CI green end-to-end on push; CONTRIBUTING gate reproduces CI checks locally | — | CI pipeline green; CONTRIBUTING instructions executable | [#67](https://github.com/deghosal-2026/planner-critic-engine/issues/67) · - [ ] |
| 4 | Docs completion | Finalize `architecture-v0.1.0.md` (D1), `quickstart.md` (D15), `api.md` (D14), `design-decisions.md` (D13), `demo-scenario.md` (D11), all other design docs reviewed for accuracy against shipped code | Every doc references the built behavior, not aspirational; quickstart reproduces CUJ 1 from scratch | — | quickstart verified in clean venv; API reference matches shipped code | [#68](https://github.com/deghosal-2026/planner-critic-engine/issues/68) · - [ ] |
| 5 | Release notes | Create `docs/reference/release-notes-v0.1.0.md` | Changelog: features shipped, tools/surfaces delivered, breaking changes (none), known gaps (P1 deferrals), upgrade-path (from nothing) | — | release-notes self-consistent with shipped package | [#69](https://github.com/deghosal-2026/planner-critic-engine/issues/69) · - [ ] |
| 6 | Success-criteria roll-up | Audit §7.1 items 1–15 against the built package; document in release notes or a `SUCCESS_CRITERIA_AUDIT.md` | Every criterion has a yes/partial/no with evidence (test, report, demo) | — | 15 criteria audited; deviations documented | [#70](https://github.com/deghosal-2026/planner-critic-engine/issues/70) · - [ ] |
| 7 | Release run | Tag `v0.1.0`, GitHub release (+ notes), PyPI publish (trusted publishing if configured, else manual `twine`), CI badge in README, repo public | `pip install planner-critic==0.1.0` from PyPI; GitHub release page renders; CI badge shows passing | F-60 | `pip install planner-critic==0.1.0` from PyPI; repo public | [#71](https://github.com/deghosal-2026/planner-critic-engine/issues/71) · - [ ] |

### M10 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| PyPI install | `pip install planner-critic==0.1.0` from PyPI | release smoke test |
| Quickstart | `init` → first approved plan < 10 min | clean-venv verification |
| Security | OWASP 6/10 + OpenSSF Passing + Essential verified | audit checklist in SECURITY.md |
| Hygiene | SECURITY + CONTRIBUTING + CI + branch protection present | repo settings + doc review |
| Docs | all D1–D18 authored, reviewed against shipped behavior, no aspirational language left | doc review |
| Success criteria | 15 criteria audited; deviation ≤ 2 partials | SUCCESS_CRITERIA_AUDIT.md |
| Coverage | >95% | `--cov-fail-under=95` |
| Lint | 0 ruff + 0 mypy strict | `ruff` + `mypy` |

### M10 Exit Gate

- [ ] Code review passed (all shipped files + release branch reviewed)
- [ ] Coverage > 95%
- [ ] Lint clean (ruff + mypy strict)
- [ ] Comments + docstrings in all code
- [ ] OWASP 6/10 + OpenSSF Passing + PlannerCritic Essential verified + documented in SECURITY.md
- [ ] Quickstart reproduces CUJ 1 from a clean venv
- [ ] `pip install planner-critic==0.1.0` from PyPI verified
- [ ] Field-test report (M9) present and all P0 cells pass
- [ ] All design docs D1–D18 authored and reviewed against shipped behavior
- [ ] GitHub release + tag + CHANGELOG complete; repo public (if timing decided)

**Dependency:** M1–M9 (everything ships through here). **Produces:** v0.1.0 release artifact + foundation for v0.2.0 (P1 items: web UI, Postgres, Anthropic/Gemini, multi-critic, plan templates, export, OTel, heuristic packs, property-based fuzzing — see [index](wbs-v0.1.0-index.md)).