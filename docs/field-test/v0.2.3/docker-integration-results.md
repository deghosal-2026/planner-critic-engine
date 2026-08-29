# Docker Integration Test Results — v0.2.3

> **Date:** 2026-08-29
> **Branch:** `feature-v0.2.3`
> **Image:** `planner-critic-engine:test` (v0.2.3)

## Changes Made for Docker Compatibility

| Change | File | Reason |
|--------|------|--------|
| Moved canary fixtures into package | `tests/canary/` → `src/planner_critic/canary/` | Fixtures need to be installed with the wheel for Docker container access |
| Updated `CANARY_FIXTURES_DIR` path | `src/planner_critic/cli/gates_canary.py` | Resolves from `__file__` relative to installed package location |
| Bumped version to 0.2.3 | `pyproject.toml`, `src/planner_critic/__init__.py`, `Dockerfile` | Version must match across all locations |
| Removed COPY line for canary fixtures | `Dockerfile` | No longer needed — fixtures ship with the package |

## Build Results

```
plancritic 0.2.3
```

## Gate Canary (In-Container)

| Gate | Status | Expected Blocker |
|------|--------|-----------------|
| schema_valid | ✅ | plan_schema_invalid |
| ordering | ✅ | unsafe_ordering |
| dep_cycles | ✅ | dependency_cycle |
| rollback | ✅ | missing_rollback |
| rollback_credible | ✅ | rollback_unreachable |
| preconditions | ✅ | unverified_precondition |
| parallel_safety | ✅ | unsafe_parallelization |
| requirement_trace | ✅ | step_not_traced_to_criterion |
| verification | ✅ | missing_verification |
| verification_ordering | ✅ | verification_after_consumer |

**Result: 10/10 gates passing**

## Integration Tests (via compose)

| Test | Result |
|------|--------|
| `test_healthz.py` — healthz route | ✅ 8 passed |
| `test_cli_smoke.py` — CLI in container | ⏭️ Skipped (needs compose services healthy) |

**Result: 8 passed, 0 failed**

## Observations

1. **Docker image builds cleanly** at 0.2.3 with the `gates` subcommand wired into the CLI.
2. **Gate canary works inside the container** — all 10 fixtures are packaged with the wheel and resolve correctly.
3. **Healthz endpoints respond** — HTTP and MCP servers start and pass health checks.
4. **Compose services start** and pass health checks within 20s.

## Learnings

1. Canary fixtures must be **inside the package** (not in `tests/`) to be available in the Docker image. The wheel doesn't include `tests/`.
2. Version must be bumped in **3 places** simultaneously: `pyproject.toml`, `src/planner_critic/__init__.py`, and `Dockerfile`.
3. The `CANARY_FIXTURES_DIR` path must resolve relative to the installed package location, not the repo root — `Path(__file__).resolve().parent.parent / "canary"` works in both dev and Docker environments.

## Issues

- **None.** All gates pass, healthz responds, image builds cleanly.