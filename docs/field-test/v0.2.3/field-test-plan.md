# Field Test Plan — v0.2.3 "Corrections + Gate Canary"

> **Status:** Planned · **Version:** 0.2.3 · **Window:** Aug 29-Sep 5, 2026
> **Owner:** Deb Ghosal
> **Branch:** `feature-v0.2.3`
>
> This plan builds on v0.2.2's 183-goal corpus and adds four new verification dimensions driven by M1 fixes: Gate Canary health check, transit-integrity assertion, approving_authority enforcement, and DecisionContext population.

## 1. What Changed From v0.2.2

| Dimension | v0.2.2 | v0.2.3 | Why |
|-----------|--------|--------|-----|
| **Gate Canary** | Not measured | `plancritic gates canary --check` run before/after sweep | Assert every gate class still fires on known-bad plan (#278) |
| **Transit-integrity** | Not measured | `verify_transit_integrity()` in boundary evaluator | Detect redaction corrupting numeric JSON (F-20, #296) |
| **Authority enforcement** | Dormant on all shipped surfaces | `build_escalation_manager()` binds authority from stored contract; CLI/HTTP/MCP enforce | PermissionError now fires from all surfaces (F-14, #297) |
| **DecisionContext** | Never populated (all `"unknown"`) | Populated from registry/transport: model_id, version, temperature, prompt hash, timestamp | Trial records attributable (#298) |
| **Frozen-Claim Protocol** | Prose-versus-artifact only | Extended: denominator completeness, artifact freeze, determinism boundaries | Catch internally consistent claims with wrong denominator (#279) |
| **Docker** | v0.2.2, no `gates` CLI | v0.2.3 image, `gates` subcommand wired, canary fixtures packaged | CI-ready, in-container gate canary |
| **Corpus** | 183 goals across 43 domains | 183 goals across 43 domains (unchanged) | No new domains this release |
| **Model pairs** | 5 pairs | 5 pairs (unchanged) | No new pairs this release |
| **Cost** | ~$0.57 | ~$0.57 (same LLM calls) | Measurement infrastructure only |

## 2. Objective

| # | Question | How answered |
|---|----------|-------------|
| Q1 | **Do all deterministic gates still fire on known-bad plans?** | Run `plancritic gates canary --check` before and after the sweep. All 10 gates must pass. |
| Q2 | **Does redaction corrupt numeric JSON fields?** | Run `verify_transit_integrity()` on boundary evaluator output. Zero corruption events. |
| Q3 | **Does approving_authority enforcement work from all surfaces?** | End-to-end test against CLI/HTTP/MCP with known authority. PermissionError fires on wrong principal. |
| Q4 | **Is DecisionContext populated with real metadata?** | Verify trial records have model_id, version, temperature, prompt hash, timestamp — not "unknown". |
| Q5 | **Do any regressions appear against the v0.2.2 baseline?** | Compare all metrics against published v0.2.2 field test results. Document deltas. |

## 3. Pass/Fail Criteria

### 3.1 Standard Sweep (unchanged from v0.2.2)

| Criterion | Target | Status |
|-----------|--------|--------|
| Balanced approved | 73/73 | ✅ Same as v0.2.2 |
| Strict escalated | 96/97 | ✅ Same as v0.2.2 |
| Adversarial blocked | 8/8 | ✅ Same as v0.2.2 |
| True failures | 0 | ✅ Same as v0.2.2 |
| Underclaim approvals | 0 | ✅ Same as v0.2.2 |

### 3.2 New Verification Dimensions

| Criterion | Target | Verification method |
|-----------|--------|-------------------|
| Gate Canary | 10/10 gates pass | `plancritic gates canary --check` pre and post sweep |
| Transit-integrity | 0 corruption events | `verify_transit_integrity()` on boundary report |
| Authority enforcement | PermissionError on wrong principal | CLI/HTTP/MCP e2e tests with stored AcceptanceContract |
| DecisionContext | 0 trial records with `model_id="unknown"` | Boundary evaluator report inspection |

### 3.3 Comparison Against v0.2.2

| Metric | Expected | If worse |
|--------|----------|----------|
| Balanced approved | 73/73 (same) | Regression — investigate |
| Strict escalated | 96/97 (same) | Regression — investigate |
| Gate canary passes | 10/10 (new) | Fix gate failure before release |
| Transit-integrity events | 0 (new) | Fix redaction before release |
| Authority enforcement | PermissionError fires (new) | Fix escalation management before release |
| DecisionContext populated | No "unknown" (new) | Fix provider wiring before release |

## 4. Execution Order

1. Run `plancritic gates canary --check` — pre-sweep baseline
2. Run standard 183-goal field test sweep
3. Run `plancritic gates canary --check` — post-sweep verification
4. Run boundary evaluator with transit-integrity assertion
5. Run authority enforcement e2e tests (CLI/HTTP/MCP)
6. Run DecisionContext population verification
7. Generate comparison table vs v0.2.2
8. Capture learnings
9. Write FIELD_TEST_REPORT.md

## 5. Deliverables

- `docs/field-test/v0.2.3/field-test-plan.md` — this document
- `docs/field-test/v0.2.3/FIELD_TEST_REPORT.md` — full results with comparison table
- `docs/field-test/v0.2.3/learnings.md` — lessons learned
- `docs/field-test/v0.2.3/docker-integration-results.md` — Docker test results
- All results in `results/field-test/v0.2.3/`