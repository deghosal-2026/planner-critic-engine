# Field Test Report

**Date:** 2026-08-20 22:47:02 UTC
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
| core-api | mcc-01-aws-to-gcp | None |

## Per-Goal Results (core-api dimension)

| Goal | Pass | Status | Reason | Revs | LLM Calls | Tasks | Findings |
|------|------|--------|--------|------|-----------|-------|----------|
| mcc-01-aws-to-gcp | ❌ | escalated | converged_stalled | 2 | 2 | 8 | 6 |
