# 02 — Architecture (What We Are Building)

> Sub-document of the [Design overview](../README.md). The technical heart: the core engine, the two pluggable surfaces, the critique engine, the loop, the plan schema, and the demo corpus.

## 2.1 Core value

**A pre-execution planning-quality engine for any LLM and any agent framework that:**

1. **Decomposes** a goal into a structured, typed plan — tasks, dependencies, ordering, verification steps, rollback points — via a planner LLM role.
2. **Audits** the plan via an *independent* critic role across six heuristic families, returning severity-graded findings (`blocker` / `warning` / `info`).
3. **Revises** in a bounded loop with a revision budget, convergence detection, and a regression guard (a revision that *introduces* a new blocker escalates).
4. **Escalates** to a human with a minimal, precise question when the loop cannot converge — showing the goal, the current plan, the blocker, the critique trail, and the revision history, with direct plan patching before approval.
5. **Stores** every plan version with diffs and critique history in a pluggable store (SQLite default, Postgres-ready).
6. **Re-gates** at execution time — before each step, the critic optionally re-verifies its preconditions hold (the world moved) and triggers a replan instead of blind execution.
7. **Forensics** — links an approved plan to its later executions and classifies failures as `planning` vs `execution`, flagging critiques that missed a real failure for feedback.

**The core engine is model- and framework-agnostic.** It speaks plain typed JSON. Two pluggable surfaces reveal its power.

## 2.2 Non-Goals (v1.0)

