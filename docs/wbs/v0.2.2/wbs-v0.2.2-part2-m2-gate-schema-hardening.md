# WBS — PlannerCritic Engine v0.2.2-M2: Gate & Schema Hardening

> Part of the v0.2.2 release. See [index](wbs-v0.2.2-index.md) for milestone overview and dependency graph.
>
> **Branch:** `rel-0.2.2` · **Milestone:** [v0.2.2-M2 Gate & Schema Hardening](https://github.com/deghosal-2026/planner-critic-engine/milestone/16)
>
> **Scope:** Deterministic gate improvements and schema evolution. Each ships with a regression test that fails on pre-fix code.

---

## Overview

M2 adds deterministic gates and schema improvements that strengthen the engine's structural validation. Each issue ships with a RED→GREEN regression test, and the corpus regression must show zero false positives on clean plans.

| Issue | Title | Area | Complexity |
|-------|-------|------|------------|
| #242 | Live-boundary runner decision-context capture | testing | medium |
| #243 | Machine-actionable finding contract | schema | high |
| #244 | Runtime precondition verification on by default | engine | medium |
| #245 | Typed rollback restoration contracts | schema/gates | high |
| #255 | Requirement-traceability gate | gates/schema | high |

---

## #242 — [v0.2.2] Live-boundary runner decision-context capture + unsupported-evidence frequency metric

**Problem:** The v0.2.1 live-boundary runner (#218) measures critic non-determinism across repeated trials, but it does not capture the full decision context. A label shift caused by a prompt or tool-definition change between runs is indistinguishable from stochastic variance. Additionally, the evidence metric measures cross-trial consistency, which means a critic citing the same nonexistent function ten times scores perfectly stable and perfectly undetected.

**Proposed by:** Peter (peterbuildssecure, dev.to article 2 comments)

**Fix:**
1. Every trial records: model id, model version, temperature, system-prompt hash, tool-schema hash
2. Explanations get their claimed facts extracted and validated against boundary plans (whose ground truth is fully known)
3. Report leads with two rates: decision disagreement across identical trials, and unsupported-evidence frequency — as separate axes

**Completion checklist:**
- [ ] Trial records include model id, version, temperature, system-prompt hash, tool-schema hash
- [ ] Explanation facts extracted and validated against ground-truth boundary plans
- [ ] Unsupported-evidence frequency metric implemented and reported
- [ ] Decision disagreement and unsupported-evidence frequency reported as separate axes
- [ ] Boundary corpus regression green (no false positives on clean plans)
- [ ] Integration test: critic citing nonexistent function is detected as unsupported evidence

---

## #243 — [v0.2.2] Machine-actionable finding contract — edge targeting, observed-state/evidence fields, finding-schema versioning, replay snapshots

**Problem:** Findings currently carry an id, target task id, plan version, machine-readable reason code, and suggested fix. They do not include:
- Edge-level targeting (ordering defects should name the producer-consumer pair, not one task)
- An observed-state field (what the gate actually observed)
- Evidence references back to the precondition facts or edges that fired
- An independent finding-schema version
- A retained precondition snapshot (so a rerun can tell whether the plan changed because the task changed or because the gate logic changed)

**Proposed by:** Triumph (triumph1701, dev.to article 7 comments)

**Fix:**
1. Add `target_edge: Optional[Tuple[str, str]]` for edge-level targeting
2. Add `observed_state: str` describing what the gate actually observed
3. Add `evidence: List[str]` with references to the precondition facts or edges that fired
4. Add `schema_version: str` to the finding schema
5. Add `precondition_snapshot: str` (hash of the precondition facts at evaluation time)
6. The replay-boundary test: same plan + bumped gate versions must be attributable to gate-logic change; changed plan + same gates to plan change

**Completion checklist:**
- [ ] Edge-level targeting field added to Finding
- [ ] Observed-state field added to Finding
- [ ] Evidence references field added to Finding
- [ ] Finding-schema version field added and incremented on schema changes
- [ ] Precondition snapshot retained and attributed to findings
- [ ] Replay-boundary test: same plan + bumped gate versions → gate-logic change attribution
- [ ] Replay-boundary test: changed plan + same gates → plan change attribution
- [ ] Corpus regression green

---

## #244 — [v0.2.2] Runtime precondition verification on by default — re-gate shipped-but-inert

**Problem:** The runtime precondition verification gate was shipped in v0.2.0 but is off by default, probe-only in coverage, and has no fail-closed path. Deployments that don't explicitly enable it get no runtime precondition checking.

**Fix:**
1. Enable runtime precondition verification by default
2. Add fail-closed path: if a precondition is violated at runtime, the plan escalates
3. Add probe-only mode as an opt-in alternative (for monitoring without enforcement)
4. Verify corpus regression green with default-on
5. Document migration path for existing deployments

**Completion checklist:**
- [ ] Runtime precondition verification enabled by default
- [ ] Fail-closed path implemented (precondition violation → escalation)
- [ ] Probe-only mode available as opt-in
- [ ] Corpus regression green with default-on
- [ ] Migration path documented for existing deployments
- [ ] Test: precondition violation under default config produces escalation

---

## #245 — [v0.2.2] Typed rollback restoration contracts — declarative restored-state + restoration-evidence fields on RollbackStep

**Problem:** The rollback credibility gate (#216) infers rollback credibility from surrounding structure. This works for obvious cases but misses subtle patterns. A stronger contract requires each high-blast-radius action to declare what state it restores and what evidence proves restoration possible.

**Proposed by:** Suraj Suradkar (suraj09, dev.to article 7 comments — "propose vs prove" split)

**Fix:**
1. Add optional `restored_state: str` field to RollbackStep (declarative description of the state after rollback)
2. Add optional `restoration_evidence: str` field to RollbackStep (how to verify the state was restored)
3. When both fields are present, the gate validates them against the plan graph
4. When absent, the gate derives credibility as today (backward compatible)
5. Migration path: declaration is advisory in v0.2.2, required in a future release once corpus coverage earns it

**Completion checklist:**
- [ ] `restored_state` field added to RollbackStep schema
- [ ] `restoration_evidence` field added to RollbackStep schema
- [ ] Gate consumes declaration when both fields present
- [ ] Gate derives credibility as today when fields absent (backward compatible)
- [ ] Corpus regression green (zero false positives on clean plans)
- [ ] Migration path documented
- [ ] Test: rollback with declared restored_state passes credible gate
- [ ] Test: rollback with no declaration still passes credible gate (backward compat)

---

## #255 — [v0.2.2] Requirement-traceability gate — every plan step traces back to an acceptance criterion

**Problem:** A plan can be safe and well-ordered yet still drift from the user story it was meant to deliver. There is no deterministic check that each plan step serves a documented acceptance criterion.

**Proposed by:** jlcases (dev.to article 1 comments) and Kartik N V J K (dev.to article 9 comments)

**Fix:**
1. Add a deterministic gate that checks every plan step references at least one acceptance criterion from the goal
2. Steps that do not reference any criterion are flagged as "semantic orphans" with BLOCKER severity
3. Criteria are defined in the goal schema and bound at run start (frozen by #215)
4. The gate is injection-immune (it parses the plan AST, not goal text)

**Completion checklist:**
- [ ] Requirement-traceability gate implemented as a deterministic gate
- [ ] Gate checks every plan step against acceptance criteria from the goal
- [ ] Steps with no criterion reference flagged as BLOCKER (semantic_orphan)
- [ ] Gate is injection-immune (parses AST, not goal text)
- [ ] Corpus regression: zero false positives on clean plans
- [ ] Corpus regression: plans with orphan steps are correctly blocked
- [ ] Integration with acceptance-criteria contract (#215) verified

---

## M2 Closure Gate

Before M2 closes, the following must be true:

### Standard milestone exit gate
- [ ] **Code review**: all M2 changes reviewed, no P1/P2 findings
- [ ] **Lint clean**: `ruff check src/ tests/` + `ruff format --check` 0 errors
- [ ] **Type check**: `mypy --strict src/ tests/` 0 errors
- [ ] **Test coverage**: `pytest --cov=src/ --cov-report=term` reports >90%
- [ ] **Documents updated**: all docs affected by M2 changes are current (gate docs, schema docs, failure-mode register)
- [ ] **Clean checkin**: no debug code, no print statements, no TODOs

### M2-specific closure
- [ ] All 5 issues closed with evidence
- [ ] Every issue ships with a regression test that fails on pre-fix code
- [ ] Corpus regression green on the full 170-goal sweep
- [ ] No false positives on clean plans for any new gate
- [ ] All new schema fields are backward compatible or have documented migration paths
- [ ] Full test suite passes on `rel-0.2.2` after M2 merge