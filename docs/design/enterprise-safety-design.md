# Design D24 — Enterprise-Scale Safety Subsystem

> **As-built design for M6 (v0.2.0)** · Covers posture resolution, run budgets, state isolation, precondition ledger, blast-radius quotas, secret redaction, gate rationale metadata, and plan-signature persistence.

---

## 1. Subsystems Overview

M6 adds **eight safety subsystems** that together form the enterprise-scale safety layer:

| Subsystem | Module | Purpose |
|-----------|--------|---------|
| PostureResolver | `posture.py` | Context-aware risk-posture switching — env/k8s/git signals map to `strict` / `balanced` / `permissive` |
| RunBudget | `run_budget.py` | Run-level cost/depth/time ceilings enforced **above** the per-goal budget |
| ReplanClassifier | `run_budget.py` | Transient vs deterministic vs ambiguous execution-failure classification |
| StateView | `state.py` | Immutable read-only snapshots for critic consistency across concurrent plans |
| StateLock | `state.py` | Resource-URI-based write coordination across concurrent agent executions |
| PreconditionLedger | `ledger.py` | Deterministic, cross-revision precondition state store — compaction-proof |
| BlastRadiusQuotaGate | `quota.py` | Hard operator-defined resource/action limits with auto-escalation |
| SecretsRedactor | `redaction.py` | Deterministic secret/PII redaction across all external-output surfaces |
| GateRationale | `gates/base.py` | First-class `{author, rationale, added_at, stale_at}` on every gate definition |
| PlanSignatureStore | `store/base.py` + `versions.py` | Persistent `plan_signatures` table in SQLite + store protocol methods |

---

## 2. PostureResolver (`posture.py`)

### Design

```python
@dataclass(frozen=True)
class PostureRule:
    match: dict[str, str]      # e.g. {"env": "production"}
    posture: RiskTolerance      # strict | balanced | permissive

@dataclass(frozen=True)
class ResolvedPosture:
    posture: RiskTolerance
    rule_id: int | None
    context_signal: str | None
```

- **Rule ordering**: first-match-wins (ordered list). No rule → fallback to goal's `risk_tolerance`.
- **Context signals collected**: `ENV`, `PC_ENV`, `PC_GIT_BRANCH`, `PC_TERRAFORM_WORKSPACE`, `PC_K8S_NAMESPACE`, plus extensible `register_context_source()` for platform-specific signals.
- **Regex support**: if a rule's match value starts with `re:`, the remainder is treated as a regex pattern.
- **Fail-closed invariant**: `permissive` only relaxes the warning-acknowledgement requirement. Deterministic gate blockers are never overridden (F-73 holds in all tiers).
- **Permissive tier**: warnings tolerated without ack; blockers always block.

### Integration Points

- `schema/goal.py`: `RiskTolerance.PERMISSIVE` added to the enum.
- `approval.py`: `resolve_threshold()` treats `permissive` like `balanced` (warnings acknowledged) but with the semantic difference that warning acknowledgement is implicit.
- `cli/plan.py`: `--posture-rules-file` and `--posture` flags.

---

## 3. RunBudget + ReplanClassifier (`run_budget.py`)

### RunBudget

```python
@dataclass
class RunBudget:
    run_max_budget_usd: float | None
    run_max_depth: int | None
    run_max_time: float | None
```

- **Three ceilings**: spend (USD), cascading replan depth, wall-clock timeout.
- **Enforced above** the per-goal F-13 budget: the per-goal budget bounds a single plan's loop; the run-level ceiling bounds the entire execution lineage.
- **First breach latches** the `exceeded` state.

### ReplanClassifier

```python
class ReplanClassifier:
    TRANSIENT_CODES = {"timeout", "rate_limit", "network_error", ...}
    DETERMINISTIC_CODES = {"precondition_drift", "schema_mismatch", ...}
```

- Classifies execution failures as `TRANSIENT`, `DETERMINISTIC`, or `AMBIGUOUS`.
- Per-step retry budget (`step_max_retries`, default 3): after N transient retries on the same step, classification escalates to `AMBIGUOUS`.
- `TRANSIENT` → retry with backoff (not a replan); `DETERMINISTIC` → trigger replan (F-16); `AMBIGUOUS` → escalate.

### Reason Codes

| Code | Trigger |
|------|---------|
| `run_budget_exceeded` | `run_max_budget_usd` hit |
| `run_depth_exceeded` | `run_max_depth` hit |
| `run_timeout` | `run_max_time` elapsed |
| `transient_retry_triggered` | Transient failure → retry |
| `deterministic_replan_triggered` | Deterministic failure → replan |
| `ambiguous_replan_escalated` | Ambiguous → escalate |
| `step_retry_budget_exceeded` | Per-step retries exhausted |

---

## 4. StateView + StateLock (`state.py`)

### StateView

Immutable read-only snapshot of environment state, versioned and captured at plan-approval time:

```python
@dataclass(frozen=True)
class StateSnapshot:
    version: str
    captured_at: datetime
    snapshot: dict[str, Any]
```

- Critic + `EnvProbe` read from the `StateView`, not live mid-mutation state.
- `is_stale()` detects version or timestamp divergence — feeds the re-gate (F-46).
- Reason code: `state_view_stale` (info).

### StateLock

Resource-URI-based write coordination:

```python
class StateLock:
    strategy: LockStrategy  # WAIT | FAIL_FAST | ESCALATE
```

- Acquires a lock on a resource URI (`aws:sg-123`, `k8s:deploy-api`) when a plan step mutates it.
- Concurrent plans targeting the same resource are blocked per `lock_strategy`.
- `active_locks()` and `pre_execution_conflict()` for pre-execution conflict detection.
- Reason codes: `resource_locked_by_concurrent_execution` (blocker), `concurrent_resource_conflict` (blocker).

