# Field Test Report

**Date:** 2026-08-20 22:29:00 UTC
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
| core-api | dbm-02-mysql-to-postgres | None |

## Per-Goal Results (core-api dimension)

| Goal | Pass | Status | Reason | Revs | LLM Calls | Tasks | Findings |
|------|------|--------|--------|------|-----------|-------|----------|
| dbm-02-mysql-to-postgres | ❌ | approved | approved | 1 | 1 | 3 | 2 |
