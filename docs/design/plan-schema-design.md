# D2 — Plan Schema Design

> **Authored in:** M1 (Core Engine) · **Status:** Built, mirrors implementation · **WBS:** D2 · **Refs:** [PRD 02 §2.8](../../design/prd/02-architecture.md#28-plan-schema-typed-sketch), [PRD 05 F-02/F-15](../prd/05-features.md)

## Purpose

Define the typed Goal/PlanVersion/Task/Branch/Dependency/VerificationStep/RollbackStep models exactly as built in M1 (`planner_critic/schema/goal.py`, `planner_critic/schema/plan.py`). This is the source of truth for the schema's fields, validation rules, immutability contract, and serialization.

## Design Decisions (see D13 for the full DD log)

- **Pydantic v2 everywhere, frozen.** Every model is `frozen=True`: a validated value cannot be mutated after construction. This makes an approved plan a stable, auditable value that can be safely shared, stored, and diffed.
- **Strict enums** (`StrEnum`). Unknown enum values fail construction with `ValidationError` — a goal or plan can never carry an untyped posture.
- **Flat schema package.** `schema/goal.py` + `schema/plan.py`; the loop, gates, and store all import from here. No circular imports (schema never imports loop/approval/gates).

## Goal (`schema/goal.py`, F-01)

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | `str` | required | non-empty |
| `description` | `str` | required | validated non-blank |
| `constraints.budget` | `Budget` | `Budget()` | optional ceilings, all `int ≥ 1` |
| `constraints.budget.max_tokens` | `int \| None` | `None` | uncapped when unset |
| `constraints.budget.max_calls` | `int \| None` | `None` | uncapped when unset |
| `constraints.budget.max_revisions` | `int \| None` | `None` | uncapped when unset |
| `constraints.time` | `str \| None` | `None` | free-form deadline |
| `constraints.environment` | `str \| None` | `None` | assumed environment |
| `constraints.tools` | `list[str]` | `[]` | tools assumed available |
| `risk_tolerance` | `RiskTolerance` | `BALANCED` | `strict \| balanced` |
| `replan_policy` | `ReplanPolicy` | `PATCH` | `patch \| restart \| abort` |
| `approval_ttl` | `timedelta \| None` | `None` | `None` = never expires (∞) |
| `metadata` | `dict[str, str]` | `{}` | opaque |

**Validation:** `id`/`description` non-empty; description non-blank; budget fields non-negative via `ge=1` (cannot spend negative tokens). Enums are strict.

## PlanVersion (`schema/plan.py`, F-02 + F-15)

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | unique per revision |
| `goal_id` | `str` | goal this plan serves |
| `plan_schema_version` | `str` | fixed `PLAN_SCHEMA_VERSION = "0.1.0"` |
| `version` | `int ≥ 1` | revision counter |
| `parent_version` | `str \| None` | id of the parent revision (None for root) |
| `created_at` | `datetime` | UTC, default now |
| `tasks` | `list[Task]` | the steps |
| `dependencies` | `list[Dependency]` | ordering edges |
| `branches` | `list[Branch]` | explicit fan-out/fan-in shape |

### Task

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | unique |
| `description` | `str` | what it accomplishes |
| `action` | `str` | verb |
| `target` | `str` | object acted on |
| `parallel_group` | `str \| None` | tasks sharing a group run concurrently |
| `preconditions` | `list[Precondition]` | each grounded in an established fact and/or an `EnvProbe` |
| `verification` | `VerificationStep \| None` | what/how/expected |
| `rollback` | `RollbackStep \| None` | trigger/action/safety_guard |
| `risk_class` | `RiskClass` | `low\|medium\|high\|critical` |
| `blast_radius` | `str` | `low\|medium\|high\|critical` |

### Precondition

| Field | Type | Notes |
|---|---|---|
| `description` | `str` | human label |
| `fact` | `str` | the fact that must be established |
| `established_by` | `str \| None` | earlier task id or `env:` fact that establishes it |
| `probe` | `EnvProbe \| None` | optional live-state probe (M2) |

### VerificationStep / RollbackStep

- `VerificationStep{what, how, expected}` — field names deviate from the PRD sketch's `what_to_check` (they express the same contract with shorter names).
- `RollbackStep{trigger, action, safety_guard}` — verbatim PRD.

### Dependency

`{from_task, to_task, kind{hard|soft}, reason}` — `hard` = must precede (drives DAG/ordering gates); `soft` = advisory (never enforces ordering).

### Branch

`Branch{id, kind{fan_out|fan_in}, tasks[], join{all|any|quorum}}`.

## Structural Invariants (model validator)

Enforced **at construction** so a malformed plan can never flow into a gate or a store:

1. Task ids are unique.
2. Every dependency `from_task`/`to_task` resolves to an existing task; no self-dependencies.
3. Every branch's `tasks[]` resolves to existing tasks.
4. A `parallel_group` may not list a task twice.
5. **A hard dependency between two tasks of the same `parallel_group` is rejected** — they run concurrently, so a hard edge is a contradiction. (Soft edges inside a group are allowed: advisory.)

## Immutability & Serialization

- `frozen=True` gives immutability-once-stored: after construction a `PlanVersion` cannot be mutated. New revisions are **new instances** with `version` incremented and `parent_version` pointing at the parent's id.
- `PlanVersion.to_dict()` / `from_dict()` are lossless JSON round-trips (`model_dump(mode="json")` / `model_validate`), used by the store (M2) and the plan diff (M2).

## Edge Cases Covered (tests)

- Empty task list → schema-invalid finding.
- Duplicate task ids, unknown dependency endpoints, self-dependency, unknown branch members → `ValidationError`.
- Hard edge inside a parallel group → `ValidationError`; soft edge inside a group → allowed.
- `created_at` survives round-trip (does not silently reset).
- Strict `str`-typed enums round-trip as strings in JSON (store-friendly).