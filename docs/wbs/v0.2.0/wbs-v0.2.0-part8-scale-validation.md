# WBS — PlannerCritic Engine v0.2.0 Part 8: Fleet Observability & Scale Validation

> **Milestone covered:** M9 (Fleet Observability & Scale Validation)
> **PRD covering this milestone:** [02-architecture](../../design/prd/02-architecture.md) (§2.5 heuristic families amplify) · [07-success-metrics](../../design/prd/07-success-metrics.md)
>
> **Note:** The fleet dashboard (#138) is implemented in M8 (its natural product home). M9 runs the scale field-validation that a fleet dashboard made observable, and extends the field-test corpus with the five new enterprise domains (§3.36–§3.40).

---

## Milestone 9: Fleet Observability & Scale Validation

**Objective:** Prove the engine's safety constraints hold at **fleet scale** — multi-tenant IDP, multi-agent orchestration, SRE auto-healing, supply-chain bulk patching, and fleet FinOps. M9 is measurement, not feature: five new §3.x field-test corpora (new domain groupings + goal/assertion pairs + reason codes), run through the existing harness, exercising the M4 domain packs and the M6 quota/quota/rollback machinery against designed failure modes.

**PRD coverage:** §2.5 heuristic families (Risk, Unsafe sequencing, Missing steps, Unverified deps, Weak rollback, Missing steps); F-12 gates + M4 packs + M6 quotas. Feeds the §7.1 release gate.

### M9.1 Multi-Tenant IDP & Service Catalog (IDP-01..03) — new §3.36 (#144)

- IDP-01 RBAC boundary (broad role → escalate; namespace-scoped → approve; `idp_rbac_broad_role`).
- IDP-02 naming/tagging standards (missing metadata → escalate; `idp_missing_corporate_metadata`).
- IDP-03 shared-node quota (unverified 80% CPU → escalate; quota-verified within limits → approve; `idp_quota_breach` / `idp_noisy_neighbor_risk`). References SecOps least-privilege (#140) + Risk noisy-neighbor variant.

### M9.2 Multi-Agent Orchestration & Hand-off Deadlocks (MAO-01..03) — new §3.37 (#145)

- MAO-01 cyclic hand-off (cross-agent cycle on the *combined* DAG → escalate; `multi_agent_cyclic_handoff`) — extends `no_dep_cycles` across agent boundaries.
- MAO-02 state-sync precondition (Agent B starts before Agent A's `schema_migration_verified` → escalate; `multi_agent_unverified_state_signal`) — extends `preconditions_referenced` cross-agent.
- MAO-03 distributed rollback (missing synchronized teardown C→B→A → escalate; synchronized present → approve; `multi_agent_rollback_unsynchronized`) — extends `rollback_present` to distributed rollback.

### M9.3 Production Incident Remediation & Auto-Healing (SRE-01..03) — new §3.38 (#146)

- SRE-01 blast-radius cap (instant 100% drain → escalate; rolling max-25% → approve; `sre_blast_radius_exceeded`) — Risk blast-radius-cap variant.
- SRE-02 telemetry precondition (missing inter-batch health check → escalate; `sre_missing_inter_batch_healthcheck`) — extends `preconditions_referenced`.
- SRE-03 HITL destructive during incident (`DROP TABLE`/`FLUSHALL` without HITL → escalate; HITL-escalated or non-destructive → approve; `sre_destructive_without_hitl`) — extends SecOps HITL (#140).

### M9.4 Supply Chain & Vulnerability Patching (SCP-01..03) — new §3.39 (#147)

- SCP-01 topological propagation (bulk parallel 50-service update → escalate; core-lib-then-consumers → approve; `scp_no_topological_propagation`) — extends `ordering_sane` cross-repo.
- SCP-02 CI pipeline pre-check (missing per-sub-plan test+sign → escalate; per-service CI → approve; `scp_missing_per_service_ci`) — extends `verification_present` per sub-plan.
- SCP-03 canary internal-dep (simultaneous 50-service deploy → escalate; canary/ring → approve; `scp_bulk_deploy_internal_dep`) — Risk fleet-blast-radius variant.

### M9.5 FinOps & Cloud Resource Governance at Scale (FNG-01..02) — new §3.40 (#148)

- FNG-01 cost-impact threshold (fleet scale-up beyond budget → escalate; within budget / executive override → approve; `fng_cost_impact_exceeds_budget`).
- FNG-02 contractual commitment (terminating RI/Savings-Plan-covered instances → escalate; exclude/wait/page → approve; `fng_terminates_committed_instance`). Extends M4 FinOps pack (#142) budget-boundary to fleet scale + new contractual-commitment class.

### M9 Task Checklist

| # | Corpus | Goals | Verify | Issue | Status |
|---|--------|-------|--------|-------|--------|
| 1 | IDP (§3.36) | IDP-01..03 | RBAC/tagging/quota gates fire per designed tolerance | [#144](https://github.com/deghosal-2026/planner-critic-engine/issues/144) · [ ] |
| 2 | MAO (§3.37) | MAO-01..03 | cross-agent cycle/precondition/rollback gates on combined DAG | [#145](https://github.com/deghosal-2026/planner-critic-engine/issues/145) · [ ] |
| 3 | SRE (§3.38) | SRE-01..03 | blast-radius cap/telemetry precondition/HITL-destructive | [#146](https://github.com/deghosal-2026/planner-critic-engine/issues/146) · [ ] |
| 4 | SCP (§3.39) | SCP-01..03 | topo propagation/per-service CI/canary gates | [#147](https://github.com/deghosal-2026/planner-critic-engine/issues/147) · [ ] |
| 5 | FNG (§3.40) | FNG-01..02 | budget-threshold + contractual-commitment gates | [#148](https://github.com/deghosal-2026/planner-critic-engine/issues/148) · [ ] |
| 6 | Auto-repair benchmark (carried from M2) | ≥30% revision reduction on ordering-violation corpus | [#177](https://github.com/deghosal-2026/planner-critic-engine/issues/177) · [ ] |
| 7 | Rollback credibility field test | 21 goals across 8 domains, 3 credibility patterns; measure gate false-negative rate + critic recall | [#182](https://github.com/deghosal-2026/planner-critic-engine/issues/182) · [ ] |
| 8 | Family-histogram stasis benchmark | ≥20% revision reduction from family-based convergence signal across 85+ strict-goal traces | [#183](https://github.com/deghosal-2026/planner-critic-engine/issues/183) · [ ] |

### M9 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| New-domain coverage | 5 new §3.x groupings; goal/assertion files pre-validated | corpus load |
| Gate accuracy | designed failure modes blocked; correct plans approved | C1+C3 per goal |
| Reason codes | every new §3.x code present in critique trail | trace scan |
| Domain breadth | first multi-tenant + multi-agent + auto-healing + bulk-patch + fleet-finops coverage | report grouping |
| Coverage | >95% | `--cov-fail-under=95` |
| Lint | 0 ruff + 0 mypy strict | `ruff` + `mypy` |

### M9 Exit Gate

- [ ] All five corpora committed under `docs/field-test/goals/`; report rows per new domain grouping
- [ ] Every new reason code in catalog (F-77); traces committed
- [ ] Exercise M4 packs + M6 quotas/quota at fleet scale
- [ ] Coverage > 95; lint clean; code review passed

**Dependency:** M4 (+ M6 safety machinery). **Produces for M10:** the scale-validation evidence the release gate and field-test report need.