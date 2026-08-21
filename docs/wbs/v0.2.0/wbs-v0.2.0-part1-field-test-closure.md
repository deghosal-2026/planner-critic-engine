# WBS — PlannerCritic Engine v0.2.0 Part 1: Field-Test Closure of v0.1.0

> **Milestone covered:** M1 (Field-Test Closure of v0.1.0)
> **PRD covering this milestone:** [07-success-metrics](../../design/prd/07-success-metrics.md) (§7.1) · [08-risks](../../design/prd/08-risks.md) · [09-roadmap §9.2](../../design/prd/09-roadmap.md#92-v020-p1)

---

## Milestone 1: Field-Test Closure of v0.1.0

**Objective:** Before building any v0.2.0 feature, close every not-run / deferred / partial capability left in the shipped v0.1.0. The v0.1.0 field test graded the engine on structure (gates, reason codes, termination) but several capabilities ran on a subset of goals or were never run end-to-end against a real LLM. M1 turns every "not run" / "pass*" / "partial" row into a measured fact so v0.2.0 is built on a proven base.

**PRD coverage:** §7.1 success criteria roll-up; §08 risk evidence; C2/C4/C5/C6/C7/C9–C18/C20–C30 capability matrix.
**CUJs covered:** all P0 re-verified end-to-end (1–11, 13–15).

### M1 Key Items (the closure set, grouped from the 0.1.0 report gaps)

| Source gap | 0.1.0 report finding | Closure |
|---|---|---|
| CLI surface (C5, C20–C23) | `demo`/`quickstart`/`migrate` return non-zero; "not run — deferred" | #85 — exercise full CLI against real LLM (DB-01, K8S-01, corpus, temp dir) |
| HTTP + MCP surfaces (C6, C7, C26, C27) | "not run — deferred to M10" | #86 — full endpoint matrix + stdio/HTTP parity + bootstrap |
| Adapter coverage (C12, C28) | only raw-Python ran (1 adapter × 1 goal) | #87 — 2 goals × 6 adapters × wrap/unwrap + audit trail |
| Critique-mode matrix (C2) | only db-01 ran all 3 modes (3/12) | #88 — add K8S-01, IR-01, CI-01 × 3 modes = 12/12 |
| Escalation / Explain / Replan (C9, C10, C11, C25) | partial coverage, tested on wrong goals | #89 — deny path, escalated-explain, restart on ARCH-01, replan lineage |
| Never-exercised capabilities (C13, C14, C16, C18, C19, C24) | re-gate/forensics/shadow/TTL/probe-kind/schema-migrate never run; db_query+deploy_status stubs | #90 — run all 6; fix probe stubs |
| Cross-dimension correctness (C15, C17, C30) | replay empty, complexity only db-01, no reason-code catalog sweep | #91 — persistence fix, K8S-01 complexity, catalog sweep, assertion pre-validation |
| Loop/budget/termination depth (C29, C4) | only max_revisions ceiling; `regression_thrashing` never produced | #92 — all 3 ceilings, induce regression, 31-goal strict cap=4 sweep |
| Model & robustness sweeps | single model, healthy endpoint only | #93 — cross-model, fail-closed injection, local-model dimension, concurrency |
| §1 Q3 finding quality | noise rate never measured | #97 — classify all 65 goals' findings; noise top-10; injection-bypass rescan |
| §1 Q4 executor-usability | executability never validated | #98 — preconditions grounding + fresh-executor dry-run pass on 6 approved plans |
| Failure clustering | reviewer asked "did planning failures cluster by task kind?" — current matrix lacks failure-kind tabulation | #173 — tag rows by failure shape; report whether signal is domain- or shape-driven |
| Methodological control | field-doc reader noted strict-arm 81 goals/35 domains show zero variance | #172 — a known-clean golden plan run through strict to prove discriminating power |

### M1 Task Checklist

> Each task maps to one issue. Status checkboxes track progress; the exit gate below is the completion bar.

| # | Task | Build (files/docs) | Behavior + verify | Issue | Status |
|---|------|--------------------|-------------------|-------|--------|
| 1 | CLI surface coverage | `docs/field-test/reports/0.1.0/cli-surface/` + fixes | Every command exit 0; `plan` output structurally matches programmatic API; replay covers all revisions | [#85](https://github.com/deghosal-2026/planner-critic-engine/issues/85) · [ ] |
| 2 | HTTP + MCP surfaces | `.../http-surface/`, `.../mcp-surface/`, `.../mcp-http-surface/`, `.../bootstrap/` | All endpoints 200; diff non-empty; MCP stdio ∥ HTTP parity; bootstrap round-trips | [#86](https://github.com/deghosal-2026/planner-critic-engine/issues/86) · [ ] |
| 3 | Adapter coverage | `.../adapters/<goal>/<adapter>/` | 6 adapters × 2 goals produce valid PlanVersion; wrap/unwrap structural equality; audit trail | [#87](https://github.com/deghosal-2026/planner-critic-engine/issues/87) · [ ] |
| 4 | Critique-mode matrix | `.../critique-modes/{k8s-01,ir-01,ci-01}/<mode>/` | 12/12; heuristic-only 0 LLM; deterministic-first LLM iff gate-clean; llm-every-revision findings every revision | [#88](https://github.com/deghosal-2026/planner-critic-engine/issues/88) · [ ] |
| 5 | Escalation/Explain/Replan | `.../{escalation,explain,replan}/` | approve+deny round-trip; escalated-explain (replan_aborted); restart fresh plan+chain (#C25) | [#89](https://github.com/deghosal-2026/planner-critic-engine/issues/89) · [ ] |
| 6 | Never-exercised capabilities | probe fixes + `.../{rogate,forensics,shadow,ttl,schema-migrate}/` | re-gate fires replan; forensics linked; shadow zero-footprint; TTL within 1s; probes real; migrate lossless | [#90](https://github.com/deghosal-2026/planner-critic-engine/issues/90) · [ ] |
| 7 | Cross-dimension correctness | persistence fix + assertion-validator command | replay non-empty; complexity on K8S-01; reason-code catalog 100% produced; 65/65 assert valid | [#91](https://github.com/deghosal-2026/planner-critic-engine/issues/91) · [ ] |
| 8 | Loop/budget/termination depth | `.../{budget,termination}/` | 3 ceilings each produce `budget_exceeded`; `regression_thrashing` produced; 28+/31 strict converged_stalled | [#92](https://github.com/deghosal-2026/planner-critic-engine/issues/92) · [ ] |
| 9 | Model & robustness sweeps | `.../{multi-model,failclosed,local-model,concurrency}/` | cross-model adversarial 5/5 escalate; fail-closed `planning_unavailable`; local-model recorded; no store corruption | [#93](https://github.com/deghosal-2026/planner-critic-engine/issues/93) · [ ] |
| 10 | Finding-quality audit (Q3) | `docs/field-test/field-test-results-0.1.0.md` | % noise/specific/actionable/task-linked for all 65; noise top-10 cited; injection-bypass noted | [#97](https://github.com/deghosal-2026/planner-critic-engine/issues/97) · [ ] |
| 11 | Executor-usability audit (Q4) | `.../field-test-results-0.1.0.md` | deterministic grounding on 29 approved; ≥80% walkable; gap inventory + evidence | [#98](https://github.com/deghosal-2026/planner-critic-engine/issues/98) · [ ] |
| 12 | Failure-shape clustering analysis | `docs/field-test/0.1.0-failure-clustering/` | tag rows by failure shape; report answers domain-vs-shape; cheap rule-based heuristic | [#173](https://github.com/deghosal-2026/planner-critic-engine/issues/173) · [ ] |
| 13 | Positive-control test | `.../0.1.0-positive-control/` + matrix control row | known-clean plan under strict unmodified; result recorded whether or not surprising | [#172](https://github.com/deghosal-2026/planner-critic-engine/issues/172) · [ ] |

### M1 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| Capability closure | 0 rows left as "not run" / "pass*" / "deferred" | field-test report audit |
| CLI fidelity | every command exit 0; plan output structurally matches API | CLI suite |
| MCP parity | stdio ∥ HTTP byte-consistent | parity test |
| Reason-code catalog | 100% of catalog produced across sweep | C30 sweep |
| Failure-cluster analysis | every row tagged; report answers domain-vs-shape | clustering report |
| Positive control | known-clean plan result recorded, whatever it shows | control row in matrix |
| Coverage | >95% | `--cov-fail-under=95` |
| Lint | 0 ruff + 0 mypy strict | `ruff` + `mypy` |

### M1 Exit Gate

- [ ] All v0.1.0 field-test gaps closed; report rows no longer "not run"/"pass*"/partial
- [ ] Coverage > 95; lint clean (ruff + mypy strict); code review passed
- [ ] Hermetic gate holds: CI never calls a paid LLM
- [ ] **Design doc authored:** D24 (if not yet), fix field-test harness + assertion pre-validation

**Dependency:** v0.1.0 (shipped). **Produces for M2+:** a fully-measured, proven v0.1.0 base on which all v0.2.0 features build.