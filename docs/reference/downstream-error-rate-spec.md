# Downstream-Error-Rate Measurement Specification (#250)

> **Status:** Measurement spec (v0.2.2) — implementation deferred to partner-runner integration.
> **Author:** Debashish Ghosal · **Date:** 2026-08-26
> **F-07 companion:** Operational cost benchmark (#221, shipped v0.2.1)

---

## Problem

The engine deliberately stops at approval — it does not execute plans. Therefore, it cannot
measure whether an approved plan, when executed by a downstream runner, actually succeeds
or fails. This downstream error rate is the most important operational metric the engine
cannot produce solo.

## Measurement Goal

Compute the **downstream error rate** for approved plans: the fraction of approved plans
that, when executed by a partner runner, result in a failure (execution error, state
corruption, unexpected rollback, or user-reported incident).

```
downstream_error_rate = failed_executions / total_approved_plans
```

## Required Trace Fields

Partner runners must emit the following fields for each executed plan:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `plan_id` | string | yes | The approved plan's id |
| `goal_id` | string | yes | The goal the plan was generated for |
| `execution_status` | string | yes | `"success"`, `"failure"`, or `"partial"` |
| `error_type` | string | no | Classification of the error (e.g. `"timeout"`, `"state_corruption"`, `"rollback_triggered"`, `"unexpected_output"`) |
| `error_message` | string | no | Free-text description of what went wrong |
| `duration_ms` | integer | no | Execution wall-clock time in milliseconds |
| `steps_attempted` | integer | no | Number of plan steps that were executed |
| `steps_failed` | integer | no | Number of plan steps that failed |
| `executed_at` | datetime | yes | When execution started |
| `runner_version` | string | no | Version identifier of the partner runner |

## Integration Points

The partner runner can send execution results back to the engine through any of:

1. **Webhook callback** — The engine exposes a `POST /execution-results` endpoint that
   accepts the trace fields above as JSON. The runner calls this after each plan execution.
2. **Store append** — The runner writes directly to the same plan store (SQLite) that the
   engine uses, appending an `ExecutionTrace` record (see `types.py`).
3. **API push** — The runner calls `plancritic trace record` CLI or the equivalent MCP tool.

## Data Model

The engine already has `ExecutionTrace` in `src/planner_critic/types.py`:

```python
class ExecutionTrace(BaseModel):
    id: str
    plan_id: str
    task_id: str
    outcome: str
    failure_class: Literal["planning", "execution"] | None = None
    linked_finding_id: str | None = None
```

This may need to be extended to support the full measurement. The minimal extension:

```python
class ExecutionResult(BaseModel):
    plan_id: str
    goal_id: str
    execution_status: Literal["success", "failure", "partial"]
    error_type: str | None = None
    error_message: str | None = None
    duration_ms: int | None = None
    steps_attempted: int | None = None
    steps_failed: int | None = None
    executed_at: datetime
    runner_version: str | None = None
```

## Computing the Rate

The downstream error rate is computed as:

```
rate = count(execution_status == "failure") / count(total)
```

Segmentation by:
- Plan complexity (simple vs. multi-step)
- Goal domain (database, kubernetes, security, etc.)
- Risk tolerance (balanced vs. strict)
- Time window (daily, weekly, per-release)

## Next Steps

1. **v0.2.2:** Publish this spec as a reference document.
2. **v0.3.0:** Extend `ExecutionTrace` to support the full `ExecutionResult` schema.
3. **v0.3.0:** Add `POST /execution-results` endpoint to the HTTP server.
4. **v0.3.0:** Implement the rate computation and dashboard integration.