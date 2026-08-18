# D10 — Explain Engine Design

> **Authored in:** M6 (CLI + HTTP Service + Explain + Init) · **Status:** Current baseline · **WBS:** D10 ·
> **Refs:** [PRD §CUJ15 explain](../design/prd/04-users-and-cujs.md#cuj-15--understand-why-the-loop-decided-what-it-did-loop-decision-explain), [DD-12 explain narrative format](../design/design-decisions.md#m5--m6-entries), [D1 architecture](../architecture/architecture-v0.1.0.md)

## Goal

Produce a human-readable narrative explaining why the planning loop made its decisions — approved, escalated, or replanned. The narrative must be ≤10s to render and actionability-tested: a reviewer can identify the outcome-changing factor from the text alone (CUJ 15).

## Architecture

```
   explain(store, plan_id) → ExplainResult
        │
        ▼
   replay(store, plan_id) → ReplayResult
        │  ordered list of ReplayStep (version + plan + findings)
        ▼
   for each step:
        map findings to narrative templates
        aggregate decisions
        │
        ▼
   ExplainResult
        .summary       — "Approved on revision 3"
        .narrative     — "The plan was proposed, revised twice, ..."
        .decisions[]   — per-revision ExplainDecision
```

### Narrative template mapping

Each finding's `reason_code` maps to a narrative line via `REASON_CODE_DESCRIPTIONS` (from `reason_codes.py`). The explain engine collects all findings per revision and produces:

- **Approved revision**: "Revision {N} was approved: {finding count} findings resolved, {0} blockers remaining."
- **Escalated revision**: "Revision {N} was escalated: {reason}."
- **Revised revision**: "Revision {N} was revised: {finding count} findings to address."

### Actionability contract

The test `test_actionability` verifies that a seeded plan with a specific blocker (`missing_verification`) produces a narrative containing that blocker's description. A reviewer reading the narrative must be able to identify what went wrong.

## Key decisions

### Narrative is templated, not LLM-generated

The explain engine uses structured templates driven by reason codes rather than calling an LLM. This keeps the explain path deterministic, zero-cost, and zero-network. The narrative is always ≤10s to render because it's a pure computation over stored data.

### Explain uses replay as its data source

Rather than reading the store directly, `explain()` calls `replay()` to get the ordered revision history with findings. This keeps the explain logic independent of store internals and ensures the same ordering as the replay command.

### Decisions are per-revision, not per-finding

Each `ExplainDecision` represents one revision's outcome (approved/escalated/revised), not individual findings. The narrative aggregates findings into the decision narrative. This keeps the output concise — a plan with 10 revisions produces at most 10 decisions, not 100 findings.

## Out of scope (M6)

- LLM-summarized narrative (keeping it deterministic for v0.1.0)
- Interactive explain (e.g., "why was this specific task flagged?")
- Multi-plan explain comparisons