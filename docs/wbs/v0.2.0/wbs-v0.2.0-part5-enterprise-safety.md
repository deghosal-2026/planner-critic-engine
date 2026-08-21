# WBS — PlannerCritic Engine v0.2.0 Part 5: Enterprise-Scale Safety

> **Milestone covered:** M6 (Enterprise-Scale Safety)
> **PRD covering this milestone:** [02-architecture](../../design/prd/02-architecture.md) (§2.6 posture, §2.7 plan store, §2.9 operators) · [06-security](../../design/prd/06-security-baseline.md) (compliance) · [07-success-metrics](../../design/prd/07-success-metrics.md)

---

## Milestone 6: Enterprise-Scale Safety

**Objective:** Make the engine safe to run as a **fleet** — multi-agent, multi-tenant, budgeted, auditable. M6 pairs the deterministic *counterparts* to the existing LLM heuristics (posture instead of a static flag; hard quotas instead of the LLM's subjective blast-radius judgment) with the guards that matter for shared/clustered environments: run-level cost ceilings, state isolation/locking, precinct against context-compaction precondition loss, and secret/PII redaction. Parallelizable with M7/M8. Consumes M4 pack registries for quotas and rollback.

**PRD coverage:** F-13 budget (extended to run-level), F-15 parallel semantics (extended cross-plan), F-19 EnvProbe, F-46 re-gate, F-82 OTel, §2.6 posture.
**CUJs covered:** CUJ 7 (escalation), enterprise platform-lead + on-call personas.

### M6.1 Dynamic risk-posture switching (#132)

- `PostureResolver`: ordered `{match, posture}` rules over runtime context (env vars, k8s namespace, git branch, deploy target); first match wins; fallback to goal-declared posture (backward-compatible).
- Adds the missing **`permissive`** tier: warnings tolerated without ack; **blockers never overridden** (fail-closed F-73 holds in all tiers).
- Trace records resolved posture + matching rule + context signal (audit). CLI: `plancritic plan --posture-rules-file` / `--posture`.

### M6.2 Run-level cost ceilings + transient-vs-deterministic replan gates (#149)

- `RunBudget`: `run_max_budget_usd`, `run_max_depth` (cascading replans), `run_max_time` — enforced **above** per-goal F-13 budget; tracked in store; hit → hard escalation.
- `ReplanClassifier`: transient (retry+backoff, no replan) vs deterministic (replan F-16) vs ambiguous (escalate); verdict recorded in execution trace (F-50). Per-step retry budget `step_max_retries`; `run_max_depth` limiter.
- Reason codes: `run_budget_exceeded`, `run_depth_exceeded`, `run_timeout`, `transient_retry_triggered`, `deterministic_replan_triggered`, `ambiguous_replan_escalated`, `step_retry_budget_exceeded`.
- Stops the "27 LLM calls for a 5-second blip" cascading-retry amplification.

### M6.3 State locking & isolation views (#150)

- `StateView`: immutable read-only snapshot taken at approval time; critic + `EnvProbe` read from it, not live mid-mutation state; versioned in store; `state_view_stale` on divergence (feeds F-46 re-gate → replan).
- `StateLock`: resource-URI-based write coordination (`lock_strategy: wait|fail_fast|escalate`); `resource_locked_by_concurrent_execution` blocker; cross-plan active-execution registry + pre-execution conflict detection (`concurrent_resource_conflict`; Risk-family variant).

### M6.4 Persistent precondition ledger (#151)

- `PreconditionLedger`: deterministic KV store `{key: {satisfied, satisfied_by, satisfied_at, verified_by}}` in the plan store; survives context compaction; injected to the planner as structured context (not a compactable message).
- Gates query the **ledger**, not LLM memory (F-12 `preconditions_referenced` correctness on revision N+1). Compaction detection: `precondition_redundantly_re_injected` (info), `precondition_dropped_from_compaction` (warning).
- Cross-revision persistence; auditable per-revision ledger state.

### M6.5 Multi-tenant state sandboxing & blast-radius quotas (#158)

- `BlastRadiusQuota`: hard operator-defined limits — `max_resource_changes`, `max_destructive_actions`, `max_database_alterations`, `restricted_clusters`, `restricted_actions`.
- Pre-LLM deterministic enforcement: breach → blocker + **auto-injected approval escalation** (F-30); `blast_radius_quota_breach` / `blast_radius_restricted_cluster` / `blast_radius_restricted_action`. Interaction with posture: strict → always blocker+escalate; permissive → warning (but restricted_* still escalate).
- CLI: `plancritic quota list/set/check`.

### M6.6 Secret & PII redaction filter (#159)

- `SecretsRedactor`: deterministic interception at every external-output surface (LLM call, plan store, OTel F-82, CLI, `diagnose`, `studio`). Built-in patterns (AWS keys, API keys ≥16, OAuth2, JWT, private keys, Slack tokens, GH PATs, email, phone, SSN) + custom regex via `secrets.yaml`.
- Modes `redact` / `hash` (SHA-256, for dedup) / `skip` (per pattern). Audit trail logs redaction counts without the secret; `secret_redacted` (info) reason code. SOC 2 / HIPAA / GDPR / ISO 27001 compliance story; never sends content to an external classifier.

### M6.7 Gate rationale as first-class metadata (#174)

- Every gate definition carries `{author, rationale, added_at, stale_at, amend_conditions}` as first-class schema fields.
- Rationale surfaced in escalation, explain, and dashboard surfaces (#53 HTTP, #51 explain, #138) so a gate is never a silent verdict.
- Planner can introspect rule rationale at runtime to reason about a constraint rather than just being blocked by it.
- Stale-rule signal flags a gate when the evidence/precondition cited in its rationale has moved since `added_at`, triggering re-review. Prevents permanent silent dead-ends.

### M6 Task Checklist

| # | Task | Verify | Issue | Status |
|---|------|--------|-------|--------|
| 1 | PostureResolver + permissive tier + trace audit | ENV=production→strict; dev→permissive; blocker never overridden | [#132](https://github.com/deghosal-2026/planner-critic-engine/issues/132) · [ ] |
| 2 | RunBudget + ReplanClassifier + retry/depth limits | transient→retry not replan; deterministic→replan; ceilings escalate | [#149](https://github.com/deghosal-2026/planner-critic-engine/issues/149) · [ ] |
| 3 | StateView + StateLock + cross-plan registry | concurrent same-resource blocked; critic reads consistent snapshot | [#150](https://github.com/deghosal-2026/planner-critic-engine/issues/150) · [ ] |
| 4 | PreconditionLedger + compaction detection | 5-rev plan survives compaction; gate checks ledger | [#151](https://github.com/deghosal-2026/planner-critic-engine/issues/151) · [ ] |
| 5 | BlastRadiusQuota + auto-escalation | quota breach blocked pre-LLM; restricted_* escalate | [#158](https://github.com/deghosal-2026/planner-critic-engine/issues/158) · [ ] |
| 6 | SecretsRedactor + patterns + modes + audit | secret stripped before all external surfaces; counts w/o value | [#159](https://github.com/deghosal-2026/planner-critic-engine/issues/159) · [ ] |
| 7 | Gate rationale metadata + stale-rule signal | every gate has author+rationale+added_at; stale gates surfaced | [#174](https://github.com/deghosal-2026/planner-critic-engine/issues/174) · [ ] |

### M6 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| Posture correctness | rules resolve + permissive tier valid; blockers never relaxed | posture suite |
| Run-budget | ceilings escalate; retry vs replan classified and traced | run-budget field test |
| State isolation | concurrent-plan no race; stale snapshot → replan | state suite |
| Ledger | accuracy across 5+ revisions w/ compaction | ledger field test |
| Quota | breach blocked pre-LLM; restricted actions escalate | quota field test |
| Redaction | 0 secrets in any external output; audit counts only | redaction suite |
| Gate rationale | every gate has author+rationale+added_at; stale signal surfaces in dashboard | schema audit + dashboard query |
| Coverage | >95% | `--cov-fail-under=95` |
| Lint | 0 ruff + 0 mypy strict | `ruff` + `mypy` |

### M6 Exit Gate

- [ ] All six safety mechanisms enforced deterministically (no LLM requirement to trigger)
- [ ] Gate rationale metadata shipped: every gate carries author+rationale+added_at; stale signal surfaces
- [ ] **Design doc authored:** D24 (enterprise safety)
- [ ] Every new reason code in catalog (F-77)
- [ ] Coverage > 95; lint clean; code review passed

**Dependency:** M1 (+ M4 pack registries for quotas/rollback). **Produces for M7–M10:** the safety layer `plancritic check`/CI/studio surfaces run against, and the compliance evidence M10 security posture needs.