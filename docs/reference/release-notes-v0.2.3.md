# Release Notes — v0.2.3

**Date:** 2026-08-29

**What's new in PlannerCritic v0.2.3,** a measurement infrastructure release that fixes three community-raised issues (F-20 deterministic-corruption, F-14 approving_authority, DecisionContext) and ships the Deterministic Gate Canary and Extended Frozen-Claim Protocol.

---

## Quick Summary

| Metric | v0.2.2 | v0.2.3 |
|--------|--------|--------|
| Field test goals | 183 | 183 (same) |
| Balanced approved | 73/73 | 73/73 (same) |
| Strict escalated | 96/97 | 96/97 (same) |
| Deterministic tests | 1345 | 1359 (+14) |
| Gate Canary | N/A | 10/10 |
| Docker integration | N/A | 13 passed |
| Total cost | $0.49 | $0.60 |

## What Changed

### DecisionContext (#298)
- `DecisionContext` was defined but never populated — every trial record showed `model_id="unknown"`
- Now built from the provider spec at call time
- New optional fields on `ProviderSpec`: `model_version`, `temperature`

### Transit-Integrity Check (F-20, #296)
- `verify_transit_integrity()` added to the redaction module
- Asserts numeric/boolean fields survive `redact_dict()` unchanged
- 0 corruption events on boundary evaluator report

### Approving_Authority Enforcement (F-14, #297)
- `approving_authority` was test-only — no shipped surface bound it
- Added contract persistence to `PlanStore`
- `build_escalation_manager()` helper looks up authority from stored contract
- All 4 surfaces (CLI, HTTP, MCP tools, MCP server) now enforce

### Deterministic Gate Canary (#278)
- `plancritic gates canary --check` — 10 gate fixture pairs
- Zero LLM cost (~0.005s per gate)
- All 10 gates passing in dev and Docker

### Extended Frozen-Claim Protocol (#279)
- Denominator completeness requirement
- Artifact selection freeze
- Determinism boundary documentation

## Upgrade Notes
- No breaking changes
- `model_version` and `temperature` are optional TOML fields — existing configs work unchanged
- Gate canary fixtures are packaged with the wheel
