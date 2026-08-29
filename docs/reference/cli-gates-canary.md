# `plancritic gates canary` — Gate Health Check

## Usage

```bash
plancritic gates canary --check    # CI gate: exit 1 if any gate fails
plancritic gates canary --report   # Machine-readable JSON output
plancritic gates canary --canary-dir <path>   # Override fixtures directory
```

## Description

Runs a deterministic health check against all 10 gate classes. Each gate is tested against a `(good_plan, bad_plan)` fixture pair:
- The good plan must produce zero findings (gate approves).
- The bad plan must produce a blocker with the expected reason code.

This catches silent gate death: if a refactor breaks a gate, blocker counts drop and read as "improved safety." The canary prevents that by asserting every gate still fires on a known-bad plan.

## Exit Codes

- `0`: All gates pass.
- `1`: One or more gates failed (only with `--check`).

## Report Format (JSON)

```json
{
  "version": "v0.2.3",
  "total": 10,
  "passed": 10,
  "failed": 0,
  "results": [
    {
      "gate": "ordering",
      "healthy": true,
      "expected_blocker": "unsafe_ordering",
      "actual_findings": ["unsafe_ordering"],
      "error": ""
    }
  ]
}
```

## Gate Coverage

| Gate | Fixture | Expected Blocker |
|------|---------|-----------------|
| `schema_valid` | `tests/canary/schema_valid/` | `plan_schema_invalid` |
| `ordering` | `tests/canary/ordering/` | `unsafe_ordering` |
| `dep_cycles` | `tests/canary/dep_cycles/` | `dependency_cycle` |
| `verification` | `tests/canary/verification/` | `missing_verification` |
| `verification_ordering` | `tests/canary/verification_ordering/` | `verification_after_consumer` |
| `rollback` | `tests/canary/rollback/` | `missing_rollback` |
| `rollback_credible` | `tests/canary/rollback_credible/` | `rollback_unreachable` |
| `preconditions` | `tests/canary/preconditions/` | `unverified_precondition` |
| `parallel_safety` | `tests/canary/parallel_safety/` | `unsafe_parallelization` |
| `requirement_trace` | `tests/canary/requirement_trace/` | `step_not_traced_to_criterion` |

## Zero LLM Cost

All canary checks are deterministic. Cost per check: ~0.005s per gate, negligible in CI.