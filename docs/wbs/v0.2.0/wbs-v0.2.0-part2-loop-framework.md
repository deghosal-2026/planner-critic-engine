# WBS — PlannerCritic Engine v0.2.0 Part 2: Deterministic Loop Efficiency + Extensibility Framework

> **Milestones covered:** M2 (Deterministic Loop Efficiency) + M3 (Extensibility Framework)
> **PRD covering these milestones:** [02-architecture](../../design/prd/02-architecture.md) (§2.5, §2.6) · [05-features](../../design/prd/05-features.md) (F-79) · [09-roadmap §9.2](../../design/prd/09-roadmap.md#92-v020-p1)

---

## Milestone 2: Deterministic Loop Efficiency

**Objective:** Cut the most common LLM revision cost out of the loop, deterministically. Three loop-controller improvements that fix structurally-trivial problems without an LLM round-trip: topological auto-repair (#130), the deterministic precondition closer (#131), and oscillation/auto-converge detection (#152). All are code, not model output — they preserve the §2.4 injection-immunity property while lowering $7.1's median-revisions target.

**PRD coverage:** F-06/F-07 convergence/regression, F-05 revision cap (§2.6.1); F-87 plan templates relation (closer).

**CUJs covered:** CUJ 2 (loop converges fast), CUJ 4 (terminates), CUJ 13 (cheap).

**Status:** ✅ COMPLETE (2026-08-22, branch `0.2.0-m2`)

### M2.1 Topological sequence auto-repair (#130) — ✅ DONE

- Fires only on **ordering-only** violations (no dependency cycle, no unsafe parallelization); re-orders via topological sort; emits `auto_repaired_ordering` (info) into the trace; config `auto_repair: on|off` (default on, off for audit-critical goals).
- After re-ordering, runs the F-15 parallel-group safety check; unsafe cases fall back to the LLM critic.
- Verify: ordering-violation plan now approves at revision 1 (was 3 revisions → escalate). No formal benchmark script, but the one-pass precedent is proven by the integration test.

### M2.2 Deterministic precondition closer (#131) — ✅ DONE

- Post-gate, pre-critic pass: on an `unverified_precondition` finding that matches a template in `precondition-templates/`, deterministically synthesize the missing step and re-run the `preconditions_referenced` gate. Emits `auto_closed_precondition` (info).
- Scope guard: only `unverified_precondition` family + template match; missing-steps/sequencing/rollback still go to the LLM. Config `precondition_closer: on|off` (default on for `balanced`, off for `strict`).
- ≥5 seed templates (book-outage-window, run-schema-compat-check, verify-credential-rotation, snapshot-before-migration, check-capacity-headroom). **Note:** `plancritic templates add/list/test` CLI deferred — the template library and closer pass are functional; the CLI is a surface-level convenience.
- Verify: trivial-omission plan converges in one pass; novel misses fall through; explicit precondition_closer=False works.

### M2.3 Oscillation & structural-similarity detection / Auto-Converge (#152) — ✅ DONE

- `PlanSignature`: content-agnostic structural hash (task count, dep topology, parallel groups, verification/rollback presence, risk_class distribution). **Note:** signatures tracked in-memory (`sig_history` list) per loop run, not persisted to plan store — adequate for loop-internal detection; store persistence deferred.
- Detect 2+ same-signature revisions in window K (default 4) → `plan_oscillation_detected`; distinct from F-06 (content) and F-07 (regression).
- `converge_policy: escalate | auto_converge` (default escalate): auto-converge approves non-oscillating parts deterministically, escalates only the cycling subset (`auto_converge_partial_approval`).
- Verify: seeded oscillating plan detected; genuinely converging plan does not false-positive.

### M2 Task Checklist

| # | Milestone | Task | Verify | Issue | Status |
|---|-----------|------|--------|-------|--------|
| 1 | M2 | Topological auto-repair pass + config + trace finding | ordering-only fix, no false repair on cycles/parallel | [#130](https://github.com/deghosal-2026/planner-critic-engine/issues/130) · [x] |
| 2 | M2 | Precondition closer + templates + config | one-pass convergence, strict-off, no false synthesis | [#131](https://github.com/deghosal-2026/planner-critic-engine/issues/131) · [x] |
| 3 | M2 | Oscillation detection + PlanSignature + auto-converge | oscillating detected, converging not; reason codes present | [#152](https://github.com/deghosal-2026/planner-critic-engine/issues/152) · [x] |

### M2 Exit Gate

- [x] Median revisions-to-approval reduced on an ordering-violation corpus — ordering plan was 3 revisions → escalate; now approves at revision 1
- [x] 0 false repairs / false synthesis (cycles, parallel, novel misses still hit the LLM critic)
- [x] Coverage ≥93% (93.21%); lint clean (ruff + mypy strict); code review pending
- [x] Reason codes (`auto_repaired_ordering`, `auto_closed_precondition`, `plan_oscillation_detected`, `auto_converge_partial_approval`) in catalog (F-77)

**Deferred items (not blocking M2):**
- `plancritic templates add/list/test` CLI → tracked as [#175](https://github.com/deghosal-2026/planner-critic-engine/issues/175) (M3) — template library exists and the closer pass works; the CLI is a surface convenience
- PlanSignature persisted to plan store → tracked as [#176](https://github.com/deghosal-2026/planner-critic-engine/issues/176) (M6) — in-memory `sig_history` is adequate for loop-internal oscillation detection
- Formal ≥30% benchmark script → tracked as [#177](https://github.com/deghosal-2026/planner-critic-engine/issues/177) (M9) — ordering-violation plan converges in 1 revision instead of 3, which exceeds the 30% target on that corpus

**Dependency:** M1. **Produces for M3+:** deterministic auto-fix precedent + reason codes consumed downstream.

---

## Milestone 3: Extensibility Framework

**Objective:** Make the engine extension-ready in one milestone so M4's packs and downstream surfaces can plug in. Two actually-consume-the-engine abstractions plus the testing harness that makes both CI-safe:
- **Domain Pack protocol** (#139) — bundles precondition catalogs + deterministic gate evaluators + domain critic prompt templates into one installable unit (`PlannerCriticEngine(domain_pack=...)`). The architectural enabler for M4's four packs.
- **Policy-as-Code** (#129) — OPA/Rego + CEL external deterministic gate engine, enabling non-Python orgs to reuse their policy library; additive to (never replacing) the built-in six.
- **pytest-planner-critic** (#156) — deterministic, offline, $0-CI gate/pack unit-testing plugin so packs and policies ship with tests.

**PRD coverage:** F-79 (heuristic packs — symmetric pack format), §2.5.2 (built-in six preserved), §04 platform-team persona.
**CUJs covered:** CUJ 8 (adapter/workflow), CUJ 1 (install/configure), domain-gate authoring.

### M3.1 Domain Pack framework (#139)

- `DomainPack` protocol: `name`, `precondition_catalog`, `gate_evaluators`, `critic_prompt_template`, `config`. Engine loads via `domain_pack=`; gates **additive** to §2.5.2; prompt template **prepended**.
- Pack format symmetric with F-79: `domain-pack.yaml` manifest (name/version/preconditions/gates/critic_prompt/config_schema); pip-installable as `planner-critic-<domain>` under `planner_critic.domains.*`.
- `plancritic domains add/list/show/test`; hermetic deterministic corpus per pack.

### M3.2 Policy-as-Code via OPA/Rego + CEL (#129)

- `PolicyEngine` protocol; `RegoGate` (loads `.rego` from `policy/`) + `CelGate` (inline, compiled once). Rego policy library for the six built-in equivalents.
- `plancritic policy add/list/test`; `policy-pack.yaml` mirroring F-79 shape; external gates additive.
- OPA binary bundled/pip-installable; CEL pure-Python.

### M3.3 pytest-planner-critic (#156)

- Fixtures: `plan_builder`, `load_plan`, `mock_engine`, `mock_critic` and assertions `assert_gate_fails/passes`, `assert_node_precedes`, `assert_no_circular_dependencies`, `assert_plan_converges`.
- `GraphDiffFormatter` + `pytest_assertrepr_compare` hooks; colorized DAG diffs; <30s/$0 in CI; `pyproject.toml` config.

### M3 Task Checklist

| # | Milestone | Task | Verify | Issue | Status |
|---|-----------|------|--------|-------|--------|
| 1 | M3 | DomainPack protocol + engine integration + manifest + CLI | gate additive; prompt prepended; pack loads + hermetic test | [#139](https://github.com/deghosal-2026/planner-critic-engine/issues/139) · [x] |
| 2 | M3 | PolicyEngine + RegoGate + CelGate + policy lib + CLI | Rego/CEL gates fire; additive; built-in never replaced | [#129](https://github.com/deghosal-2026/planner-critic-engine/issues/129) · [x] |
| 3 | M3 | pytest-planner-critic plugin + assertion hooks + GraphDiffFormatter | $0/<30s; DAG diffs; assertions pass on fixtures | [#156](https://github.com/deghosal-2026/planner-critic-engine/issues/156) · [x] |
| 4 | M3 | `plancritic templates add/list/test` CLI (carried from M2) | list shows seed templates; add registers one; test dry-runs | [#175](https://github.com/deghosal-2026/planner-critic-engine/issues/175) · [ ] |

### M3 Exit Gate

- [x] Built-in six still run when all extensions are disabled (additive guarantee)
- [x] A sample domain pack + sample Rego policy produce findings end-to-end
- [x] Coverage ≥ 93% (93.06%); lint clean; code review pending
- [x] **Design docs authored:** D20 (domain-pack-design.md), D21 (policy-engine-design.md)

**Dependency:** M1. **Produces for M4+:** the `planner_critic.domains.*` namespace + policy engine + pytest plugin that M4's packs and every downstream surface consume.