- **Executing the plan itself** — PlannerCritic plans and critiques; an existing runner executes. The adapters gate, re-gate, and serialize; they do not run the plan.
- **Replacing execution engines or agent frameworks** (LangGraph, CrewAI, etc.).
- **Guaranteeing plan correctness** — it reduces risk; it cannot eliminate it (the critic shares the planner's blind spots as an LLM).
- **Arbitrary multi-planner architectures** — starts as one planner + one critic (multi-planner is v0.3, on request).
- **Automatic goal intake from unstructured chat without a goal schema.**
- **Exhaustive model-family support at v0.1** — the OpenAI-compatible transport covers most real deployments; Anthropic/Gemini are v0.2 transports on the same protocol.
- **Full LessonExtractor** — missed-critique records and suggested checks ship; automated standing-rule promotion is the Week 8 flagship's job.
- **Tool-layer security (data leakage, supply chain, tool prompt injection)** — covered by sibling repo ToolTrust; PlannerCritic focuses on plan-layer safety.

## 2.3 Component diagram

```
                      ┌─────────────────────────────────────────────┐
   Goal ─────────────►│            CORE ENGINE (agnostic)            │
   constraints        │                                             │
   risk_tolerance     │  ┌──────────┐    ┌──────────┐               │
   budget             │  │ Planner  │◄──►│  Loop    │               │
                      │  │ (LLM)    │    │Controller│               │
   ┌──────────────┐   │  └────┬─────┘    └────┬─────┘               │
   │ LLM PROVIDER │   │       │draft         │revise/approve/escalate│
   │  LAYER       │   │       ▼              │                      │
   │  - registry  │   │  ┌──────────┐        │                      │
   │  - transport │   │  │ Critic   │◄───────┘                      │
   │  (OpenAI-    │   │  │ (det +   │                               │
   │   compatible)│   │  │  LLM)    │─findings──►severity threshold   │
   └──────┬───────┘   │  └────┬─────┘                               │
          │           │       │ findings                            │
          ▼           │       ▼                                     │
   (planner + critic  │  ┌──────────┐    ┌────────────┐              │
    use configured    │  │Escalation│    │ Plan Store │              │
    providers/models) │  │ Manager  │    │ (SQLite/   │              │
                      │  └────┬─────┘    │  Postgres) │              │
                      └───────┼──────────┴────────────┘              │
                              │                                       │
                  approved plan│  + re-gate + execution trace         │
                              ▼                                       │
                      ┌─────────────────┐                             │
                      │ FRAMEWORK       │  raw Python / LangGraph /   │
                      │ ADAPTERS (6)    │  PydanticAI / CrewAI /     │
                      └─────────────────┘  OpenAI SDK / MCP          │
                                                                │
              ┌──────────────────────────────────────────────────┘
              ▼
        CLI · MCP server · HTTP service · (web UI v0.2)
```

## 2.4 LLM provider layer (built registry-first)

- **`LLMProvider` protocol** — a thin interface (`complete(messages, tool_schemas)` → structured output) that any model/transport implements: `name`, `base_url`, `model`, `transport` type, optional `api_key`.
- **Config-driven registry** — providers are defined in config, not code: `plancritic providers add <name> --transport openai-compatible --base-url ... --model ...`. The engine loads whatever is configured. This is built *first*; the OpenAI-compatible transport is the first concrete implementation *on top of* it.
- **Cost control** — the default config points at local/cheap endpoints (OMLX, Ollama, vLLM). Paid providers are only used when explicitly registered. The planner and critic can use *different* providers/models (a different family for the critic is recommended, per the blind-spot research).
- **Per-goal spend budget** — every goal carries an optional spend ceiling (`constraints.budget`: max tokens, max LLM calls, max revisions). The loop controller enforces it: hitting the budget escalates rather than spending more. A runaway plan on a paid provider cannot rack up unbounded spend.
- **Deterministic gates are injection-immune** — schema/dependency/ordering/rollback checks run as code, not as model output; a goal crafted to corrupt the plan cannot weaken the deterministic critique. The LLM critic is *not* injection-immune (it reads the goal text) — so it is always paired with the deterministic gates, never the sole gate.
- CI never calls a paid LLM: the hermetic gate is deterministic-only.

## 2.5 Critique engine (dual-mode)

| Mode | Default | Behavior | Cost |
|------|---------|----------|------|
| **`deterministic-first`** | ✅ | Free deterministic gates (schema validity, dependency cycles, ordering sanity, verification-step presence, rollback presence) run first; the LLM critic only fires on drafts that pass the deterministic gates | Low — LLM calls only for survivable drafts |
| **`llm-every-revision`** | option | Full six-heuristic LLM critique on every draft | High — full audit depth per revision |

Same engine, one config knob (`critic.mode`). Users with cheap/audit-critical goals choose `llm-every-revision`; everyone else gets the low-cost default.

### 2.5.1 The six critique heuristic families

| Family | What it audits | Example blocker | Deterministic / LLM |
|---|---|---|---|
| **Feasibility** | Each task is achievable with the stated environment/tools/constraints; no impossible or undefined steps | "Step 3 assumes a tool that isn't in the environment" | LLM |
| **Risk** | Blast radius of each step vs the goal's `risk_tolerance`; irreversible / external / high-cost steps flagged | "Step 5 deletes prod data with no dry-run gate" | LLM |
| **Missing steps** | Gaps between the stated goal and the plan — obvious prerequisites omitted | "No step verifies DB schema compatibility before the migration cutover" | LLM |
| **Unsafe sequencing** | Dependency / ordering hazards — a step running before its precondition; **parallelization that breaks safety** (e.g. two prod writes in one `parallel_group`) | "Rollback step is scheduled after the 50% rollout step" / "Two irreversible prod writes run in the same parallel group" | Deterministic (dependency graph) + LLM |
| **Unverified dependencies** | A step depends on a fact never established earlier in the plan (external state, a prior verification) | "Step 6 assumes the outage window is booked; no step books it" | LLM |
| **Weak rollback** | High-blast-radius steps lack a rollback or verification step; rollback ordering unsound | "Irreversible prod write has no rollback step" | Deterministic (rollback presence) + LLM |

Every finding carries a heuristic family, severity (`blocker` / `warning` / `info`), a task reference, a machine-readable `reason_code`, and a human message. **A blocker from a deterministic gate can never be overridden by the LLM critic** (injection-safety).

### 2.5.2 Deterministic gates (the free layer)

| Gate | Check | Reason code |
|---|---|---|
| `schema_valid` | Plan parses against the typed schema | `plan_schema_invalid` |
| `no_dep_cycles` | Dependency graph is a DAG | `dependency_cycle` |
| `ordering_sane` | No task ordered before a hard dependency | `unsafe_ordering` |
| `verification_present` | High-blast-radius steps carry a verification step | `missing_verification` |
| `rollback_present` | High-blast-radius steps carry a rollback step | `missing_rollback` |
| `preconditions_referenced` | Every precondition references an established earlier task or env fact | `unverified_precondition` (deterministic variant) |

### 2.5.3 Diff-aware critique (cost optimization)

On revision N>1, the critic re-audits only **changed tasks + their dependents** rather than the whole plan — a cost optimization aligned with the budget. A full re-critique is still available via `critic.mode=llm-every-revision` when audit depth justifies it. The changed-task set is computed from the plan diff (F-78).

## 2.6 Approval & loop semantics

- **Per-goal approval threshold** (from the goal schema's `risk_tolerance` field): `strict` = zero warnings tolerated; `balanced` = warnings tolerated but must be explicitly acknowledged in the final plan. **No blockers may ever remain.**
- **Loop termination:** (a) critic approves (threshold met) ✓, (b) revision cap reached (default 3, configurable) → escalate, (c) **convergence detection** — revisions circling the same blockers, or plan diffs converging to near-zero between versions → escalate early, (d) **regression guard** — a revision introduces a *new* blocker → escalate (planner is thrashing), (e) **budget hit** → escalate.

### 2.6.1 Loop controller algorithm (pseudocode)

```
function run_loop(goal, provider_registry, config):
    plan_v = planner.decompose(goal)             # LLM call
    store.put(PlanVersion(plan_v, parent=None))
    for revision in 1..config.revision_cap:
        gates = deterministic_gates(plan_v)        # free, always run
        if critic.mode == "deterministic-first":
            if gates.has_blocker(): plan_v = planner.revise(plan_v, gates.as_findings()); continue
            findings = critic.audit(plan_v, changed_tasks_only=(revision>1))  # LLM
        else:  # llm-every-revision
            findings = gates.as_findings() + critic.audit(plan_v)
        store.put(Findings(plan_v, findings))
        if meets_threshold(findings, goal.risk_tolerance): return Approved(plan_v)
        if budget_exceeded(goal.budget): return Escalate(budget)
        if regression_detected(findings, prior_findings): return Escalate(thrashing)
        if converged(plan_v, prior_plan): return Escalate(stalled)
        prior_plan, prior_findings = plan_v, findings
        plan_v = planner.revise(plan_v, findings)  # LLM call
        store.put(PlanVersion(plan_v, parent=prior_plan))
    return Escalate(revision_cap)
```

The controller is **deterministic on identical inputs** (F-74, CI-asserted): given the same planner/critic outputs, the same loop decisions (approve/revise/escalate) result.

## 2.7 Execution feedback (planning vs execution)

- An approved plan can be linked to later executions and **tagged** `planning` / `execution` on failure.
- A tagged failure that the critic *missed* is **recorded with its critique history** ("the critic said this was fine; execution proved otherwise") and **surfaces a suggested deterministic check** to the operator.
- This feeds LessonExtractor (Week 8 flagship): the missed-critique records become a standing-rule corpus. The data model captures the miss at v0.1; automated promotion is a v0.2+ concern.

## 2.7b Replan semantics (mid-execution)

When the re-gate (F-46) finds a stale precondition, "a replan request" is not enough — the behavior must be defined. PlannerCritic supports three policies, set per goal (`replan_policy`):

| Policy | Behavior | When it fits |
|---|---|---|
| **`patch`** (default) | The planner revises only the remaining steps from the stale one onward; already-executed steps are preserved. The revision is a *sub-plan* linked to the parent plan's history (F-53). | Most goals — keep progress, fix the tail |
| **`restart`** | The whole plan is re-decomposed from the goal, ignoring prior execution; the prior plan + execution trace is archived as a parent. | The goal's assumptions changed fundamentally |
| **`abort`** | Stop; escalate to a human. A stale precondition that's *not* auto-replannable (e.g. an irreversible step's precondition failed mid-run). | High-stakes / irreversible mid-plan |

A replan is recorded in the same plan history as a linked sub-plan (F-53), so the full execution lineage — original plan → partial execution → replan → completion — is reconstructable from the store.

## 2.7c Shadow mode (the adoption wedge)

`plannercritic plan "<goal>" --dry-run` (F-14) runs the full planner→critic→revise→approve loop *alongside* an agent's existing single-pass planner and logs what PlannerCritic **would** have blocked/approved/escalated — without gating execution. This is the tooltrust `dry_run` adoption pattern: deploy in observe mode, compare against your current planner's output, tune, then flip to enforce. The plan store records shadow decisions distinctly (`mode: shadow`) so a diff is one query.

## 2.7d Plan complexity / cost estimate (deterministic, pre-approval)

Before a user approves, PlannerCritic surfaces a deterministic derived summary (F-17): step count, parallel-branch count, irreversible-op count, est. LLM calls, est. token cost. The user can gate on **cost**, not just risk — and the estimate feeds the budget check. Zero LLM cost to compute.

## 2.7e Approval expiry / stale plan

An approved plan carries a TTL (`approval_ttl`, default ∞, configurable). An expired approval forces a replan per §2.7b — the world may have moved between approval and execution. The re-gate covers *per-step* drift; the TTL covers *whole-plan* drift.

## 2.8 Plan schema (typed sketch)

```
Goal:
  id, description, constraints{budget, time, environment, tools[]},
  risk_tolerance{strict|balanced}, replan_policy{patch|restart|abort},
  approval_ttl (seconds, default ∞), metadata

PlanVersion (one per revision; immutable once stored):
  id, goal_id, plan_schema_version (semver), version (int),
  parent_version (nullable; set for replans), created_at
  tasks: Task[], deps: Dependency[], branches: Branch[]  (explicit parallel/branch beyond deps)

Task:
  id, description, action (verb), target,
  parallel_group (nullable; tasks in the same group run concurrently),
  preconditions[] (each may declare an EnvProbe to verify a live fact),
  verification: VerificationStep|null,
  rollback: RollbackStep|null, risk_class, blast_radius

Branch:
  id, kind{fan_out|fan_in}, tasks[], join{all|any|quorum}

Dependency:
  from_task, to_task, kind{hard|soft}, reason

EnvProbe (optional; grounds a precondition in live state):
  kind (e.g. env_var, db_query, http_check, deploy_status),
  query, expected

VerificationStep: what_to_check, how, expected
RollbackStep:    trigger, action, safety_guard

Finding (critic output; one per task per version):
  id, task_id, version, heuristic_family, severity{blocker|warning|info},
  reason_code, message, suggested_fix

Escalation:
  id, plan_id, version, blocker_finding_id, question,
  status{open|approved|denied}, resolution, resolved_at

ExecutionTrace (plan ↔ run link):
  id, plan_id (approved version), task_id, outcome,
  failure_class{planning|execution|null}, linked_finding_id (missed-critique)

PlanComplexity (deterministic, derived, pre-approval):
  step_count, parallel_branch_count, irreversible_op_count,
  est_llm_calls, est_token_cost
```

## 2.9 Demo corpus (seeded flaws)

A domain-agnostic `examples/` set. Each goal has a known seeded flaw the critic must surface — this is what makes the "aha" demo and the field-test matrix credible, not staged.

| Goal domain | One-liner | Seeded flaw the critic must catch | Heuristic family |
|---|---|---|---|
| Service migration | "Migrate service X to the new auth provider" | No step verifies DB schema compatibility before cutover | Missing steps |
| Rollout | "Canary-deploy feature Y to 10% then 50%" | Rollback step scheduled after the 50% step | Unsafe sequencing |
| Refactor | "Split monolith module Z into two services" | Step assumes an outage window is booked; no step books it | Unverified dependencies |
| Incident response | "Mitigate the auth-service 5xx spike" | No verification step confirms mitigation before declaring resolved | Weak rollback |

## 2.10 Terminal-state definition ("done" for v0.1.0)

A working `v0.1.0` you can `pip install planner-critic`, run `plancritic init` (config + provider + example goal), give it a non-trivial goal, watch the critic flag a real gap in the planner's first draft, see the planner revise to approval — or escalate cleanly with a precise question when it can't — with every plan version and critique stored and diffs inspectable, a `plannercritic-demo` runner showing plan→approve→re-gate→execute end-to-end, re-gate catching a stale precondition and triggering a defined replan, failures classifiable as planning vs execution, shadow mode logging what *would* have happened without gating, and a field-test matrix green across all six frameworks against a local model.