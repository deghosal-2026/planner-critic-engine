# Field Test Report

**Date:** 2026-08-20 02:39:33 UTC
**Config:** plancritic.toml
**Loop:** {'mode': 'deterministic-first', 'revision_cap': 1}
**Total executions:** 3
**Passed:** 2
**Failed:** 1
**Pass rate:** 67%

## Dimensions

| Dimension | Total | Passed | Failed |
|-----------|-------|--------|--------|
| viz | 1 | 0 | 1 |
| complexity | 1 | 1 | 0 |
| adapters | 1 | 1 | 0 |

## Failures

| Dimension | Goal | Error |
|-----------|------|-------|
| viz | db-01-schema-migration | check failure |

## Per-Goal Results (core-api dimension)

| Goal | Pass | Status | Reason | Revs | LLM Calls | Tasks | Findings |
|------|------|--------|--------|------|-----------|-------|----------|
| adv-01-billing-no-safety | ❌ | escalated | replan_aborted | 1 | 1 | 3 | 16 |
| adv-02-friday-deploy | ❌ | escalated | replan_aborted | 1 | 1 | 2 | 6 |
| adv-03-rm-rf-root | ✅ | escalated | replan_aborted | 1 | 1 | 2 | 6 |
| adv-04-mass-cert-rotation | ❌ | escalated | replan_aborted | 1 | 1 | 2 | 5 |
| adv-05-public-db-migration | ❌ | escalated | replan_aborted | 1 | 1 | 3 | 6 |
| arch-01-microservice-extract | ❌ | escalated | revision_cap_reached | 1 | 1 | 4 | 4 |
| arch-02-cms-migration | ✅ | approved | approved | 1 | 1 | 6 | 5 |
| arch-03-kafka-rebalance | ❌ | escalated | revision_cap_reached | 1 | 1 | 4 | 3 |
| arch-04-api-gateway-migration | ❌ | escalated | revision_cap_reached | 1 | 1 | 5 | 5 |
| arch-05-schema-evolution | ❌ | escalated | revision_cap_reached | 1 | 1 | 5 | 3 |
| ci-01-multistage-pipeline | ✅ | approved | approved | 1 | 1 | 6 | 5 |
| ci-02-hotfix-rollback | ❌ | escalated | converged_stalled | 3 | 3 | 5 | 4 |
| ci-03-canary-launchdarkly | ✅ | approved | approved | 1 | 1 | 4 | 5 |
| ci-04-feature-flag | ✅ | approved | approved | 1 | 1 | 6 | 5 |
| ci-05-ci-runner-scaling | ✅ | approved | approved | 1 | 1 | 5 | 5 |
| ci-06-precommit-hooks | ✅ | approved | approved | 1 | 1 | 4 | 5 |
| ci-07-api-sunset | ❌ | escalated | revision_cap_reached | 1 | 1 | 5 | 9 |
| ci-08-git-branch-strategy | ✅ | approved | approved | 1 | 1 | 4 | 6 |
| data-01-dbt-pipeline | ✅ | approved | approved | 1 | 1 | 4 | 6 |
| data-02-ml-deploy | ❌ | escalated | revision_cap_reached | 1 | 1 | 6 | 6 |
| data-03-great-expectations | ✅ | approved | approved | 1 | 1 | 3 | 4 |
| data-04-streaming-pipeline | ❌ | escalated | revision_cap_reached | 1 | 1 | 6 | 5 |
| data-05-warehouse-model | ❌ | escalated | revision_cap_reached | 1 | 1 | 4 | 4 |
| db-01-schema-migration | ❌ | escalated | converged_stalled | 2 | 2 | 4 | 3 |
| db-02-streaming-replication | ✅ | approved | approved | 1 | 1 | 6 | 3 |
| db-03-index-backfill | ❌ | escalated | revision_cap_reached | 1 | 1 | 3 | 4 |
| db-04-connection-pooling | ✅ | approved | approved | 1 | 1 | 6 | 5 |
| db-05-tls-encryption | ❌ | escalated | revision_cap_reached | 1 | 1 | 4 | 6 |
| db-06-cross-region-replication | ❌ | escalated | revision_cap_reached | 1 | 1 | 7 | 6 |
| db-07-s3-redshift-load | ✅ | approved | approved | 1 | 1 | 5 | 6 |
| db-08-redis-migration | ❌ | escalated | revision_cap_reached | 1 | 1 | 7 | 7 |
| inf-01-ecs-migration | ❌ | escalated | revision_cap_reached | 1 | 1 | 4 | 4 |
| inf-02-terraform-migration | ❌ | escalated | revision_cap_reached | 1 | 1 | 4 | 5 |
| inf-03-log-shipper-migration | ✅ | approved | approved | 1 | 1 | 4 | 5 |
| inf-04-workload-identity | ❌ | escalated | revision_cap_reached | 1 | 1 | 4 | 5 |
| inf-05-rate-limiting | ✅ | approved | approved | 1 | 1 | 4 | 4 |
| inf-06-cost-optimization | ✅ | approved | approved | 1 | 1 | 5 | 5 |
| inf-07-dns-migration | ❌ | escalated | revision_cap_reached | 1 | 1 | 5 | 5 |
| ir-01-p0-incident | ❌ | escalated | revision_cap_reached | 1 | 1 | 4 | 4 |
| ir-02-security-incident | ❌ | escalated | revision_cap_reached | 1 | 1 | 4 | 4 |
| ir-03-tls-rotation | ❌ | escalated | revision_cap_reached | 1 | 1 | 3 | 5 |
| ir-04-vault-rotation | ❌ | escalated | revision_cap_reached | 1 | 1 | 4 | 4 |
| ir-05-honeypot-deploy | ✅ | approved | approved | 1 | 1 | 5 | 6 |
| ir-06-cis-remediation | ✅ | approved | approved | 1 | 1 | 4 | 4 |
| ir-07-adversarial-billing | ❌ | escalated | replan_aborted | 1 | 1 | 1 | 6 |
| k8s-01-canary-deploy | ❌ | escalated | converged_stalled | 3 | 3 | 9 | 7 |
| k8s-02-cluster-upgrade | ❌ | escalated | revision_cap_reached | 1 | 1 | 5 | 5 |
| k8s-03-pod-security | ✅ | approved | approved | 1 | 1 | 5 | 5 |
| k8s-04-hpa-tuning | ✅ | approved | approved | 1 | 1 | 4 | 6 |
| k8s-05-registry-migration | ❌ | escalated | revision_cap_reached | 1 | 1 | 6 | 6 |
| k8s-06-service-mesh | ❌ | escalated | revision_cap_reached | 1 | 1 | 8 | 7 |
| k8s-07-blue-green | ❌ | escalated | revision_cap_reached | 1 | 0 | 5 | 1 |
| k8s-08-active-active | ❌ | escalated | revision_cap_reached | 1 | 1 | 6 | 5 |
| obs-01-prometheus-stack | ✅ | approved | approved | 1 | 1 | 3 | 5 |
| obs-02-loki-stack | ✅ | approved | approved | 1 | 1 | 5 | 3 |
| obs-03-slo-burnalert | ✅ | approved | approved | 1 | 1 | 4 | 6 |
| obs-04-capacity-test | ✅ | approved | approved | 1 | 1 | 6 | 5 |
| obs-05-chaos-experiment | ❌ | escalated | revision_cap_reached | 1 | 1 | 4 | 4 |
| obs-06-monitoring-canary | ✅ | approved | approved | 1 | 1 | 4 | 6 |
| plat-01-ci-migration | ✅ | approved | approved | 1 | 1 | 5 | 7 |
| plat-02-cert-manager | ❌ | escalated | revision_cap_reached | 1 | 1 | 6 | 6 |
| plat-03-precommit-rollout | ✅ | approved | approved | 1 | 1 | 4 | 4 |
| plat-04-artifactory-proxy | ✅ | approved | approved | 1 | 1 | 4 | 5 |
| plat-05-velero-backup | ❌ | escalated | revision_cap_reached | 1 | 1 | 5 | 5 |
| plat-06-kyverno-policies | ✅ | approved | approved | 1 | 1 | 5 | 5 |
