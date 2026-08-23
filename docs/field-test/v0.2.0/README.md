# v0.2.0 Field Test

> **Branch:** `0.2.0-m10-field-test` · **Status:** Planned

This directory contains the v0.2.0 field test artifacts.

## Contents

| File | Description |
|------|-------------|
| `field-test-plan.md` | Field test plan — 176 goals across 40 domains, 11 adversarial, 4 benchmark suites |
| `reports/` | Per-goal traces and report artifacts (populated after execution) |
| `results/` | Benchmark JSON outputs (populated after execution) |
| `scripts/` | Benchmark scripts (auto-repair, rollback credibility, family-histogram stasis) |

## Key Changes from v0.1.0

- **17 new goals** across 5 new domain groupings (IDP, MAO, SRE, SCP, FNG) + 3 new adversarial-policy goals
- **Strict-goal assertions** now use `approve_expected: false` (matching documented engine behavior)
- **4 benchmark suites** added: auto-repair (#177), rollback credibility (#182), family-histogram stasis (#183), security oracle (#123–#127)
- **6 enterprise safety mechanisms** field-tested: posture, run budget, state lock, ledger, quota, redaction
- **4 domain packs** evaluated: SecOps, Supply Chain, FinOps, Data Engineering

## See Also

- [Field test plan](field-test-plan.md)
- [v0.1.0 field test](../v0.1.0/field-test-plan.md)
- [WBS v0.2.0 part9](../../wbs/v0.2.0/wbs-v0.2.0-part9-release.md)