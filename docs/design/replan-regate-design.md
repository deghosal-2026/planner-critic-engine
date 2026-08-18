# D8 — Replan + Re-gate Design

> **Authored in:** M4 (Escalation + Forensics + Replan + Viz) · **Status:** Current baseline · **WBS:** D8 ·
> **Refs:** [PRD §2.7b replan semantics](../design/prd/02-architecture.md#27b-replan-semantics-mid-execution), [§2.7d plan complexity & cost estimate](../design/prd/02-architecture.md#27d-plan-complexity--cost-estimate-deterministic-pre-approval), [DD-09 replan policy defaults](../design/design-decisions.md#m4-entries), [D1 architecture](../architecture/architecture-v0.1.0.md)

## Goal

When a plan fails mid-execution, the system must decide what to do next. The replan module provides three policies — `patch`, `restart`, `abort` — that determine how the next plan revision is created. The re-gate module (M5) will add execution-time re-verification of preconditions before a step runs. Together they form the mid-execution recovery and safety layer.

## Replan semantics (§2.7b)

### Policies

| Policy | Behavior | Lineage | Use case |
|--------|----------|---------|----------|
| `patch` (default) | The planner revises remaining steps; sub-plan linked to parent | `version++`, `parent_version` = failed revision | Most common — quick correction of one step |
| `restart` | The planner re-decomposes from scratch | `version++`, `parent_version` = failed revision | The plan is fundamentally wrong; start over |
| `abort` | No plan revision is created; `ReplanAbort` raised | None | Human must decide what to do |

All three policies preserve **version lineage**: every plan revision (whether root, patch, or restart) carries a `parent_version` pointing at its predecessor. The version chain is always traversable for forensics and replay — there is no orphan revision.

### Implementation

The replan function is a **pure stamping function** — it does not decide *what* the revised plan contains. That is the planner role's job. It only stamps the correct version metadata:

```
replan(goal, current, revised) → PlanVersion
  if goal.replan_policy == "abort": raise ReplanAbort
  return PlanVersion(
      id=current.id,            // same plan id
      goal_id=current.goal_id,
      version=current.version + 1,
      parent_version=current.id, // lineage link
      tasks=revised.tasks,       // planner's content
      dependencies=revised.dependencies,
      branches=revised.branches,
  )
```

### Replan trace (F-53)

A `ReplanLink` record is stored alongside the new revision to capture:
- The parent plan id and version being replaced.
- The replan policy (`patch` or `restart`) that produced this revision.
- An optional `partial_execution` JSON snapshot — what completed before the failure.

The store provides `put_replan_link` / `get_replan_link` / `get_child_replan_links` so the full lineage is queryable: from root → partial execution → replan → completion.

## Re-gate design (F-46, M5 scope)

The re-gate is an **execution-time safety check** not yet implemented (M5). Its design:

### What re-gating checks

Before executing a task, the re-gate re-verifies that the preconditions the deterministic gates accepted at plan-time still hold at execution-time (preconditions may reference probes whose results change — DD-06, EnvProbe is read-only by contract):

1. **Precondition re-check** — for every task precondition that has an `EnvProbe`, re-run the probe and compare with `expected`. If the fact no longer holds, the precondition is stale.
2. **Blast-radius re-evaluation** — if the execution environment has changed (e.g. a parallel task completed with an unexpected outcome), re-assess whether the remaining steps' blast-radius is still acceptable.
3. **Replan trigger** — if re-gating fails, trigger the goal's `replan_policy` to produce a new plan revision.

### EnvProbe interaction

Probes are read-only by contract (DD-06). At plan-time, probes are optional enrichments — deterministic gates never depend on them. At execution-time, the re-gate *does* depend on probes: a stale precondition is a real safety issue that must either re-plan or halt.

### Re-gate data flow

```
   ExecutionRecorder.record(approved, task_id, outcome)
        │  outcome == "failed"
        ▼
   ReGate.check(approved_plan, task_id, env_probes)
        │  for each precondition with a probe:
        │      probe_result = run_probe(precondition.probe)
        │      if probe_result != expected → stale
        ▼
   if stale → replan(goal, current_plan, planner.decompose(goal))
        │
        ├── PATCH → planner revises remaining tasks → new revision
        ├── RESTART → planner re-decomposes → new revision
        └── ABORT → ReplanAbort raised
```

## Lineage model

Every plan revision — root, patch, restart — is a `PlanVersion` in the same plan lineage:

```
   root (v1) ──► patch (v2) ──► restart (v3) ──► patch (v4)
                  │                │
                  ▼                ▼
              ReplanLink        ReplanLink
              (parent=v1,       (parent=v2,
               policy=patch)     policy=restart)
```

The parent chain (`PlanVersion.parent_version`) is a linked list. The `ReplanLink` store records add type + partial-execution metadata. Both together let a walker reconstruct: *"v1 was executed, task t2 failed, replan policy was `patch`, v2 was created, executed, …"*

## Out of scope (M4)

- Re-gate code (F-46, deferred to M5 adapters — requires frameork adapter layer to inject into execution flow)
- Automatic probe-driven re-gating (the store + EnvProbe interfaces are ready; wiring is M5)
- Replan-vs-execution concurrency (how to handle a replan while another task is still running)
- Cost-model-aware replan (choose between patch/restart based on estimated cost of each)