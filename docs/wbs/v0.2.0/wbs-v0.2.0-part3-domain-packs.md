# WBS — PlannerCritic Engine v0.2.0 Part 3: Domain Packs + Scaffolding

> **Milestone covered:** M4 (Domain Packs + Scaffolding)
> **PRD covering this milestone:** [05-features](../../design/prd/05-features.md) (F-79 heuristic packs, F-85 init, F-87 templates) · [04-users-and-cujs](../../design/prd/04-users-and-cujs.md) (enterprise personas) · [02-architecture](../../design/prd/02-architecture.md) (§2.5)

---

## Milestone 4: Domain Packs + Scaffolding

**Objective:** Turn the M3 Domain Pack framework into installed, domain-specific strategies for the four highest-value enterprise domains — plus a golden-path scaffolding command and the inverse-rollback synthesizer that each pack extends. This is the "works with my domain" adoption story.

**PRD coverage:** F-79 (pack format), F-85 (init), F-87 (templates), §2.5 gate families extended per domain.
**CUJs covered:** CUJ 8 (workflow), CUJ 1 (install/configure), CUJ 14 (demo).

### M4.1 SecOps domain pack (#140) — `planner_critic.domains.secops`

Three gate evaluators + precondition catalog + SecOps critic prompt:
- **Blast-radius check** — isolation without a prior traffic drain → `secops_isolation_without_traffic_drain` (Risk family).
- **Forensic order of operations** — terminate/stop before snapshot → `secops_forensic_order_violation` (Unsafe sequencing + Unverified deps).
- **Least-privilege verification** — broad privilege (`sts:AssumeRole` `*`) without HITL → `secops_broad_privilege_without_hitl` (Risk + escalation F-30).
- Precondition catalog: `traffic_drained`, `snapshot_created`, `failover_complete`, `credential_revoked` (+ EnvProbe bindings).
- Hermetic corpus: ≥6 seeded flaws, $0 LLM. Gates additive to built-in six.

### M4.2 Software supply chain pack (#141) — `planner_critic.domains.supply_chain`

Three gate evaluators + catalog + prompt:
- **Transitive locking** — manifest edit without lockfile regeneration → `supply_chain_lockfile_not_regenerated` (Unsafe sequencing).
- **Breaking-change pre-checks** — major semver bump without migration script/linter before deploy → `supply_chain_breaking_change_without_migration` (Missing steps + Unverified deps).
- **Artifact integrity** — deploy of unsigned/unattested artifact → `supply_chain_unsigned_artifact` / `supply_chain_missing_sbom` (Missing steps + Weak rollback).
- Preconditions: `lockfile_regenerated`, `migration_script_passed`, `artifact_signed`, `sbom_generated`, `linter_clean`. Ecosystem-agnostic lockfile detection (npm/poetry/cargo/go). ≥6 seeded flaws.

### M4.3 FinOps pack (#142) — `planner_critic.domains.finops`

Two gate evaluators + catalog + prompt:
- **Grace-period enforcement** — instant delete without snapshot + notify + wait → `finops_delete_without_grace_period` (Unsafe sequencing + Risk).
- **Budget-boundary gates** — expansion breaches localized cap without executive override → `finops_budget_boundary_breached` (Risk + escalation F-30).
- Preconditions: `snapshot_created`, `owner_notified`, `grace_period_elapsed`, `budget_within_cap`, `spend_forecast_checked`; cloud-agnostic billing EnvProbe (AWS/GCP/Azure adapters). ≥6 seeded flaws. Constructor arg: `FinOpsDomainPack(budget_cap=...)`.

### M4.4 Data engineering pack (#143) — `planner_critic.domains.data_eng`

Three gate evaluators + catalog + prompt:
- **Schema pre-verification** — destructive query without verified backup → `data_eng_destructive_without_backup` (Missing steps + Unverified deps).
- **SLA-window constraints** — migration outside maintenance window → `data_eng_migration_outside_maintenance_window` (Unverified deps).
- **Dual-write rollback plans** — live migration without dual-write/fallback → `data_eng_migration_without_dual_write` / `...without_fallback` (Weak rollback).
- Preconditions: `backup_created`, `backup_verified_restorable`, `maintenance_window_active`, `dual_write_enabled`, `fallback_path_defined`, `schema_compatibility_checked`. EnvProbe works against Postgres + MySQL. ≥8 seeded flaws.

