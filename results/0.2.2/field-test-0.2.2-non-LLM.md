# Field Test Results — v0.2.2 Non-LLM

**Date:** 2026-08-26
**Branch:** `rel-0.2.2` (commit `59b46d7`)
**Coverage:** —

---

## Pytest — Deterministic Test Suite

| Category | Passed | Skipped | Warnings |
|---|---|---|---|
| Unit & integration tests | 1345 | 15 (12 docker-gated¹, 3 LLM², 1 flaky³) | 18 |

¹ Docker-gated skips require `docker compose up -d` then `PC_INTEGRATION=1`.
² LLM-dependent skips covered by the M5 field test sweep.
³ `test_robustness_c93.py:45` — flaky SQLite concurrency race under CI resource constraints.

**Notes:**
- Full pytest suite `--no-cov`
- ruff check + format clean
- 12 docker-gated tests excluded (no docker compose running)
- 3 LLM-dependent docker tests skip (covered by M5 sweep)

---

## P0 — Goal & Assertion Validation

| Metric | Count |
|---|---|
| Goals scanned | 181 |
| Domains | 42 |
| Valid (JSON + assertion YAML parse) | 181 |
| Broken | 0 |

---

## P4 — Hermetic Benchmarks

### bench_cycling.py — #229 #217 Self-Test

| Scenario | Expected fire | Fired | Result |
|---|---|---|---|
| defective-flat-mass-cycler | True | True | ✅ |
| legitimate-bimodal-declining-mass | False | False | ✅ |
| stasis | False | False | ✅ |
| monotone-progress | False | False | ✅ |

**Overall:** `SELF-TEST PASS`

### bench_live_boundary.py — #218 Self-Test

| Check | Passed |
|---|---|
| cases_evaluated > 0 | ✅ |
| All 4 metrics present | ✅ |
| Stub yields zero flips | ✅ |
| Stub yields zero drift | ✅ |
| Per-case records match | ✅ |

**Overall:** `SELF-TEST PASS`

### bench_operational.py — #221 Operational Benchmark

**Status:** COMPLETE — 181 traces analyzed

| Metric | v0.2.1 | v0.2.2 |
|---|---|---|
| Goals analyzed | 169 | 181 |
| Latency (approved) p50 | 13.86s | 24.69s |
| Latency (approved) p95 | 19.27s | 40.55s |
| Latency (escalated) p50 | 27.82s | 45.97s |
| Latency (escalated) p95 | 72.69s | 103.64s |
| Mean blockers per goal | 2.58 | 2.92 |
| Mean advisories per goal | 1.86 | 2.74 |
| Escalation decisions | 98 | 100 |
| Decisions per 100 goals | 58.0 | 55.2 |
| Mean LLM calls per goal | 1.4 | 1.63 |
| Median revisions to resolution | 1.0 (≤2 ✅) | 2.0 (≤2 ✅) |
| Downstream error rate | Deferred | Deferred |

---

## P2 — Subsystem Hermetic (pytest field_test_v0_2_0 + field_test_v0_2_1)

| Test directory | Tests |
|---|---|
| tests/field_test_v0_2_0/ | 90 passed |
| tests/field_test_v0_2_1/ | 3 passed |
| **Total** | **93 passed** |

---

## Summary

| Phase | Result |
|---|---|
| 🧪 Pytest suite | ✅ 1345 passed, 15 skipped |
| ✅ P0 validate | ✅ 181/181 valid |
| ✅ P2 subsystem hermetic | ✅ 93 passed |
| ✅ P4 benchmarks | ✅ all pass |
| ⏳ P3 LLM (goals sweep) | COMPLETE — 181 runs (170 inherited + 11 new) |
| ✅ P3 LLM (boundary #218) | COMPLETE — 6 cases × 5 trials, 60 audits, `underclaim_approvals=1` |