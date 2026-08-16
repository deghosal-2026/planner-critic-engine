# D3 — Loop Controller Design

> **Authored in:** M1 (Core Engine) · **Status:** Built, mirrors implementation · **WBS:** D3 · **Refs:** [PRD 02 §2.6 revise-until-approved loop, §2.7 escalation](../../design/prd/02-architecture.md#26-revise-until-approved-loop)

## Purpose

Document the M1 loop controller (`planner_critic/loop/_controller.py`) — the verbatim state machine from the PRD §2.6.1 pseudocode — and the deterministic guard helpers it uses (`budget.py`, `regression.py`, `convergence.py`, `ttl.py`).

## The Loop Goal

Take a `Goal`, a `PlannerRole`, and a `CriticRole`; produce either an **approved** `ApprovedPlan`, or an **escalated** `Escalation` with a reason code, spent budget, revision count, and a human question. Bounded spend. Deterministic exit conditions verified **before** any model spend on a revision.

## Controllers: `run_loop` (public API) vs `_run` (the state machine)

- `run_loop(...)` (loop/_controller.py:78) — the public entry: decodes tolerance & expiry from the goal, then hands to `_run`. Raises `PlanningError(reason_code="planning_unavailable")` if either role is missing.
- `_run(...)` (loop/_controller.py:164) — the iterative core. State: `budget`/`spend`, `revision_count`, `approval_ttl`/`elapsed`, `prior_plan`, `prior_findings`, `seen_cycles`.

## Per-Revision Sequence (M1, llm-every-revision mode)

For revision `r = 1..cap`:

1. **Record revision** — `history.append(plan)`; `spend.calls += 1`.
2. **Deterministic gates** — `findings = run_deterministic_gates(plan)` (free, injection-immune).
3. **Critic audit** — `_safe_audit`: call `critic.audit(plan, prior=findings)`; **guardrail**: every returned finding is `model_validate`-checked; malformed findings are silently dropped and a `malformed_critic_output` warning is recorded (criticism can never inject arbitrary state). Merged into `findings`.
4. **Approval check** — `resolve_threshold(findings, tolerance)`:
   - `strict` → any `WARNING` or `BLOCKER` defers (fail-closed).
   - `balanced` → only `BLOCKER`s defer; warnings need acknowledgment.
   - Approved when the tolerance threshold is met **and** `approval_expired(ttl, elapsed)` is false (an expired approval defers even if findings are clean).
5. **Budget check** — `budget_exceeded(budget, spend)`: `max_calls`/`max_tokens` crossed → escalate `budget_exceeded`. (M1 is deterministic-token: `tokens ≈ n_shots × n_tokens_avg`.)
6. **Regression guard** — `regression_detected(prior_findings, findings)`: a new `BLOCKER` key `(reason_code, task_id)` appeared that wasn't in the prior revision → escalate `regression_thrashing` immediately.
7. **Convergence guard** — `stalled(prior_plan, current_plan, prior_findings, findings)`:
   - `circling_blockers`: the same `(reason_code, task_id)` set inflow v2+ → escalate `convergence_stalled_circling`.
   - `near_zero_diff`: plan fingerprint (tasks + deps + branches) unchanged from prior revision → escalate `convergence_stalled_zero_diff`.
8. **Revise** — `_revise_or_raise`: `planner.revise(goal, plan, findings)` restarts the plan (no `draft=False` in M1), producing a new **immutable** `PlanVersion` with `id`/`version` stamped and `parent_version` linked. If the planner raises, escalate `critic_stalled` (planner failure = planning failure).

## Escalation: `_escalate`

Maps every exit reason to `(status="escalated", reason_code)`. Question text (`_compose_question`) is deterministic: project context absent in M1, so it cites the blockers and asks a concrete yes/no or repair question per finding. Every escalation includes `revision_count`, `spend`, the final plan, and the findings that forced the exit.

## Deterministic Guards (sibling modules)

| Module | Function | Trigger |
|---|---|---|
| `loop/budget.py` | `SpendState`, `budget_exceeded` | `max_calls`/`max_tokens`/`max_revisions` crossed |
| `loop/regression.py` | `regression_detected` | new `(reason_code, task_id)` blocking key in current vs prior |
| `loop/convergence.py` | `circling_blockers`, `near_zero_diff`, `stalled` | repeated blocker set (v2+), or fingerprint-identical revision |
| `loop/ttl.py` | `approval_expired` | approval older than `goal.approval_ttl` |

## Exit Condition Table

| Condition (checked in order) | Status | `reason_code` |
|---|---|---|
| Roles missing at entry | `PlanningError` | `planning_unavailable` |
| Approval threshold met | `approved` | `approved` |
| Budget exhausted | `escalated` | `budget_exceeded` |
| New blocker introduced | `escalated` | `regression_thrashing` |
| Blockers recur from v2+ | `escalated` | `convergence_stalled_circling` |
| Fingerprint-identical revision | `escalated` | `convergence_stalled_zero_diff` |
| Planner raised | `escalated` | `critic_stalled` |
| No approval by `revision_cap` | `escalated` | `revision_cap_reached` |
| Critic finding malformed | recorded | `malformed_critic_output` (warning) |
| Plan violates schema | gate finding | `schema_invalid` (blocker) |

## Edge Cases Covered (tests)

- Revision cap reached with still-blocking findings → `revision_cap_reached`.
- `strict` tolerance: warning alone defers → not approved; accepted planning loop continues.
- Regression: planner introduces a new `missing_verification` blocker on revision 2 → escalated at revision 2 (no wasted revision 3).
- Zero-diff stall: planner returns byte-identical plan on revision 2 → escalated.
- Circling: warning→warning→blocker pattern escalates only after the blocker recurs (v2+).
- Critic returns garbage/`None` → dropped, warning recorded, loop not poisoned.
- Planner raises → `critic_stalled` escalation, no crash.
- `approval_ttl` in the past → not approved even with clean findings.
- Budget `max_calls=1` → escalate `budget_exceeded` on the 2nd call.
- No blocker, no budget, ttl=never → approved with clean findings.