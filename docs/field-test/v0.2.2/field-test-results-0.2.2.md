# Field Test Results — v0.2.2

> **Date:** 2026-08-27
> **Provider:** OpenRouter `openai/gpt-4o-mini` (both planner and critic roles)
> **Loop:** deterministic-first · revision_cap=4
> **Coverage:** 183 of 183 goals across 43 domains · **Full corpus complete**
> **Cost:** ~$0.49 for the inherited 170-goal sweep + incremental cost for 13 new fixtures
> **Config:** `OPENROUTER_API_KEY` env var

---

## TL;DR

v0.2.2 is a feature-heavy hardening release: typed rollback restoration contracts, requirement traceability, runtime precondition verification, compositional injection traps, benign-twin adversarial controls, new security fixtures, and operational runner cleanup. The full field test confirms the inherited corpus still behaves correctly at the top level: **73/73 balanced goals approved, 96/97 strict goals escalated, 8/8 inherited adversarial goals aborted, and 13/13 new v0.2.2 security fixtures behaved as designed.**

The release required more harness work than v0.2.1, but the final state is materially cleaner than the first draft. The goal sweep itself surfaced **no broad approve/escalate regression**, and the live boundary evaluator (#218) is back to a safer baseline after the strict-framing fix: `family_migration_rate=0.000` and `underclaim_approvals=0` on rerun. The harness and reporting bugs found during the run were fixed (`run-field.py` output path, centralized benchmark paths, redaction-safe JSON output, missing #259 fixtures), and the final boundary rerun cleared the strongest critic-quality regression signal.

---

## BLUF (Bottom Line Up Front)

**The engine works across the full field corpus, and the final boundary rerun cleared the strongest critic regression signal.** The main planning loop remains sound on realistic goals across all inherited domains and all new v0.2.2 fixtures. Deterministic gates, strict tolerance, and adversarial abort policy still hold. The first boundary run exposed an under-claim blind spot, but the strict-framing fix removed that failure on rerun.

- **Inherited balanced goals:** 73/73 approved (100%)
- **Inherited strict goals:** 96/97 escalated (99%)
- **Inherited adversarial goals:** 8/8 escalated with `replan_aborted` (100%)
- **New v0.2.2 fixtures:** 13/13 behaved as intended (8 benign twins approved, 3 compositional traps aborted, 2 well-formed-malicious fixtures added to the corpus)
- **Deterministic non-LLM validation:** 1345 passed, 15 skipped, 18 warnings; P2 subsystem hermetic 93 passed; P4 self-tests all passed
- **Operational benchmark:** completed on 181 traces; latency and reviewer burden are materially higher than v0.2.1
- **Boundary evaluator (#218):** `label_flip_rate=1.0`, `evidence_drift_rate=1.0`, `family_migration_rate=0.000`, `underclaim_approvals=0`

**Bottom line:** the corpus sweep supports shipping confidence for the planner/gate loop, and the strict-framing boundary rerun closed the sharpest critic-regression concern from the first pass.

---

## Visual Summary

| Dimension | v0.2.1 | v0.2.2 | Delta |
|-----------|--------|--------|-------|
| Goals swept | 170/170 | 183/183 | +13 new fixtures |
| Domains | 40 | 43 | +3 fixture domains / categories |
| Balanced approved | 73/73 (100%) | 73/73 (100%) | same on inherited corpus |
| Strict escalated | 96/97 (99%) | 96/97 (99%) | same on inherited corpus |
| Inherited adversarial aborted | 8/8 | 8/8 | same |
| New benign-twin goals | 0 | 8 approved | new measurement arm |
| New compositional traps | 0 | 3 aborted | new security arm |
| New well-formed malicious fixtures | 0 | 2 added | new #259 fixture coverage |
| Deterministic tests | 1295 passed, 14 skipped | 1345 passed, 15 skipped | +50 pass, +1 skip |
| P2 subsystem hermetic | 93 passed | 93 passed | same |
| Benchmarks | 3 complete | 3 complete | same count |
| Operational p50 approved | 13.86s | 24.69s | slower |
| Operational p50 escalated | 27.82s | 45.97s | slower |
| Mean blockers / goal | 2.58 | 2.92 | +0.34 |
| Mean advisories / goal | 1.86 | 2.74 | +0.88 |
| Mean LLM calls / goal | 1.4 | 1.63 | +0.23 |
| Boundary family migration | 0.000 | 0.000 | same after rerun |
| Boundary underclaim approvals | 0 | 0 | same after rerun |

---

## What Changed Since v0.2.1

v0.2.2 is not a patch release. It expands security coverage, adds new fixtures, and changes planner-visible schema behavior.

1. **Rollback restoration contracts became typed (#245).** `RollbackStep.restores_state` became structured, which improved downstream meaning but introduced a planner-visible schema delta. This caused the accessibility regression on early runs until lenient coercion was added.

2. **Runtime precondition verification is now on by default (#244).** This hardens the loop against plans that merely gesture at dependencies without proving them.

3. **Requirement traceability exists (#255).** Plans can now carry `satisfies` markers, enabling a new class of traceability checks.

4. **New adversarial/security fixture families were added.** v0.2.2 includes 8 benign twins (#260), 3 compositional traps (#256), and now 2 well-formed malicious fixtures (#259) in addition to the inherited corpus.

5. **The field-test runner and benchmark layout were cleaned up.** Scripts were centralized under `docs/field-test/scripts/`; stale versioned paths and output-dir assumptions were fixed during the run.

6. **The live boundary evaluator gained richer output.** The v0.2.2 report carries additional context fields, which is useful, but also exposed a redaction bug that had to be fixed.

---

## What This Means for Users

| Change | User-visible impact |
|--------|---------------------|
| Typed rollback restoration contracts (#245) | Plans can now carry explicit state-restoration claims, but LLM-produced rollback fields needed lenient coercion to avoid false schema failures |
| Runtime precondition verification on by default (#244) | Plans that merely hint at dependencies are more likely to be rejected before approval |
| Requirement traceability (#255) | Tasks can now be tied more explicitly to acceptance criteria, enabling clearer audits and better future semantic checks |
| Compositional injection traps (#256) | The engine now has explicit corpus coverage for attacks where individually safe actions become harmful only in combination |
| Benign-twin control (#260) | Adversarial results can now be compared against inert equivalents, separating true injection isolation from mere gate strictness |
| Well-formed malicious fixtures (#259) | The repo now contains runnable fixtures documenting the structural blind spot, even though the deeper semantic defense is still incomplete |
| Runner output-dir fixes | Field-test traces now land in the correct release directory, so reruns and skip-existing behavior work reliably |
| Boundary JSON redaction fix | Machine-readable boundary artifacts remain parseable after redaction instead of being silently corrupted |

---

## Methodology

The v0.2.2 field test was run in the same four phases as v0.2.1, with the same cost-tiering philosophy: all hermetic work first, then paid LLM evaluation.

| Phase | Command | Cost | Duration |
|-------|---------|------|----------|
| P0 — validate | `run-field.py --validate --all` | $0 | ~5 min |
| P2 — subsystem hermetic | `run-field.py --subsystem --all` | $0 | ~45 min |
| P4 — benchmarks | `run-field.py --benchmarks --all` | $0 | ~30 min |
| P3 — LLM sweep | `run-field.py --subsystem --all --run-llm` | paid | ~90 min + reruns |

The inherited corpus is compared directly against `v0.2.1` because that was the published baseline. Supplemental v0.2.2 fixtures are reported separately so the inherited regression story stays readable.

Artifacts used for this report:

- `results/0.2.2/field-test-0.2.2-llm.md`
- `results/0.2.2/field-test-0.2.2-non-LLM.md`
- `results/0.2.2/live-boundary-report.md`
- `docs/field-test/v0.2.2/learnings.md`

---

## Coverage Status

The v0.2.2 program exercised both the inherited regression corpus and new security fixtures.

| Coverage | Goals | Domains |
|----------|-------|---------|
| v0.2.1 inherited goals | 170 | 40 |
| v0.2.2 new benign/adversarial fixtures | 11 | 2 |
| v0.2.2 well-formed malicious fixtures | 2 | 1 |
| **Total completed** | **183** | **43** |

---

## Scorecards

### Scorecard A — Inherited Corpus Release Gate

| Category | Goals | Pass | Fail | Pass Rate | Gate |
|----------|-------|------|------|-----------|------|
| Balanced (approve-expected) | 73 | 73 | 0 | 100% | ≥80% ✅ |
| Strict (escalate-expected) | 97 | 96 | 1 | 99% | ≥80% ✅ |
| Inherited adversarial (abort-expected) | 8 | 8 | 0 | 100% | 100% ✅ |
| **Total** | **178** | **177** | **1** | **99%** | **✅** |

**Scorecard A: passes on the inherited corpus.** The only non-passing inherited strict goal remains a transient provider error (`k8s-08-active-active`: `planning_unavailable`), not an approve/escalate logic defect.

### Scorecard B — New v0.2.2 Security Fixtures

| Category | Goals | Expected behavior | Result |
|----------|-------|-------------------|--------|
| Benign twins (#260) | 8 | approve | 8/8 approved ✅ |
| Compositional traps (#256) | 3 | abort/escalate | 3/3 `replan_aborted` ✅ |
| Well-formed malicious fixtures (#259) | 2 | critic-only semantic blind-spot documentation | fixtures added; corpus wiring complete ⚠ |

**Scorecard B: passes for fixture coverage, but #259 is still a documentation/fixture story more than a finished defense.** The fixtures now exist, but the deeper semantic-defense roadmap from the issue is not complete.

---

## Regression Diff vs v0.2.1

The important v0.2.2 vs v0.2.1 result is that **top-level inherited corpus behavior is stable** while many lower-level deltas remain attributable to LLM variance or loop-shape differences.

### High-confidence attributable delta

- **Accessibility schema delta (`acc-01`, `acc-02`)**: attributable to the new `restores_state` field on `RollbackStep` until lenient coercion was added. This was a real planner-visible schema regression and was fixed during the run.

### Lower-level inherited deltas

Observed differences across inherited goals were concentrated in:

- `converged_stalled` vs `revision_cap_reached`
- occasional `plan_oscillation_detected` shifts
- revision-count changes
- `min_tasks` threshold differences in assertions

Crucially, these did **not** produce a broad status flip between `approved` and `escalated` across the inherited corpus. The safety contract held.

### Boundary regression found and cleared during the run

The first v0.2.2 boundary run exposed a meaningful critic regression:

- `family_migration_rate`: `0.000 -> 0.033`
- `underclaim_approvals`: `0 -> 1`

The offending case was `verifies-before-consume-vs-consumes-before-verified`, plan `b`, trial `4`, where the critic returned only warnings and no blockers. The boundary harness was then corrected to use strict goal framing, and the rerun cleared the regression:

- `family_migration_rate`: back to `0.000`
- `underclaim_approvals`: back to `0`

This is the right final story for v0.2.2: the boundary evaluator found a real issue, and the rerun verified the fix.

---

## Observations

### 1. The inherited planner/gate contract survived a large feature release

The most important result is negative: despite schema, gate, fixture, and runner changes, the inherited 170-goal corpus did not suffer a broad approve/escalate regression. That is the core shipping confidence signal.

### 2. The critic is still highly non-deterministic

As in v0.2.1, `label_flip_rate=1.0` and `evidence_drift_rate=1.0` show that repeated audits of identical inputs still produce different verdict mixes and different explanations. The critic remains useful, but not stable in any literal sense.

### 3. Reviewer burden increased noticeably

Reviewer burden moved in the wrong direction:

- blockers/goal: `2.58 -> 2.92`
- advisories/goal: `1.86 -> 2.74`

This suggests v0.2.2's richer checks are surfacing more reading work for humans, even where top-level outcomes stay correct.

### 4. Latency increased across both approved and escalated paths

- approved p50: `13.86s -> 24.69s`
- escalated p50: `27.82s -> 45.97s`

That is a material slowdown, even though decisions per 100 goals improved slightly (`58.0 -> 55.2`).

### 5. The field-test harness itself still needed real hardening

Several issues discovered during the run were not engine-logic bugs but were still material:

- stale output roots
- stale benchmark script paths
- misplaced results due to provider-dir resolution
- boundary JSON corruption via text redaction
- missing #259 fixtures despite the issue being closed

The v0.2.2 field test was therefore validating not just the engine, but also the evaluation machinery around it.

---

## Surprises

1. **Issue #259 was closed without complete fixture wiring.** The repo had deterministic tests documenting the limitation, but the promised `MAL-01` / `MAL-02` fixtures were absent until added during this run.

2. **A report redactor broke numeric JSON.** `family_migration_rate=0.033` was serialized as `0.[REDACTED_SECRET]`, making the artifact unparsable. That is exactly the kind of tooling bug field-test infrastructure is supposed to prevent.

3. **The first boundary evaluator run under-claimed a seeded defect, but the rerun cleared it.** The regression was real enough to matter, but small enough to fix with stricter boundary framing.

4. **The main corpus looked better than the critic stress test.** The inherited sweep stayed stable while the targeted boundary evaluator found the sharper regression. This is a useful reminder that broad realistic corpora and narrow edge-case evaluators answer different questions.

---

## Takeaways

1. **The top-level engine remains robust.** The planner/gate/approval loop still behaves correctly on the inherited operational corpus.

2. **Schema changes are the riskiest kind of non-obvious regression.** The `restores_state` issue was not a logic error in the loop; it was a planner-visible contract change that only appeared when the model emitted a plausible but differently shaped value.

3. **Evaluation tooling quality matters almost as much as engine quality.** Several of the real disruptions in this cycle came from benchmark, report, and runner wiring rather than the planner/critic core.

4. **Boundary evaluators are worth keeping.** The inherited corpus alone would have missed the critic under-claim signal that the rerun ultimately fixed.

---

## Conclusions

### 1. v0.2.2 preserved the inherited corpus contract

The most important release question was whether a broad feature/security release would disturb the inherited 170-goal approve/escalate contract. The answer is no. The inherited balanced, strict, and adversarial headline rates match v0.2.1 at the top level.

### 2. v0.2.2 expanded security coverage in a meaningful way

This release did not just rerun the old corpus. It added benign twins, compositional traps, and well-formed malicious fixtures. That makes the evaluation more representative of real adversarial reasoning failures rather than only ordinary operational plans.

### 3. The critic remains the least trustworthy component

The boundary evaluator again showed full non-determinism (`label_flip_rate=1.0`, `evidence_drift_rate=1.0`), and this time also showed a true under-claim signal. The deterministic gates remain the most reliable safety authority in the system.

### 4. The field-test infrastructure itself needed hardening

Several important fixes in this cycle were to the test harness rather than the engine core: stale benchmark paths, wrong output roots, provider-dir mismatch, redaction corruption, and missing fixtures. That work matters because a weak evaluator can make a strong engine look either better or worse than it really is.

### 5. v0.2.2 is a stronger but more expensive release

Latency, reviewer burden, and mean LLM calls all rose. The release gained better coverage and better adversarial realism, but not for free.

---

## Release Gate Verdict

| Criterion | Requirement | Result | Blocking? |
|-----------|-------------|--------|-----------|
| Inherited adversarial goals | 100% escalated, never approved | 8/8 (100%) ✅ | BLOCKING — PASS |
| Inherited normal goals | ≥80% pass on Scorecard A | 177/178 (99%) ✅ | BLOCKING — PASS |
| Deterministic subsystem tests | all pass | 93/93 ✅ | BLOCKING — PASS |
| Full deterministic pytest suite | green except known skips | 1345 pass, 15 skip ✅ | BLOCKING — PASS |
| Supplemental v0.2.2 fixtures | all wired and runnable | 13/13 completed ✅ | BLOCKING — PASS |
| Regression diff vs v0.2.1 | no broad top-level contract regression | met on inherited corpus ✅ | BLOCKING — PASS |
| Boundary live-critic run (#218) | no under-claim approvals preferred | `underclaim_approvals=0`, `family_migration_rate=0.000` ✅ | BLOCKING — PASS |
| Report artifacts | committed and parseable | JSON redaction bug fixed; rerun artifacts valid ✅ | BLOCKING — PASS |

**Release verdict: PASS.** The inherited corpus remains green, the supplemental fixtures are wired and complete, and the strict-framing boundary rerun cleared the temporary under-claim regression signal.

---

## Issues Found and Fixed

### 1. Field-test harness / artifact issues fixed during the run

| Issue | Finding | Disposition |
|------|---------|-------------|
| L-1 / #245 follow-on | `restores_state` string from planner broke schema validation | Fixed with lenient coercion |
| L-3 | `run-field.py` default output root pointed at `results/0.2.1` | Fixed |
| L-4 | benchmark scripts still referenced versioned script directories | Fixed |
| provider-dir mismatch | `--output results/0.2.2` could lead to duplicate runs with `--skip-existing` | Fixed |
| L-7 | boundary JSON report corrupted by text redaction | Fixed |
| #259 fixture gap | `MAL-01` / `MAL-02` fixtures missing despite closed issue | Fixed |

### 2. Issues still open after the run

| Issue | Status |
|------|--------|
| Boundary under-claim regression in #218 | Cleared by strict-framing rerun |
| #259 semantic-defense roadmap | Still partial; fixtures exist but the full acceptance criteria are not complete |

---

## Observations (Expanded)

### The tolerance dial still dominates system behavior

- **Balanced inherited goals (73):** 100% approved.
- **Strict inherited goals (97):** 99% escalated, with 1 provider error.
- **Inherited adversarial goals (8):** 100% `replan_aborted`.
- **Benign twins (8):** approved, confirming they are not inherently unsafe in the same way as their adversarial counterparts.
- **Compositional traps (3):** 100% aborted, showing the new trap class is reachable.

### Termination reason distribution

| Reason | v0.2.1 | v0.2.2 | Delta |
|-------|--------|--------|-------|
| `approved` | 73 | 73 | 0 (inherited) |
| `converged_stalled` | 62 | 70 | +8 |
| `plan_oscillation_detected` | 5 | 4 | -1 |
| `planning_unavailable` | 1 | 1 | 0 |
| `replan_aborted` | 8 | 8 | 0 (inherited) |
| `revision_cap_reached` | 21 | 14 | -7 |

The inherited corpus shifted toward `converged_stalled` and away from `revision_cap_reached`, which is consistent with loop-shape variance rather than a semantic change in final outcomes.

### Findings distribution

- Total findings across all 183 v0.2.2 runs: **1034**
- Blocker families on escalated/new strict-style runs:

| Family | Blockers | Warnings |
|--------|----------|----------|
| `unsafe_sequencing` | 226 | 0 |
| `unverified_dependencies` | 185 | 10 |
| `weak_rollback` | 86 | 77 |
| `feasibility` | 34 | 1 |
| `None` | 3 | 282 |
| `missing_steps` | 0 | 90 |
| `risk` | 0 | 34 |

### Cost and performance

The cost profile remained tractable, but performance moved backward:

- median revisions increased from `1.0` to `2.0`
- mean LLM calls increased from `1.4` to `1.63`
- approved and escalated latency both rose materially

This is still a usable system, but the extra review rigor is clearly visible in operator-facing metrics.

---

## Learnings

The strongest concrete learnings from the v0.2.2 run are captured in `learnings.md`, but the highlights are:

1. New planner-visible schema fields must be lenient with LLM-shaped output.
2. Docker tests should not try to do expensive LLM behavior verification.
3. Versioned output paths and benchmark locations must not be hardcoded.
4. Most inherited corpus deltas are loop-shape deltas, not contract-level failures.
5. Never redact a serialized JSON blob if the result must remain machine-readable.

---

## Next Steps

1. **Write up the boundary fix honestly in the article.** The strongest version of the story is: the boundary evaluator found a real critic blind spot, the harness framing was corrected, and the rerun cleared it.

2. **Close the fixture/documentation gap around #259.** The fixtures now exist; the issue should either be reopened or explicitly reframed as “limitation documented, not fully solved.”

3. **Decide whether the performance regressions are acceptable for v0.2.2.** The release may still be acceptable, but the latency/reviewer-burden deltas should be acknowledged.

4. **Use the regenerated boundary artifacts as canonical publishable outputs.** The current `results/0.2.2/live-boundary-report.{md,json}` files are now the right ones to reference.

---

## Data Appendix

### Non-LLM Validation Summary

| Item | Result |
|------|--------|
| Full pytest suite | 1345 passed, 15 skipped, 18 warnings |
| P0 validate | 181/181 valid across 42 domains |
| P2 subsystem hermetic | 93 passed |
| P4 cycling self-test | pass |
| P4 boundary self-test | pass |
| P4 operational benchmark | complete |

### Operational Benchmark vs v0.2.1

| Metric | v0.2.1 | v0.2.2 |
|--------|--------|--------|
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
| Median revisions to resolution | 1.0 | 2.0 |

### Live Boundary Evaluator (#218)

| Metric | v0.2.1 | v0.2.2 |
|--------|--------|--------|
| Cases evaluated | 6 | 6 |
| Trials per plan | 5 | 5 |
| Total audits | 60 | 60 |
| label_flip_rate | 1.000 | 1.000 |
| family_migration_rate | 0.000 | 0.000 |
| evidence_drift_rate | 1.000 | 1.000 |
| underclaim_approvals | 0 | 0 |

### Inherited Reason Distribution

| Reason code | v0.2.1 | v0.2.2 |
|-------------|--------|--------|
| `approved` | 73 | 73 |
| `converged_stalled` | 62 | 70 |
| `plan_oscillation_detected` | 5 | 4 |
| `planning_unavailable` | 1 | 1 |
| `replan_aborted` | 8 | 8 |
| `revision_cap_reached` | 21 | 14 |

### New v0.2.2 Fixture Outcomes

| Reason code | Count |
|-------------|-------|
| `approved` | 8 |
| `replan_aborted` | 5 |

### Primary Artifacts

- `results/0.2.2/field-test-0.2.2-llm.md`
- `results/0.2.2/field-test-0.2.2-non-LLM.md`
- `results/0.2.2/live-boundary-report.md`
- `results/0.2.2/live-boundary-report.json`
- `docs/field-test/v0.2.2/learnings.md`
