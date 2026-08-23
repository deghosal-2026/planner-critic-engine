# Live-critic boundary-case report — v0.2.1 (#218)

- **Model:** `openai/gpt-4o-mini`
- **Trials per plan:** 5
- **Cases evaluated:** 6
- **Elapsed:** 156.3s
- **Estimated audits:** 60 (cases × trials × 2 plans)

## Metrics

| Metric | Value |
|---|---|
| label_flip_rate | 1.000 |
| family_migration_rate | 0.000 |
| evidence_drift_rate | 1.000 |
| underclaim_approvals | 0 |

## Interpretation

- `label_flip_rate > 0` → the critic is non-deterministic on identical input.
- `family_migration_rate > 0` → seeded defects landed in advisory families (under-claim blind spot, F-13).
- `evidence_drift_rate > 0` → claimed facts varied across trials (invented evidence; normalization cannot repair).
- `underclaim_approvals > 0` → defect plans with zero blockers (balanced tolerance would have approved).

Per-case × per-trial verdicts are in `live-boundary-report.json`.
