# Field Test Report

**Date:** 2026-08-20 22:45:18 UTC
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
| core-api | win-01-ad-functional-level | None |

## Per-Goal Results (core-api dimension)

| Goal | Pass | Status | Reason | Revs | LLM Calls | Tasks | Findings |
|------|------|--------|--------|------|-----------|-------|----------|
| win-01-ad-functional-level | ❌ | escalated | revision_cap_reached | 4 | 1 | 10 | 1 |
