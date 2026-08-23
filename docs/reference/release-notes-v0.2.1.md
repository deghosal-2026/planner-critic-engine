# Release Notes v0.2.1

**Date:** 2026-08-23
**Package:** `planner-critic` v0.2.1 — [PyPI](https://pypi.org/project/planner-critic/)

## What's New

### Community Review Hardening (M11)
- **Frozen acceptance-criteria contract (#215)** — `AcceptanceContract` bound at run start; post-bind mutation creates a new contract version + audit trail; wrong-principal escalation rejection; hash stamped on every approval
- **Rollback credibility gate (#216)** — deterministic detection of unreachable / self-dependent / inconsistent-state / post-consumed rollbacks; twin fixture pair per pattern
- **Family-histogram cycling detection (#217)** — period-2 A→B→A→B blocker-family reshuffling stall signal; progress guard (#229) suppresses declining-mass alternation
- **Verification-before-mutate ordering gate (#219)** — detects vacuous verification windows (reversed-order / parallel-race); data-subject contract (#230) pre-state vs output derivation
- **Live-critic boundary-case runner (#218)** — repeated-trial evaluation of #171 fixtures against real critic models; label-flip, family-migration, evidence-drift, underclaim-approval metrics; report committed under `docs/field-test/`
- **Failure-mode register (#220)** — `docs/reference/failure-modes.md` — intentional vs needs-evidence assumptions register (14 rows)
- **Before/after operational benchmark (#221)** — latency, reviewer burden, operator workload vs critic-off baseline; downstream-error-rate spec published
- **Drift-metric blind-spot contract (#231)** — `critical_underclaims` interpretation key; two measurement classes named (critic-vs-guardrail vs critic-vs-reality)

### Code Quality (M12 #222)
- **10 code-review bugs found and fixed** (#232–#241) — histogram cycling detector dead under defaults, gate finding-id collisions, live-boundary fault isolation, acceptance-contract posture stamping, rollback-credible message quality, suggested-fix correctness, adaptor import test vacuity, evidence-drift pooling, content-hash ordering, approval-authority wiring documented (F-14)
- All fixes land with regression tests that fail on pre-fix code
- Lint clean (ruff + mypy strict, 274 files)
- Coverage 91.58% (>91% floor)

### Field Test Results (M12 #223)
- **170 goals across 40 domains** — 73 approved (balanced), 96 escalated (strict), 8 escalated (adversarial), 1 transient provider error, 0 true failures
- **30 verdict deltas vs v0.2.0** — all attributable to LLM non-determinism or #152 oscillation signal; zero unexplained
- **1295 deterministic subsystem tests** (14 docker-gated skips)
- **3 benchmarks** — cycling (#217), operational (#221), live-critic boundary (#218)
- **Live-critic boundary run:** label_flip=1.0, evidence_drift=1.0, family_migration=0.0, underclaim_approvals=0
- **Operational benchmark:** latency p50=13.86s (approved) / 27.82s (escalated), median revisions=1.0
- **Release gate: PASS** on all blocking criteria

## Breaking Changes

None. v0.2.1 is a patch release — no plan-schema changes, no store-schema changes, no API surface changes.

## Upgrade Path

No migration steps required. Update the wheel pin: `planner_critic-0.2.0-py3-none-any.whl` → `planner_critic-0.2.1-py3-none-any.whl`.

## Field Test Results

| Metric | Result |
|--------|--------|
| Balanced goals approved | 73/73 (100%) |
| Strict goals escalated | 96/97 (99%) — 1 transient provider error |
| Adversarial goals escalated | 8/8 (100%) |
| True failures | 0 |
| Verdict deltas vs v0.2.0 | 30 — all attributable |
| Scorecard A | PASS |
| Scorecard B (pass\* semantics) | 100% |
| Deterministic tests | 1295/1295 pass |
| Benchmarks | 3/3 complete |
| Live-critic boundary (#218) | Complete — report committed |
| Total LLM cost | ~$0.49 |

## Known Issues

- **Planner capability gap** — strict tolerance + LLM critic = structurally unable to approve non-trivial plans. Usable with `balanced` tolerance in production; `strict` is for adversarial/security testing.
- **Local model support** — DeepSeek-R1-8B cannot produce valid structured JSON; Qwen3-4B critic is too weak. Use `openai/gpt-4o-mini` via OpenRouter.
- **Approval-authority wiring (F-14)** — `approving_authority` enforcement (#215) is test-proven but not reachable from CLI/HTTP/MCP surfaces. Deferred to v0.3.0.
- **TUI / studio / IDE surfaces** — deferred to v0.3.0.
- **Backstage plugin / Slack dashboard** — deferred to v0.3.0.
- **Adaptive revision cap** — not yet implemented.

## Documentation

| Doc | Location |
|-----|----------|
| Field Test Results | `docs/field-test/v0.2.1/field-test-results-0.2.1.md` |
| Failure-Mode Register | `docs/reference/failure-modes.md` |
| Architecture | `docs/architecture/architecture-v0.1.0.md` |
| API Reference | `docs/reference/api.md` |
| Design Decisions | `docs/design/design-decisions.md` |
| Domain Pack Design | `docs/design/domain-pack-design.md` |
| Policy Engine Design | `docs/design/policy-engine-design.md` |
| Security | `SECURITY.md` |
| Changelog | `CHANGELOG.md` |