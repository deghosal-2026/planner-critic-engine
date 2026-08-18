# D7 — Escalation Design

> **Authored in:** M4 (Escalation + Forensics + Replan + Viz) · **Status:** Current baseline · **WBS:** D7 ·
> **Refs:** [PRD §2.1 escalation manager](../design/prd/02-architecture.md#21-core-value), [§2.7e approval expiry](../design/prd/02-architecture.md#27e-approval-expiry--stale-plan), [DD-10 escalation precision contract](../design/design-decisions.md#m4-entries), [D1 architecture](../architecture/architecture-v0.1.0.md)

## Goal

When the loop cannot converge (revision cap, regression, budget, stalled), it produces a precise single-question escalation to a human reviewer. The escalation manager is the concrete gate: it validates the precision contract, persists the record, surfaces it for a decision, records the resolution (approved or denied), and supports **direct plan patching** (the reviewer provides a fixed PlanVersion that is stored as the next revision and re-critiqued before approval).

## Architecture

```
   run_loop (loop/_controller.py)
        │  cannot converge
        ▼
   _escalate(goal, plan, findings, reason)
        │  builds Escalation with blocker_finding_id + precise question
        ▼
   EscalationManager.create(escalation)
        │  validates:
        │    • plan + revision exist in store
        │    • question is non-blank (DD-10 precision contract)
        │    • no other open escalation for this plan
        ▼
   Persistent store (SQLite/InMemory)
        │
        ├── escalate list                         (CLI / MCP tool)
        ├── escalate approve <id> --note "..."    (CLI / MCP tool)
        │       └── --patch <file>: patch_and_recritique → resolve
        └── escalate deny <id> --note "..."       (CLI / MCP tool)
```

### The patch flow

```
   escalate approve <id> --patch patch.json
        │
        ▼
   PlanVersion.from_dict(patch.json)
        │
        ▼
   EscalationManager.patch_and_recritique(plan_id, patch, critic)
        │  run_deterministic_gates(patch)
        │  critic.audit(patch, gate_findings)
        │  if blockers remain → raise ValueError (fail-closed, F-73)
        ▼
   store.put_plan_version(patch)      (version N+1, parent = N)
   store.put_findings(plan_id, N+1, findings)
        │
        ▼
   EscalationManager.resolve(esc_id, "approved", note)
        │  status → approved, resolved_at = now, resolution = note
        ▼
   store.put_escalation(resolved)
```

## Key decisions

### EscalationManager owns precision validation

The manager is the sole gate between the loop's `_escalate()` and the persistent record. It enforces:
- The target plan + revision exist in the store (never an orphan escalation).
- The question is non-blank (a blank question is not resolvable — DD-10).
- At most one open escalation per plan (one precise question at a time — no queueing).

Resolution is recorded back into the same escalation record (status, resolution text, resolved_at) so the full lifecycle is a single persistent object.

### Direct plan patching before approval (F-34)

A reviewer can supply a fixed `PlanVersion` via `--patch`. The manager stores it as the next revision (version N+1, parent = current id) and re-runs the deterministic gates + critic. If any **blocker** remains, the patch is refused fail-closed — the deterministic gates are injection-immune and a blocker can never be overridden by a model. Warnings survive but are recorded for audit.

The hermetic CLI path uses `_DeterministicCritic` / `_GateOnlyCritic` — a critic that surfaces only gate findings (no LLM call). This keeps the patch flow cheap, deterministic, and zero-network.

### Single-question precision (DD-10)

Each escalation carries exactly one resolvable question: a non-blank question and a reference to the single blocker finding that caused it. The manager enforces this at `create()` time. The loop's `_escalate()` already produces a precise single question per invocation.

### Resolution is a store-level event

The manager never holds state in memory: `create`, `list`, and `resolve` all read/write through the `PlanStore`. This makes the escalation lifecycle survive restarts — critical for a human reviewer who may take hours to respond.

## Out of scope (M4)

- Escalation web UI (deferred to v0.2.0)
- Multi-reviewer escalation (current model is one decision per escalation)
- MCP server wiring (tools registered in M5; the tool functions exist in `server/mcp_tools_escalate.py`)
- Re-gate mechanics (separate `regate.py`, covered in D8)
- Notification webhooks / Slack integration