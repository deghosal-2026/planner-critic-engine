# WBS — PlannerCritic Engine v0.2.2-M4: Operational & Audit

> Part of the v0.2.2 release. See [index](wbs-v0.2.2-index.md) for milestone overview and dependency graph.
>
> **Branch:** `rel-0.2.2` · **Milestone:** [v0.2.2-M4 Operational & Audit](https://github.com/deghosal-2026/planner-critic-engine/milestone/18)
>
> **Scope:** Observability, operational improvements, and audit-trail integrity. All ship with before/after metrics.

---

## Overview

M4 adds operational improvements that make the engine more observable, auditable, and cost-efficient. It includes the escalation audit trail, cost-vs-rigor guardrails, adaptive revision cap, multi-model comparison, critic satisfaction signals, critic/planner tier split, and downstream-error-rate measurement.

| Issue | Title | Area | Complexity |
|-------|-------|------|------------|
| #250 | Downstream-error-rate measurement via partner-runner integration | engine/testing | medium |
| #251 | Adaptive revision cap for strict goals | engine | medium |
| #252 | Multi-model planner comparison | testing | high |
| #254 | Critic satisfaction signals | critique | medium |
| #257 | Critic/planner capability tier split | engine/critique | medium |
| #261 | Escalation audit trail — actor, explain, identity plumbing | escalation | medium |
| #262 | Cost-vs-rigor guardrails — immutable gate config | engine | medium |

---

## #250 — [v0.2.2] Downstream-error-rate measurement via partner-runner integration

**Problem:** The engine deliberately stops at approval — it does not execute plans. Therefore, it cannot measure whether an approved plan, when executed by a downstream runner, actually succeeds or fails. This downstream error rate is the most important operational metric the engine cannot produce solo.

**Fix:**
1. Define the measurement spec: what trace fields a partner runner must emit for downstream error rate to be computed
2. Define the integration point: how a partner runner sends execution results back to the engine
3. Publish the spec as a reference document for runner partners
4. The measurement itself is deferred to partner-runner implementation, but the spec is ready

**Completion checklist:**
- [ ] Downstream-error-rate measurement spec published
- [ ] Required trace fields documented (plan_id, goal_id, execution_status, error_type, duration)
- [ ] Integration point defined (webhook callback, store append, or API endpoint)
- [ ] Spec reviewed and ready for partner-runner consumption
- [ ] F-07 in failure-mode register updated

---

## #251 — [v0.2.2] Adaptive revision cap — detect strict goals and reduce the cap to 1

**Problem:** Strict goals under the LLM critic always escalate (v0.1.0 field test: 81/81 strict goals escalated). The revision loop is wasted on strict goals because the critic will always find a finding. Reducing the revision cap to 1 for strict goals saves LLM calls without changing outcomes.

**Fix:**
1. Detect strict goals at run start (from `goal.risk_tolerance`)
2. Reduce the revision cap to 1 for strict goals
3. Measure cost savings on the 170-goal corpus
4. Document the behavior change

**Completion checklist:**
- [ ] Strict goals detected at run start
- [ ] Revision cap reduced to 1 for strict goals
- [ ] Corpus regression: strict goals still escalate (100%)
- [ ] Cost savings measured and reported
- [ ] Balanced goals unaffected (revision cap unchanged)
- [ ] F-10 in failure-mode register updated

---

## #252 — [v0.2.2] Multi-model planner comparison — gpt-4o, claude-3.5, deepseek-v4 against the same 170-goal corpus

**Problem:** Article 3 showed that gpt-4o as planner produced the same defect families as gpt-4o-mini — better prose, same structural mistakes. This needs to be validated across more model families to confirm the "planning is a structural problem, not a model-size problem" thesis.

**Fix:**
1. Run the same 170-goal corpus through three planner models: gpt-4o, claude-3.5 Sonnet, deepseek-v4
2. Use the same critic model for all three runs (control the critic variable)
3. Measure: pass/fail rate, cost per goal, defect family distribution, revision counts
4. Publish the comparison

**Completion checklist:**
- [ ] gpt-4o run completed on 170-goal corpus
- [ ] claude-3.5 Sonnet run completed on 170-goal corpus
- [ ] deepseek-v4 run completed on 170-goal corpus
- [ ] Same critic model used for all three runs
- [ ] Pass/fail rate, cost, defect families, and revision counts reported
- [ ] Results published in release notes
- [ ] Total cost tracked and reported

---

## #254 — [v0.2.2] Critic satisfaction signals — allow strict goals to approve when the critic explicitly endorses the plan

**Problem:** Strict mode currently escalates any plan where the critic produces a finding. But if the critic explicitly says "this plan is good" — a positive endorsement — the plan should be approvable even under strict mode. The current binary (any finding → escalate) is too conservative.

**Fix:**
1. Define a "critic satisfaction" signal: when the critic produces zero blocker findings AND explicitly endorses the plan, the plan can approve under strict mode
2. The endorsement must be explicit (not just absence of findings) — the critic must state "this plan is safe to execute"
3. Measure how many strict goals become approvable under this signal
4. Ensure no under-claim: the deterministic gates still run before the critic

**Completion checklist:**
- [ ] Critic satisfaction signal defined (explicit endorsement, not just absence of findings)
- [ ] Strict mode accepts endorsement as approval condition
- [ ] Deterministic gates still run before the critic (no under-claim risk)
- [ ] Corpus regression: goals that previously escalated now approve if critic endorses
- [ ] Corpus regression: goals with blocker findings still escalate
- [ ] Zero under-claims: no unsafe plan approved via critic satisfaction
- [ ] Results published

---

## #257 — [v0.2.2] Critic/planner capability tier split — route planner and critic to different model tiers

**Problem:** The two-LLM split (planner + critic) currently routes both roles to the same model tier. This misses the opportunity to optimize cost and security separately: the planner can be cheap and fast, while the critic — the layer that must catch blind spots and resist injection — should be held to a higher bar.

**Proposed by:** TokenLat (dev.to article 9 comments)

**Fix:**
1. Separate model configuration for planner and critic: `planner.model` and `critic.model` config keys
2. Benchmark across 3 tier combinations: same model (baseline), cheap planner + expensive critic, expensive planner + cheap critic
3. Measure pass/fail rate, cost per goal, and adversarial-goal escalation rate

**Completion checklist:**
- [ ] Separate `planner.model` and `critic.model` config keys added to `plancritic.toml` and `Goal`
- [ ] Benchmark across 3 model-tier combinations on the 170-goal corpus
- [ ] Cost-per-goal and pass-rate comparison published
- [ ] If the split reduces critic non-determinism or improves injection resistance, update the architecture docs and default config

---

## #261 — [v0.2.2] Escalation audit trail — actor field, explain output, and identity plumbing across all approve surfaces

**Problem:** The escalation path has three gaps in the audit trail:
1. **No actor field**: `Escalation` carries `status`, `resolution`, and `resolved_at` — but no `resolved_by`. Who approved is never persisted.
2. **build_explain returns "Escalated" after resolution**: It branches on the escalation *existing* and never on `escalation.status`. An approved escalation still shows "Escalated."
3. **Identity plumbing**: CLI/HTTP/MCP all pass `principal=None`, so `approving_authority` enforcement is unreachable.

**Identified by:** ANP2 Network (dev.to article 9 comments)

**Fix:**
1. Add `resolved_by: Optional[str]` to `Escalation` type, populate on every `resolve()` call
2. Update `build_explain` to check `escalation.status`: "Approved after escalation," "Rejected after escalation," or "Escalated"
3. CLI/HTTP/MCP all accept and forward `principal` to `EscalationManager.resolve()`

**Completion checklist:**
- [ ] `Escalation.resolved_by` field exists and is populated on resolve
- [ ] `build_explain` returns accurate status for all three resolution states
- [ ] CLI `escalate approve --principal <name>` works and enforces `approving_authority`
- [ ] HTTP approve endpoint accepts and forwards `principal`
- [ ] MCP approve tool accepts and forwards `principal`
- [ ] Existing tests pass with `principal=None` behavior preserved when no authority is configured

---

## #262 — [v0.2.2] Cost-vs-rigor guardrails — prevent skipping deterministic gates on simple goals

**Problem:** Cost-constrained or latency-sensitive deployments are tempted to weaken critic strictness, cap replan iterations, or skip the critic entirely on "simple" goals. Each shortcut reopens the surface the architecture was designed to close. The security contract and the budget contract are in tension, and the right knob is not "how strict is the critic" but "which path is allowed to skip the deterministic gates" — and the answer should be *none of them*.

**Proposed by:** Dean Lee (dev.to article 9 comments) and the article's own cost-vs-rigor analysis

**Fix:**
1. Add `gates.required` config section that cannot be overridden at goal time
2. Startup warning logged when any gate is disabled
3. Engine refuses to start when all gates are disabled
4. Budget config affects only critic iterations and replan caps — never the deterministic gate pass
5. "Simple" goal fast path: gates always run, critic may be skipped with warning

**Completion checklist:**
- [ ] `gates.required` config section added and enforced
- [ ] Startup warning logged when any gate is disabled
- [ ] Engine refuses to start when all gates are disabled
- [ ] Budget config cannot disable gates (documented invariant)
- [ ] "Simple" goal fast path: gates always run, critic may be skipped with warning
- [ ] Test: config with `gates.required.precondition_closer = false` raises error on engine start
- [ ] Test: budget overrides do not affect gate execution

---

## M4 Closure Gate

Before M4 closes, the following must be true:

### Standard milestone exit gate
- [ ] **Code review**: all M4 changes reviewed, no P1/P2 findings
- [ ] **Lint clean**: `ruff check src/ tests/` + `ruff format --check` 0 errors
- [ ] **Type check**: `mypy --strict src/ tests/` 0 errors
- [ ] **Test coverage**: `pytest --cov=src/ --cov-report=term` reports >90%
- [ ] **Documents updated**: all docs affected by M4 changes are current (operational docs, audit docs, config docs)
- [ ] **Clean checkin**: no debug code, no print statements, no TODOs

### M4-specific closure
- [ ] All 7 issues closed with evidence
- [ ] Escalation audit trail complete (actor, explain, identity plumbing)
- [ ] Cost-vs-rigor guardrails prevent deterministic gate skipping
- [ ] Adaptive revision cap saves LLM calls on strict goals
- [ ] Multi-model comparison results published
- [ ] Critic satisfaction signal working with zero under-claims
- [ ] Critic/planner tier split configurable and benchmarked
- [ ] Downstream-error-rate measurement spec published
- [ ] Full test suite passes on `rel-0.2.2` after M4 merge