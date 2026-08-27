# Release Notes — v0.2.2

**Date:** 2026-08-27

**What's new in PlannerCritic Engine v0.2.2,** a feature-heavy hardening release that expands security coverage, adds typed rollback contracts, and wires new adversarial fixture families — while preserving the inherited 170-goal approve/escalate contract.

---

## Quick Summary

| Metric | v0.2.2 | vs v0.2.1 |
|--------|--------|-----------|
| Field test goals | 183 (170 inherited + 13 new) | 170 |
| Balanced approved | 73/73 (100%) | same |
| Strict escalated | 96/97 (99%) | same |
| Inherited adversarial aborted | 8/8 (100%) | same |
| New adversarial-benign approved | 8/8 (100%) | new |
| New compositional traps aborted | 3/3 (100%) | new |
| True failures | 0 | same |
| Deterministic tests | 1347 passed | 1295 passed |
| Benchmarks | 5 complete | 3 complete |
| Coverage | 91% | 91.58% |

---

## What Changed

### Foundation Corrections (M1)
- Fixed "Zero True Failures" prose contradiction in v0.2.1 field test report (#246)
- Reconciled `plan_oscillation_detected` count from 3 to 5 (#247)
- Removed 75 pytest-cov artifacts from `src/` and added `*.py,cover` to `.gitignore` (#248)
- Reconciled 1294/1295 test count discrepancy in v0.2.1 docs (#263)
- Created failure-origin taxonomy classifying 51 bugs by first-detectable layer (#264)

### Gate & Schema Hardening (M2)
- Runtime precondition verification on by default (#244)
- Typed rollback restoration contracts: `restores_state` + `restoration_evidence` on `RollbackStep` (#245)
- Requirement-traceability gate: opt-in `satisfies` field on `Task` (#255)
- Machine-actionable finding contract (#243)
- Decision-context capture + unsupported-evidence frequency metric in live-boundary runner (#242)

### Security & Injection Resistance (M3)
- Wired `approving_authority` through CLI/HTTP/MCP surfaces (#238)
- Fixed field_test_harness escalation auto-approve (#253)
- 11 benign-twin goal files for adversarial goals (#260)
- Tool-result provenance + capability-scoped state transitions (#249, #258)
- 3 compositional injection trap goals (#256)
- Well-formed malicious plan detection tests (#259)

### Operational & Audit (M4)
- Cost-vs-rigor guardrails: immutable `GatesConfig` with validation (#262)
- Escalation audit trail: `resolved_by` field, `build_explain` fix (#261)
- Critic satisfaction signals: `CRITIC_SATISFIED` reason code for strict mode approval (#254)
- Adaptive revision cap: strict goals reduce to 1 revision (opt-in, default off) (#251)
- Critic/planner capability tier split (#257)
- Multi-model planner comparison benchmark script (#252)
- Downstream error rate measurement specification (#250)

---

## Field Test Results

The full 183-goal sweep (170 inherited + 13 new v0.2.2 fixtures) completed with the same top-level approve/escalate contract as v0.2.1. All verdict deltas are attributable.

### Live Boundary Evaluator (#218)

The boundary evaluator (6 cases × 5 trials × 2 plans = 60 audits) returned:

| Metric | v0.2.1 | v0.2.2 (after rerun) |
|--------|--------|----------------------|
| label_flip_rate | 1.000 | 1.000 |
| family_migration_rate | 0.000 | 0.000 |
| evidence_drift_rate | 1.000 | 1.000 |
| underclaim_approvals | 0 | 0 |

The first run exposed `underclaim_approvals=1` due to balanced boundary framing. After switching to strict framing, the rerun cleared the signal.

### Operational Benchmark (#221)

| Metric | v0.2.1 | v0.2.2 |
|--------|--------|--------|
| Latency (approved) p50 | 13.86s | 24.69s |
| Latency (escalated) p50 | 27.82s | 45.97s |
| Mean blockers per goal | 2.58 | 2.92 |
| Mean advisories per goal | 1.86 | 2.74 |
| Mean LLM calls per goal | 1.4 | 1.63 |
| Median revisions | 1.0 | 2.0 |

---

## Key Learnings

1. New planner-visible schema fields must be lenient with LLM-shaped output.
2. Docker tests should not try to do expensive LLM behavior verification.
3. Versioned output paths and benchmark locations must not be hardcoded.
4. Most inherited corpus deltas are loop-shape deltas, not contract-level failures.
5. Never redact a serialized JSON blob if the result must remain machine-readable.

---

## Changelog

See [CHANGELOG.md](../../CHANGELOG.md) for the complete changelog.

---

## Upgrading

```bash
pip install --upgrade planner-critic
```

See the [quickstart guide](quickstart.md) for configuration and usage.

---

## Known Issues

- TUI/studio/IDE extensions deferred to v0.3.0 (#133, #135, #136, #138, #154, #157)
- `approving_authority` wiring completed in this release (#238, resolves F-14)