### M4.5 `planner-critic init --template` (#155)

- `init --template <domain>` scaffolds a full `.planner-critic/` from golden-path templates: domain_config.yaml, gates (Python + Rego), preconditions/catalog.yaml, mocks, tests/test_gates.py.
- Five templates: `k8s-gitops-deploy`, `secops-incident-response` (→M4.1), `supply-chain-patching` (→M4.2), `data-eng-migration` (→M4.4), `custom` (interactive).
- Flags: `--list-templates`, `--inject` (merge into existing), `--upgrade-templates` (versioned, merge-friendly). Generated tests use the #156 plugin.

### M4.6 Inverse Rollback DAG Synthesizer (#160)

- `InverseRollbackSynthesizer` builds G_rollback at approval time from a domain-pack action-inversion registry (reversibility: `DETERMINISTIC` / `SNAPSHOT_RESTORE` / `NON_REVERSIBLE`→`sys.noop`), reversing every forward edge; validated acyclic (Kahn's).
- Partial rollback on failure at step N: filters to completed forward steps, executes in reverse topological order.
- Reason codes: `rollback_dag_generated`, `rollback_execution_triggered`, `rollback_non_reversible_step_skipped`, `rollback_missing_action_mapping`. `assert_rollback_dag_valid` pytest helper for #156.

### M4 Task Checklist

| # | Task | Verify | Issue | Status |
|---|------|--------|-------|--------|
| 1 | SecOps pack (3 gates + catalog + prompt + corpus) | drain-ordering/forensic-order/least-privilege fire; clean plan no false positives | [#140](https://github.com/deghosal-2026/planner-critic-engine/issues/140) · [ ] |
| 2 | Supply-chain pack (3 gates + catalog + prompt) | lockfile/migration/SBOM fire; ecosystem-agnostic | [#141](https://github.com/deghosal-2026/planner-critic-engine/issues/141) · [ ] |
| 3 | FinOps pack (2 gates + catalog + prompt) | grace-period + budget-cap fire; cloud-agnostic probes | [#142](https://github.com/deghosal-2026/planner-critic-engine/issues/142) · [ ] |
| 4 | Data-eng pack (3 gates + catalog + prompt) | backup/SLA/dual-write fire; Postgres+MySQL probes | [#143](https://github.com/deghosal-2026/planner-critic-engine/issues/143) · [ ] |
| 5 | `init --template` + 5 templates + flags | one-command scaffold; generated tests pass; `--inject`/`--upgrade` safe | [#155](https://github.com/deghosal-2026/planner-critic-engine/issues/155) · [ ] |
| 6 | Inverse rollback synthesizer + action-inversion registry | G_rollback reverses edges; partial rollback unwinds completed-only; acyclic | [#160](https://github.com/deghosal-2026/planner-critic-engine/issues/160) · [ ] |

### M4 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| Pack installability | each pack `pip install`-able + registers under `planner_critic.domains.*` | pack suite |
| Gate accuracy | 0 false positives on clean seeded plans; all designed gates fire on flaws | hermetic corpus |
| Prompt prepend | domain prompt visible in critic system prompt | prompt test |
| Scaffolding | `init --template` produces a passing pack + tests | template suite |
| Rollback synthesis | inverse DAG acyclic + field-test partial-unwind run | synthesizer suite |
| Coverage | >95% | `--cov-fail-under=95` |
| Lint | 0 ruff + 0 mypy strict | `ruff` + `mypy` |

### M4 Exit Gate

- [ ] All 4 packs installable + hermetic corpus green ($0 LLM)
- [ ] Packs additive to built-in six; disabling a pack restores default behavior
- [ ] `init --template` + inverse-rollback synthesizer working
- [ ] Coverage > 95; lint clean; code review passed

**Dependency:** M3. **Produces for M5+:** precondition catalogs + action-inversion registries + reason codes that M6 quotas and M9 scale field-tests consume.