---

## 5. PreconditionLedger (`ledger.py`)

```python
@dataclass
class LedgerEntry:
    satisfied: bool
    satisfied_by: str | None
    satisfied_at: datetime | None
    verified_by: str | None
```

- Key-value store keyed by precondition fact name (stable across revisions).
- Updated deterministically on task completion.
- Survives context compaction: stored in the plan store (F-09), not the LLM context window.
- `process_plan(plan)`: detects redundant re-injection (`precondition_redundantly_re_injected`) and dropped preconditions (`precondition_dropped_from_compaction`).
- Gate `preconditions_referenced` (F-12) should query the ledger, not LLM memory.

---

## 6. BlastRadiusQuotaGate (`quota.py`)

Implements the `BaseGate` protocol:

```python
class BlastRadiusQuotaGate(BaseGate):
    name = "blast_radius_quota"
```

### Quota Types

| Quota | Enforcement | Reason Code |
|-------|-------------|-------------|
| `max_resource_changes` | Count tasks in the plan | `blast_radius_quota_breach` |
| `max_destructive_actions` | Count delete/destroy/drop/terminate/remove actions | `blast_radius_quota_breach` |
| `max_database_alterations` | Count tasks targeting schema/database | `blast_radius_quota_breach` |
| `restricted_clusters` | Block tasks targeting listed clusters | `blast_radius_restricted_cluster` |
| `restricted_actions` | Block tasks using listed actions | `blast_radius_restricted_action` |

- Pre-LLM enforcement: quota breach detected before the LLM critic runs.
- Posture interaction: `strict` → always blocker; `permissive` → warning for restricted resources, still blocker for restricted actions.

### CLI

```
plancritic quota list [--domain]
plancritic quota set <key> <value> [--domain]
plancritic quota check <plan_file> --quotas <quotas.yaml>
```

---

## 7. SecretsRedactor (`redaction.py`)

```python
class SecretsRedactor:
    mode: RedactMode  # REDACT | HASH | SKIP
```

### Built-in Patterns

AWS access keys, API keys (≥16 chars), OAuth2 tokens, JWTs, private key headers, Slack tokens, GitHub PATs, email, phone, SSN.

- Custom patterns via `add_custom_pattern(name, regex)`.
- `redact(text, surface="")` — runs before all external surfaces (LLM call, store, OTel, CLI).
- `redact_dict(data, surface)` — recursive dict redaction for structured data.
- Audit trail: `audits()` return `{pattern, count, locations}` metadata — no secret values logged.
- Reason code: `secret_redacted` (info).

---

## 8. Gate Rationale (`gates/base.py`)

Every `BaseGate` optionally carries:

```python
author: str | None
rationale: str | None
added_at: datetime | None
stale_at: datetime | None
amend_conditions: str | None
```

- `metadata` property returns a dict of all fields plus a computed `is_stale` flag.
- Backward-compatible: all fields default to `None` (existing gates unchanged).
- Stale-rule signal: when `stale_at` is in the past, `is_stale` returns `True` — surfaces in explain/escalation/dashboard.

---

## 9. PlanSignature Persistence (`store/`)

### Schema Migration v4

```sql
CREATE TABLE IF NOT EXISTS plan_signatures (
    plan_id   TEXT NOT NULL,
    version   INTEGER NOT NULL,
    signature TEXT NOT NULL,
    PRIMARY KEY (plan_id, version)
);
```

### Store Protocol Extension

```python
class PlanStore(ABC):
    def put_plan_signature(self, plan_id, version, signature): ...
    def get_plan_signatures(self, plan_id) -> list[tuple[int, str]]: ...
```

- Implemented in `InMemoryStore` (dict-based) and `SQLiteStore` (SQLite-backed).
- Signatures are written alongside each revision and queryable for cross-run oscillation analysis.

---

## 10. Reason Code Additions

The following reason codes were added to the catalog (`reason_codes.py`) for M6:

| Code | Category |
|------|----------|
| `posture_resolved` | Info |
| `run_budget_exceeded` | Escalation |
| `run_depth_exceeded` | Escalation |
| `run_timeout` | Escalation |
| `transient_retry_triggered` | Info |
| `deterministic_replan_triggered` | Info |
| `ambiguous_replan_escalated` | Warning |
| `step_retry_budget_exceeded` | Escalation |
| `state_view_stale` | Info |
| `resource_locked_by_concurrent_execution` | Blocker |
| `concurrent_resource_conflict` | Blocker |
| `precondition_redundantly_re_injected` | Info |
| `precondition_dropped_from_compaction` | Warning |
| `blast_radius_quota_breach` | Blocker |
| `blast_radius_restricted_cluster` | Blocker |
| `blast_radius_restricted_action` | Blocker |
| `secret_redacted` | Info |

---

## 11. Design Decisions

1. **PostureResolver is a pure function of context**: no state, no side effects — deterministic on identical context inputs.
2. **RunBudget and ReplanClassifier are separate**: budget ceilings and failure classification are orthogonal concerns; combining them would couple cost management with error semantics.
3. **StateView is per-plan, StateLock is cross-plan**: the View gives intra-plan consistency; the Lock provides inter-plan coordination. Two separate mechanisms for two separate scopes.
4. **Ledger lives in the plan store, not in memory**: persistence across revisions is the defining feature — the leder must survive context compaction.
5. **Quota gate runs before the LLM critic**: saving LLM cost by blocking quota-breaching plans deterministically.
6. **Redactor is purely regex-based, no ML**: deterministic, offline-only, auditable — no secrets ever leave the local process for classification.
7. **Gate rationale is optional**: backward-compatible with all existing gates; only gates that explicitly set `author` and `rationale` carry metadata.