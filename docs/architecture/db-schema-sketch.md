# D4 — Plan Store / Versioning Schema Sketch

> **Authored in:** M2 (Plan Store + LLM Provider Layer) · **Status:** Current baseline · **WBS:** D4 ·
> **Refs:** [PRD §2.1 core value](../design/prd/02-architecture.md#21-core-value), §2.8 plan schema, [D1 architecture](architecture-v0.1.0.md)

The production store is **SQLite behind a pluggable interface** (§2.1 item 5):
every plan revision, its critique findings, escalations, and execution traces
are first-class rows so the full planning history is diff-able and replay-able.
Postgres-ready means the *protocol* is DB-agnostic — the DDL below is the
SQLite default.

## Tables

| Table | Key | Contents |
|-------|-----|----------|
| `plan_versions` | `(plan_id, version)` | One immutable plan revision per row |
| `findings` | `(plan_id, version)` | Critique findings for that revision |
| `escalations` | `plan_id` | The escalation (one per plan) |
| `execution_traces` | `plan_id, seq` | Per-step execution records, in order |
| `links` | `(plan_id, version, trace_id)` | Approved-revision ↔ trace forensics link |
| `schema_migrations` | `version` | Applied schema-migration versions (reversible) |

## `plan_versions`

```sql
CREATE TABLE plan_versions (
    plan_id             TEXT NOT NULL,
    goal_id             TEXT NOT NULL,
    plan_schema_version TEXT NOT NULL,      -- plan-schema version (F-27)
    version             INTEGER NOT NULL,   -- revision number, >= 1
    parent_version      TEXT,               -- NULL for root plans
    created_at          TEXT NOT NULL,      -- ISO-8601 UTC
    body                TEXT NOT NULL,      -- full PlanVersion JSON
    PRIMARY KEY (plan_id, version)
);
CREATE INDEX idx_plan_goal ON plan_versions (goal_id, plan_id, version DESC);
```

- `body` holds the typed `PlanVersion` as JSON (lossless `to_dict` round-trip).
- Indexed columns (`goal_id`, `version`) make `list_plans` / latest-revision
  lookups fast without parsing bodies.
- **Immutability:** rows are written once; a revision is never mutated.
  Revisions are linked by `parent_version`, building the draft→critique→revise
  lineage that diff/replay consume.

## `findings`

```sql
CREATE TABLE findings (
    plan_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    body    TEXT NOT NULL,                  -- list[Finding] JSON
    PRIMARY KEY (plan_id, version)
);
```

One row per revision holding that revision's full finding set. The loop writes
findings together with the revision they were produced against, so the critique
history is reconstructable without re-running the critic.

## `escalations`

```sql
CREATE TABLE escalations (
    plan_id TEXT NOT NULL,
    body    TEXT NOT NULL,                  -- Escalation JSON
    PRIMARY KEY (plan_id)
);
```

A plan escalates at most once (the loop stops at the first escalation).

## `execution_traces` + `links`

```sql
CREATE TABLE execution_traces (
    plan_id TEXT NOT NULL,
    seq     INTEGER PRIMARY KEY AUTOINCREMENT,
    body    TEXT NOT NULL                   -- ExecutionTrace JSON
);
CREATE TABLE links (
    plan_id  TEXT NOT NULL,
    version  INTEGER NOT NULL,
    trace_id TEXT NOT NULL,
    PRIMARY KEY (plan_id, version, trace_id)
);
```

`links` connects an approved revision to the trace that later executed it
(§2.1 item 7 — planning-vs-execution forensics).

## Schema versioning + migration (F-27)

- Every row carries `plan_schema_version` (semver, currently `0.1.0`).
- `schema_migrations` records applied **reversible** migrations:

```sql
CREATE TABLE schema_migrations (
    version   INTEGER NOT NULL,             -- monotonic migration id
    applied_at TEXT NOT NULL,
    PRIMARY KEY (version)
);
```

- Up/down pairs live in `planner_critic/store/versions.py`; `migrate` applies
  pending ups and can reverse applied downs.
- Old versions remain readable: `body` is self-describing JSON, and readers
  key on `plan_schema_version` before parsing.

## Side-channel (§7.2)

The store is a side channel: if the DB is unreachable, the store raises
`StoreUnavailable`; the caller warns and continues in memory. Nothing in the
planning path blocks on the store — persistence is best-effort until healthy.

## Out of scope (M2)

- Postgres dialect DDL (interface is ready; a `PostgresStore` is a later drop-in).
- JSON1/JSONB column projection queries (list/diff operate on parsed bodies).
- Retention / compaction policies.
