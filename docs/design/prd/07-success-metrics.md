# 07 — Success Criteria & Reliability

> Sub-document of the [PlannerCritic Engine PRD](../PRD.md).

## 7.1 Success criteria (by v0.1.0 release)

1. **Adoption friction:** `pip install planner-critic` → register provider → first approved plan < 10 minutes for a reader (target < 5 min with the demo trace).
2. **Blocker-detection rate:** on the demo corpus's seeded-flaw goals, the critic surfaces the seeded flaw in ≥ 90% of runs (across provider backends in the field sweep).
3. **Loop correctness:** every goal either converges to a threshold-satisfying approval or escalates with a precise question — 100% on the deterministic CI gate; ≥ 95% on the live field sweep.
4. **Escalation precision:** escalations carry a single minimal question resolvable with one decision (approve/deny/patch) — audited in tests.
5. **Framework coverage:** all six adapters exercise plan → approve → (re-gate) → execute in their native frameworks in the field-test report.
6. **Cost:** the entire HTTP/CLI/deterministic test suite runs with $0 LLM spend (hermetic CI gate); the field sweep runs on a local model.
7. **Forensics value:** plan–execution failure classification and missed-critique records are queryable from the store for any approved plan.
8. **Determinism:** loop-controller decisions are deterministic on identical inputs (CI-asserted, F-74).
9. **Revisions-to-approval distribution:** median revisions-to-approval ≤ 2 on the demo corpus; tail tracked.
10. **Budget integrity:** zero runs exceed their declared `constraints.budget`; budget-hit escalations audited in CI.
11. **Replay & viz:** any stored plan can be replayed (`plancritic replay`) and its task DAG rendered (`--graph`) — demo/article enablers.

OSS community (post-launch): 25+ stars, 3 external contributors, 1+ external framework-ecosystem adoption per quarter.

## 7.2 Reliability & support

- **Fail-closed contract:** an unapproved plan can never reach an executor; a provider failure produces a distinct `planning_unavailable` failure mode per role; no "guess and continue" path.
- **Determinism:** the loop controller is deterministic on identical inputs; the LLM is only ever advisory in the critique/planner roles and its structured output is schema-revalidated.
- **Cheap by design:** deterministic gate first, local model default, hermetic CI gate — no paid LLM on the default path or in CI.
- **Plan store is a side channel** (planning continues in memory if the store is down, with a warning); persisted when healthy.
- **Support doc, CONTRIBUTING gate** (tests/coverage/mypy), CHANGELOG policy (per portfolio convention).