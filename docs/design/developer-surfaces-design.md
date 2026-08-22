# Design D25 — Developer & Interactive Surfaces

> **As-built design for M7 (v0.2.0)** · Covers `plancritic check`, `plancritic diagnose`, `plancritic domains`, `plancritic policy`, `plancritic templates`, Python decorator ergonomics, and seed Rego policy library.

---

## 1. CLI Subcommands

M7 adds **6 new CLI subcommands** on top of the existing M1–M6 surface:

| Command | Module | Purpose |
|---------|--------|---------|
| `plancritic check` | `cli/check.py` | Lightweight deterministic gate eval (zero LLM) |
| `plancritic diagnose` | `cli/diagnose.py` | Sentry-style root-cause analyzer for execution traces |
| `plancritic domains` | `cli/domains.py` | Manage domain packs (list/show/add/test) |
| `plancritic policy` | `cli/policy.py` | Manage policies (list/add/test) |
| `plancritic templates` | `cli/templates.py` | Manage precondition templates (list/add/test) |

### 1.1 `plancritic check`

```
plancritic check [FLAGS] <PLAN_FILE>
  --domain <PACK>           Domain pack name or manifest path
  --policies-dir <PATH>     Directory with .rego / .yaml policy files
  --enforcement <MODE>      strict | permissive | dry_run (default: strict)
  --context <KEY=VAL>       Key=value context (repeatable)
  --fail-on-severity <LVL>  Minimum severity for non-zero exit
  --output <FMT>            text | json | yaml (default: text)
```

- Loads a PlanVersion JSON file, runs deterministic gates + domain gates + policies.
- Exit codes: `0` (pass), `1` (violation ≥ threshold), `4` (config error).
- Zero LLM calls, sub-second execution.

### 1.2 `plancritic diagnose`

```
plancritic diagnose <TRACE_FILE | PLAN_ID>
  --store <PATH>       SQLite store path (for plan_id lookup)
  --format <FMT>       human | json | markdown (default: human)
  --export-otel        Emit as OTel span attributes
```

- Deterministic rule engine (10 built-in rules) matching on `failure_class`, `outcome`, `reason_code`.
- Outputs: failing step, failure category, severity (1–5), root cause, suggested fix, trace excerpt.
- `unclassified_failure` for unmatched traces (never hallucinates).

### 1.3 `plancritic domains`

```
plancritic domains list
plancritic domains show <NAME>
plancritic domains add <PATH> [--name <NAME>]
plancritic domains test <NAME> <PLAN_FILE>
```

- `list` scans installed packs via `find_domain_packs()` namespace scanning.
- `test` dry-runs domain gates against a plan file, with exit code `1` on any violation.

### 1.4 `plancritic policy`

```
plancritic policy list
plancritic policy add <PATH>
plancritic policy test <NAME> <PLAN_FILE>
```

- `list` shows built-in policies + registered custom policies.
- `add` loads `.rego` files (as RegoGate) or `.yaml` policy manifests (as CelGate).
- `test` evaluates a policy against a plan file.

### 1.5 `plancritic templates`

```
plancritic templates list
plancritic templates add <NAME> --pattern <STR> [--description <STR>] [--action <STR>] [--target <STR>] [--risk-class <STR>]
plancritic templates test <NAME> <PLAN_FILE>
```

- `list` shows the 5 seed templates from `SEED_TEMPLATES` in `loop/autofix.py`.
- `add` registers a new `PreconditionTemplate` with specified pattern and task fields.
- `test` dry-runs the precondition closer against a plan file.

---

## 2. Python Decorator Ergonomics

Module: `guardrail.py`

### `@guardrail(goal, risk_tolerance, constraints, dry_run, on_escalate)`

Wraps a function to run the planning loop before execution:

```python
@guardrail(goal="Deploy to production safely", dry_run=True)
def deploy():
    ...
```

- On approval: calls the decorated function.
- On escalation: raises `EscalationRequired` (or calls `on_escalate` callback).
- `dry_run` mode: always executes, logs the gate decision.
- Docstring fallback: if `goal` is not provided, the function's docstring is used.

### `@re_gate(precondition_key, on_drift)`

Re-verifies a precondition before each call:

```python
@re_gate(precondition_key="db_healthy")
def execute_step():
    ...
```

- Raises `PreconditionDrift` on stale precondition (or calls `on_drift` callback).
- If `precondition_key` is empty, the function name is used.

### `@escalate(handler)`

Identity decorator that marks a function as an escalation handler:

```python
@escalate
def on_escalated(reason: str, findings: list[Finding]):
    notify_slack(reason)
```

### Exception Types

- `EscalationRequired(reason_code, findings)` — raised when the gate blocks execution.
- `PreconditionDrift(precondition_key)` — raised when a precondition has drifted.

---

## 3. Seed Rego Policy Library

Module: `policy.py` — `BUILTIN_POLICIES` now populated with 4 seed policies:

| Policy | Expression | Severity |
|--------|-----------|----------|
| `schema_valid` | `len(tasks) > 0` | blocker |
| `no_unsafe_ordering` | `not any(d['from_task'] == d['to_task'] ...)` | blocker |
| `high_risk_has_rollback` | `all(t has rollback for t in tasks if t.risk_class in (high, critical))` | blocker |
| `high_risk_has_verification` | `all(t has verification for t in tasks if t.risk_class in (high, critical))` | blocker |

---

## 4. Diagnostic Rules (in `cli/diagnose.py`)

10 deterministic rules matching on `failure_class` + `outcome`/`reason_code`:

| Rule | Category | Severity | Trigger |
|------|----------|----------|---------|
| Missing rollback | `precondition.missing_rollback` | 4 | `planning` + `missing_rollback` |
| Missing verification | `precondition.missing_verification` | 3 | `planning` + `missing_verification` |
| Unverified precondition | `precondition.unverified` | 3 | `planning` + `unverified_precondition` |
| Transient network | `execution.transient_network` | 2 | `execution` + `transient_retry_triggered` |
| Stale state snapshot | `state.snapshot_stale` | 3 | `execution` + `state_view_stale` |
| Resource locked | `state.resource_locked` | 4 | `execution` + `resource_locked_by_concurrent_execution` |
| Timeout | `execution.timeout` | 2 | `execution` + `timeout` |
| Auth failure | `execution.authentication` | 4 | `execution` + `auth_failure` |
| Permission denied | `execution.authorization` | 4 | `execution` + `permission_denied` |
| Blast radius quota | `quota.blast_radius` | 4 | `planning` + `blast_radius_quota_breach` |

---

## 5. Design Decisions

1. **check is the shared offline backend**: `plancritic check` is what the IDE extension (#157) and GitHub Action (#128) call for zero-LLM gate evaluation.
2. **Diagnose is rule-based, not LLM**: no hallucinated root causes. `unclassified_failure` for unmatched traces.
3. **Decorators are thin wrappers**: they delegate to the Engine facade; the decorator's job is ergonomics, not logic.
4. **Seed Rego policies mirror built-in gates**: they provide a Rego reference for teams writing custom policies.
5. **CLI error handling follows Unix conventions**: exit code 0 = pass, 1 = violation, 4 = config error.