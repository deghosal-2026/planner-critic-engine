# D6 — Critique Engine Design

> **Authored in:** M3 (Critique Engine + Loop Semantics) · **Status:** Current baseline · **WBS:** D6 ·
> **Refs:** [PRD §2.5 critique engine](../design/prd/02-architecture.md#25-critique-engine-dual-mode), [§2.5.3 diff-aware](../design/prd/02-architecture.md#253-diff-aware-critique-cost-optimization), [D1 architecture](../architecture/architecture-v0.1.0.md)

## Goal

Make the engine *actually careful*: a six-heuristic LLM critic that audits
beyond the deterministic gates, three critique strategies, diff-aware
re-audit, budget enforcement, a deterministic cost estimate, shadow mode, and
approval expiry.

## Architecture

```
   run_loop (loop/_controller.py)
        │  per revision
        ▼
   run_deterministic_gates ──► gate findings (free, injection-immune)
        │
        ▼  should_invoke_llm(mode, gate_findings)
   ┌─────────────────┬──────────────────┬──────────────────┐
   │ heuristic-only  │ deterministic-   │ llm-every-       │
   │ (gates only)    │ first            │ revision         │
   └─────────────────┴──────────────────┴──────────────────┘
                          │                │
                          ▼                ▼
                    LLMCritic.audit_diff   LLMCritic.audit
                    (F-78, changed+deps)   (full plan)
                          │
                          ▼
              structured enforcer → CritiqueOutput → Findings (LLM_* codes)
```

## Key decisions

### The three critique strategies (F-10, F-11, F-14)

One config knob, `critic.mode`, selects among three:

| Mode | LLM behavior | Cost |
|------|--------------|------|
| `heuristic-only` | Never invoked — the deterministic gates are the whole critique | 0 |
| `deterministic-first` | Gates first; the LLM only audits drafts that survive the gates | low |
| `llm-every-revision` | Full six-heuristic audit on every revision, even gate-blocked | high |

`should_invoke_llm(mode, findings)` is a pure function of (mode, gate
findings), so the dispatch is deterministic and unit-testable.

### Six-heuristic critic (F-04, §2.5.1)

`LLMCritic` binds a `Goal` at construction (a critic audits one goal's
revisions; the `CriticRole` protocol passes only `(plan, findings)`). It calls
the provider through the structured-output enforcer and maps
`CritiqueOutput` → typed `Finding`s. Each heuristic family maps to a stable
catalog reason code (`LLM_*`). Unknown families/severities from the model are
**skipped, never trusted** — injection-immunity at the parse layer.

### Injection-safety (F-12, §2.4)

A deterministic-gate blocker can never be overridden by the LLM critic. This
is structural: the critic only *appends* findings, and the threshold resolver
treats any `BLOCKER` as disqualifying regardless of source. The adversarial
fixture (`tests/fixtures/adversarial_goal.yaml`) asserts an all-clear critic
cannot clear a gate blocker.

### Diff-aware re-audit (F-78, §2.5.3)

On revision N>1 the critic re-audits only **changed tasks + their transitive
dependents** instead of the whole plan — a cost optimization aligned with the
budget. `critique/diff.py` computes the changed-task set from the plan diff
(`PlanDiff.added_task_ids` + `changed_task_ids`) and expands it through the
dependency DAG (`dependent_closure`). On the root revision the whole plan is
the scope. `llm-every-revision` always does a full audit.

### Budget + estimate (F-13, F-17, §2.7d)

`SpendState` now records an LLM call per critic invocation (`record_llm_call`)
and the spend is attached to `LoopResult.spend` for audit. The deterministic
cost estimate (`estimate.py`) derives step/branch/irreversible counts plus
worst-case LLM calls (2 per loop iteration) and a token cost — zero LLM cost
to compute. `within_budget` feeds the budget check.

### Shadow mode + expiry (F-14, F-18)

`run_shadow` runs the full loop in observe mode and stamps `LoopResult.mode =
"shadow"`; the plan store records the decision distinctly so a shadow-vs-live
diff is one query. `check_staleness` evaluates an `ApprovedPlan` against its
`approval_ttl` and returns a `StalenessCheck` — `stale=True` forces a replan
per the goal's `replan_policy`.

## Out of scope (M3)

- A model-agnostic token accounting model (real per-provider token counts)
- Escalation manager / replan mechanics (M4)
- The cost model calibration against corpus goals (M7/M9 field test)
