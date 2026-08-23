# Field Test Report

**Date:** 2026-08-20 22:53:06 UTC
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
| core-api | int-01-key-extraction | None |

## Per-Goal Results (core-api dimension)

| Goal | Pass | Status | Reason | Revs | LLM Calls | Tasks | Findings |
|------|------|--------|--------|------|-----------|-------|----------|
| int-01-key-extraction | ❌ | escalated | converged_stalled | 2 | 2 | 6 | 3 |
