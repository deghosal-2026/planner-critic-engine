# Policy Engine Design (D21)

> **Authored:** M3 (#129) — 2026-08-22  
> **Status:** As-built

## Overview

The Policy Engine provides an external deterministic gate layer that runs *in addition to* the built-in Python gates. Two evaluators are provided: a CEL-style pure-Python expression evaluator (no binary) and an OPA/Rego evaluator (requires `opa` binary).

## Protocol

```python
class PolicyEngine(ABC):
    name: str
    severity: Severity
    message: str | None
    reason_code: str | None

    @abstractmethod
    def evaluate(self, plan: PlanVersion) -> list[Finding]: ...
```

## CelGate

Pure-Python evaluator for inline CEL-style expressions. No external binary required.

```python
gate = CelGate(
    name="custom-gate",
    expression='any(t["risk_class"] == "critical" for t in tasks)',
    severity="blocker",
    message="critical risk tasks not allowed",
)
```

### Expression Scope

Evaluated via a restricted `eval()` with these variables:
- `tasks` — list of task dicts (id, risk_class, blast_radius, etc.)
- `dependencies` — list of dependency dicts
- `branches` — list of branch dicts
- Allowed builtins: `len`, `any`, `all`, `sorted`, `set`, `list`, `dict`, `str`, `int`, `float`, `min`, `max`, `sum`, `range`, `True`, `False`, `None`

### Error Handling

If the expression raises (syntax error, division by zero, etc.), the gate produces a finding with `reason_code="policy_violation"`.

## RegoGate

Shells out to the `opa eval` binary. Requires `opa` on `PATH`. Falls back gracefully when OPA is unavailable with a warning finding (`policy_evaluation_error`).

```python
gate = RegoGate(
    name="no-tasks",
    module='package test\nviolation contains "no tasks" if count(data.tasks) == 0',
    query="data.test.violation",
)
```

### Loading

- `module` — inline Rego source string, or a `Path` to a `.rego` file (read at construction time)
- `query` — the Rego query target (e.g. `data.test.violation`)
- Input is the plan serialized as JSON, loaded as a `--data` file alongside the Rego module

### Graceful Degradation

When `opa` is not on `PATH`, `evaluate()` produces a single warning finding with `reason_code="policy_evaluation_error"` rather than raising. This lets CI pipelines run deterministically even without the binary.

## Reason Codes

- `policy_violation` — a CEL or Rego policy produced a violation finding
- `policy_evaluation_error` — `opa` binary not found or evaluation failed

## Deferred

- `plancritic policy add/list/test` CLI — the policy engine is functional via the Python API; the CLI belongs with the broader pack/policy CLI effort
- Seed Rego policy library mapping the six built-in gates — the `BUILTIN_POLICIES` list is currently empty