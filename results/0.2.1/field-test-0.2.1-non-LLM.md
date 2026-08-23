# Field Test Results — v0.2.1 Non-LLM

**Date:** 2026-08-23
**Branch:** `0.2.0-m12` (commit `94c0e4b`)
**Coverage:** 91.58% (>91% floor; no regression vs M11 accepted 92%)

---

## Pytest — Deterministic Test Suite

| Category | Passed | Skipped | Warnings |
|---|---|---|---|
| Unit & integration tests | 1295 | 14 (docker-gated¹) | 18 |

¹ Docker-gated skips require `docker compose up -d` then `PC_INTEGRATION=1`.

**Notes:**
- Full pytest suite `--no-cov` (CI runs with coverage, hit 91.58%)
- ruff check + format clean, mypy --strict 0 errors (274 files)
- 14 docker-gated LLM/HTTP/MCP tests excluded (no docker compose running)

---

## P0 — Goal & Assertion Validation

| Metric | Count |
|---|---|
| Goals scanned | 170 |
| Domains | 40 |
| Valid (JSON + assertion YAML parse) | 170 |
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

**Status:** COMPLETE — 169 traces analyzed (1 excluded: `mch-04-blast-radius` provider error)

| Metric | Value |
|---|---|
| Goals analyzed | 169 |
| Latency (approved) p50 | 13.86s |
| Latency (approved) p95 | 19.27s |
| Latency (escalated) p50 | 27.82s |
| Latency (escalated) p95 | 72.69s |
| Mean blockers per goal | 2.58 |
| Mean advisories per goal | 1.86 |
| Escalation decisions | 98 |
| Decisions per 100 goals | 58.0 |
| Mean LLM calls per goal | 1.4 |
| Median revisions to resolution | 1.0 (≤2 ✅) |
| Downstream error rate | Deferred — requires partner runner integration |

**Report saved:** `results/0.2.1/operational-report.json`

---

## Wiring Tests (tests/field_test_v0_2_1/)

| Test | Status |
|---|---|
| test_self_test_passes | ✅ |
| test_run_boundary_writes_artifacts | ✅ |
| test_build_provider_errors_without_config | ✅ |

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
| 🧪 Pytest suite | ✅ 1295 passed, 14 skipped |
| ✅ P0 validate | ✅ 170/170 valid |
| ✅ P2 subsystem hermetic | ✅ 93 passed |
| ✅ P4 benchmarks | ✅ all pass |
| ⏳ P3 LLM (goals sweep) | PENDING — run `--subsystem --all --run-llm` |
| ⏳ P3 LLM (boundary #218) | PENDING — run `--subsystem --all --run-llm --no-goals` |
| ⏳ bench_operational | PENDING — requires P3 goal traces |