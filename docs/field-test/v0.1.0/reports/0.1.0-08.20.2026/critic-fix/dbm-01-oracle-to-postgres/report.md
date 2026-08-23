# Field Test Report

**Date:** 2026-08-20 22:47:55 UTC
**Config:** plancritic-fieldtest.toml
**Loop:** {'mode': 'deterministic-first', 'revision_cap': 4}
**Total executions:** 1
**Passed:** 0
**Failed:** 1
**Pass rate:** 0%

## Dimensions

| Dimension | Total | Passed | Failed |
|-----------|-------|--------|--------|
| core-api | 1 | 0 | 1 |

## Failures

| Dimension | Goal | Error |
|-----------|------|-------|
| core-api | dbm-01-oracle-to-postgres | None |

## Per-Goal Results (core-api dimension)

| Goal | Pass | Status | Reason | Revs | LLM Calls | Tasks | Findings |
|------|------|--------|--------|------|-----------|-------|----------|
| dbm-01-oracle-to-postgres | ❌ | escalated | converged_stalled | 2 | 2 | 8 | 6 |
