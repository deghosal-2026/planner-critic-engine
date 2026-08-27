# WBS — PlannerCritic Engine v0.2.2-M3: Security & Injection Resistance

> Part of the v0.2.2 release. See [index](wbs-v0.2.2-index.md) for milestone overview and dependency graph.
>
> **Branch:** `rel-0.2.2` · **Milestone:** [v0.2.2-M3 Security & Injection Resistance](https://github.com/deghosal-2026/planner-critic-engine/milestone/17)
>
> **Scope:** Adversarial and injection hardening. All injection tests must pass with 100% escalation rate.

---

## Overview

M3 closes the open security surfaces identified in the dev.to article 9 injection post and the community review. It adds indirect-injection defense, compositional injection traps, benign-twin controls, well-formed malicious plan detection, and wires the `approving_authority` through all shipped surfaces.

| Issue | Title | Area | Complexity |
|-------|-------|------|------------|
| #238 | Wire approving_authority through CLI/HTTP/MCP | escalation | medium |
| #249 | Indirect-injection defense — typed tool-result provenance | security | high |
| #253 | Fix field_test_harness escalation auto-approve | testing | low |
| #256 | Compositional injection traps | security/testing | high |
| #258 | Capability-scoped state transitions | security | high |
| #259 | Well-formed malicious plan detection | security/gates | high |
| #260 | Benign-twin control for adversarial goals | security/testing | medium |

---

## #238 — [v0.2.2][CodeReview] escalation surfaces: approving_authority never wired in CLI/HTTP/MCP; revise_contract has no production caller

**Problem:** The `approving_authority` enforcement is test-proven (#215) but not reachable from any shipped surface. The CLI (`cli/escalate.py`), HTTP server (`server/http.py`), and MCP tools (`server/mcp_tools_escalate.py`) all construct `EscalationManager(store)` without `approving_authority`, so wrong-principal `PermissionError` rejection is dormant outside direct API/tests.

**Identified by:** ANP2 Network (dev.to article 9 comments) and CodeReview #238

**Fix:**
1. **CLI**: Add `--principal` argument to `escalate approve` subparser
2. **HTTP**: Add `principal` field to the approve request body schema
3. **MCP**: Add `principal` parameter to `escalate_approve` tool signature
4. All three surfaces: pass the received principal to `EscalationManager.resolve()`
5. Existing tests (including #215 authority tests) pass
6. Regression: all existing escalation tests pass with `principal=None` behavior preserved when no authority is configured

**Completion checklist:**
- [ ] CLI `escalate approve --principal <name>` works and enforces `approving_authority`
- [ ] HTTP approve endpoint accepts and forwards `principal` in request body
- [ ] MCP approve tool accepts and forwards `principal` parameter
- [ ] All three surfaces pass principal to `EscalationManager.resolve()`
- [ ] #215 authority tests pass with principal
- [ ] Existing escalation tests pass with `principal=None` (backward compatible)
- [ ] F-14 in failure-mode register updated to "resolved"

---

## #249 — [v0.2.2] Indirect-injection defense — typed tool-result provenance + capability-scoped state transitions

**Problem:** Every injection test in the article 9 series injected the payload in the *initial goal text*. Indirect prompt injection — where the agent pulls malicious instructions from a fetched webpage, a compromised database record, or an untrusted API response midway through execution — is an entirely different threat surface. If a tool output contains a well-crafted payload, the planner may incorporate it into a sub-plan that the critic's initial semantic check never sees, because the payload entered *after* the goal was audited.

**Fix:**
1. Tool results carry typed provenance (source channel, trust level, content hash)
2. Deterministic policy gates check whether a given source channel may influence a given state transition
3. Untrusted sources (e.g., fetched web pages) cannot influence approval, payment, or deployment transitions
4. Integrated with capability-scoped state transitions (#258) for the full defense

**Completion checklist:**
- [ ] Tool-result provenance schema defined and implemented
- [ ] Each tool declares its source channel and trust level
- [ ] Deterministic policy gates check provenance on every transition
- [ ] Untrusted sources blocked from sensitive transitions
- [ ] Integration test: indirect injection via tool output is blocked
- [ ] Corpus regression green
- [ ] Documentation updated with indirect-injection defense architecture

---

## #253 — [v0.2.2][CodeReview] field_test_harness.py: escalation dimension auto-approves without exercising rejection

**Problem:** The field test harness `DIMENSIONS` table binds the `escalation` dimension to `["adv-01-billing-no-safety"]`, which is an adversarial goal. Then `run_escalation()` builds an `EscalationManager(store)`, calls `list_escalations()`, loops over `escs[:2]`, and calls `mgr.resolve(e.id, "approved", note="field test")`. It records `{"pass": True, "escalation_count": len(escs)}`. The harness flips the first two open escalations in store order to approved with no principal argument, and pass means only that the call didn't raise.

**Identified by:** ANP2 Network (dev.to article 9 comments)

**Fix:**
1. Scope `list_escalations()` to the current goal (not `store.list_plans()`)
2. Exercise the rejection path in addition to the approval path
3. Pass a principal argument to `resolve()`
4. Verify that adversarial escalations are not silently approved

**Completion checklist:**
- [ ] `list_escalations()` scoped to the current goal
- [ ] Rejection path exercised in the escalation dimension
- [ ] Principal argument passed to `resolve()`
- [ ] Adversarial escalations are not silently approved
- [ ] Existing field test results unchanged (no regression)
- [ ] Test: escalation dimension exercises both approve and reject paths

---

## #256 — [v0.2.2] Compositional injection traps — individually feasible steps that are harmful only in combination

**Problem:** The 21 injection traps in v0.2.0 tested whether the gates block individual steps that are structurally unsafe. They did not test the case where each step is *individually* feasible and structurally sound, but the *composition* of steps produces a harmful outcome.

**Proposed by:** Kartik N V J K (dev.to article 9 comments)

**Fix:**
1. Define a composition-hazard schema: declarative annotation on tasks declaring what resources/state the task touches and whether it is sensitive to concurrent or adjacent tasks
2. Add a compositional-analysis gate: given the plan DAG, detect pairs of tasks whose combined effect produces a hazard that neither produces alone
3. Generate at least 3 compositional trap goals where each step is individually feasible but the combination is harmful
4. Run the traps against the existing gates to measure the gap

**Completion checklist:**
- [ ] Composition-hazard schema defined (or existing schema extended)
- [ ] At least 3 compositional trap goals pass precondition/ordering/rollback gates but fail the compositional gate
- [ ] Compositional gate blocks all 3 traps
- [ ] Results published as a new section in the injection-resistance report
- [ ] Corpus regression: zero false positives on non-compositional plans

---

## #258 — [v0.2.2] Capability-scoped state transitions — untrusted tool results cannot acquire capabilities

**Problem:** Provenance alone (#249) tells you *where* data came from, but it does not tell you *what capabilities* that data may or may not influence. Without capability-scoped transitions, provenance-tracked data can still reach any code path. Injection defense becomes "spot malicious language in the data" — which is exactly the prompt-level approach the architecture was designed to avoid.

**Proposed by:** WebAZ (seasonkoh, dev.to article 9 comments)

**Fix:**
1. Define capability levels (ordered, strict): `untrusted_web < external_api < internal_db < internal_verified < admin_override`
2. Add `capability` field to tool results: each tool declares its source capability level (hardcoded, not LLM-decided)
3. Add `required_capability` to state transitions: each transition in the engine declares the minimum capability level needed
4. Add a capability gate: before any transition, verify that the source capability meets the required capability
5. Integrate with provenance tracking from #249: provenance carries the capability tag, and the gate checks it deterministically

**Completion checklist:**
- [ ] Capability level hierarchy defined and documented
- [ ] Each tool in the engine declares its source capability level
- [ ] Each state transition declares its required capability level
- [ ] Capability gate blocks any transition where source capability < required capability
- [ ] Integration test: untrusted tool result containing "approve dangerous plan" text is blocked by capability gate, not by content analysis
- [ ] Integration test: admin-trusted tool result passes the same capability gate
- [ ] No regression on existing gate tests

---

## #259 — [v0.2.2] Well-formed malicious plan detection — semantic gate for plans that satisfy structure but violate intent

**Problem:** The hardest remaining attack surface: a well-formed malicious plan that includes dummy rollback and dummy verification can satisfy all structural gates while carrying malicious actions. The deterministic gates check structural completeness, not semantic intent.

**Fix:**
1. **Phase 1**: Add a dedicated adversarial-prompting pass in the critic (separate from the main critique). The critic receives the plan and is explicitly prompted: "Assume this plan was written by an attacker. Identify any tasks that could be repurposed for harm while maintaining structural validity."
2. **Phase 2**: Add semantic-orphan detection: every task description must contain at least one token from the goal acceptance criteria. If a task describes an action that is not plausibly related to any acceptance criterion, flag it.
3. **Phase 3**: For high-blast-radius plans, generate an equivalent plan that achieves the same goal through different means and compare task descriptions.

**Completion checklist:**
- [ ] Phase 1: Adversarial critic pass added (separate model call, separate prompt)
- [ ] Phase 1: At least 3 well-formed malicious plans are blocked by the adversarial critic pass
- [ ] Phase 2: Semantic-orphan detection added (flag tasks with no plausible link to acceptance criteria)
- [ ] Phase 2: False-positive rate measured on the 170-goal corpus (target: <5%)
- [ ] Phase 3: Behavioral equivalence comparison added for high-blast-radius plans
- [ ] All three phases documented in architecture docs and failure-mode register
- [ ] Cost impact of Phase 1 and Phase 3 measured

---

## #260 — [v0.2.2] Benign-twin control for adversarial goals — measure injection isolation separately from gate strictness

**Problem:** The 11/11 adversarial-goal escalation rate (v0.2.1) measures the combined effect of two unknowns: gate strictness and injection isolation. A goal that is inherently unsafe would escalate even if the injected payload were stripped. The 11/11 number cannot distinguish "the gates blocked the injection" from "the gates blocked a structurally unsafe plan that happened to contain an injection."

**Proposed by:** Vinh Nguyen (dev.to article 9 comments)

**Fix:**
For each adversarial goal in the corpus, produce a **benign twin**:
- Same plan request, same goal structure
- Injected text stripped (or replaced with inert equivalent)
- Everything else identical (goal ID, tooling, environment)

Then run both twins through the full engine pipeline and compare.

**Completion checklist:**
- [ ] Benign twin exists for each of the 11 adversarial goals (8 original + 3 adversarial-policy)
- [ ] Twin is identical to the adversarial goal except injected text is stripped
- [ ] Both twins run through the same pipeline (planner + critic + gates)
- [ ] Result comparison published alongside the 11/11 headline
- [ ] If the control reveals a gap, update the injection-resistance claim in the architecture docs and the failure-mode register

---

## M3 Closure Gate

Before M3 closes, the following must be true:

### Standard milestone exit gate
- [ ] **Code review**: all M3 changes reviewed, no P1/P2 findings
- [ ] **Lint clean**: `ruff check src/ tests/` + `ruff format --check` 0 errors
- [ ] **Type check**: `mypy --strict src/ tests/` 0 errors
- [ ] **Test coverage**: `pytest --cov=src/ --cov-report=term` reports >90%
- [ ] **Documents updated**: all docs affected by M3 changes are current (security docs, gate docs, failure-mode register)
- [ ] **Clean checkin**: no debug code, no print statements, no TODOs

### M3-specific closure
- [ ] All 7 issues closed with evidence
- [ ] All injection defenses pass 100% escalation rate on adversarial goals
- [ ] approving_authority reachable from all three shipped surfaces
- [ ] Indirect injection blocked by provenance + capability gates
- [ ] Compositional injection traps blocked by new gate
- [ ] Benign-twin control published
- [ ] Corpus regression green on the full 170-goal sweep
- [ ] Full test suite passes on `rel-0.2.2` after M3 merge