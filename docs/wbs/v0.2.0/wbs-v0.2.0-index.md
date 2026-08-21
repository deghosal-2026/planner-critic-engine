# WBS — PlannerCritic Engine v0.2.0 (Index)

> Work breakdown for the **v0.2.0 (P1) release** — the security-hardened, extensible, enterprise-integrated second release (see [PRD 09 — Roadmap](../../design/prd/09-roadmap.md) §9.2). Ten milestones (M1–M10) across nine part files. **Author:** Debashish Ghosal · **Date:** 2026-08-21 · **Status:** Planned (issues filed)
>
> PRDs: [01-why](../../design/prd/01-why.md) · [02-architecture](../../design/prd/02-architecture.md) · [04-users-and-cujs](../../design/prd/04-users-and-cujs.md) · [05-features](../../design/prd/05-features.md) · [06-security](../../design/prd/06-security-baseline.md) · [07-success-metrics](../../design/prd/07-success-metrics.md) · [08-risks](../../design/prd/08-risks.md) · [09-roadmap](../../design/prd/09-roadmap.md)

---

## 1. Milestone Overview

> **Sequencing rationale:** v0.2.0 is sequenced *base-first*. M1 closes every field-test gap left by v0.1.0 so we build on a proven base. M2 is a dependency-free efficiency win. M3 ships the one-time extensibility infrastructure (domain-pack framework + policy engine + pytest plugin) that M4's packs and most downstream surfaces consume. M5 (security oracle) runs on the v0.1.0 base and is parallelizable with M3–M6. M6/M7/M8 are three parallel product stones; M9 does scale field-validation; M10 is release. No milestone starts before its dependencies' exit gates pass.

| M# | Name | Core content | Issues | Part file | Status |
|----|------|--------------|--------|-----------|--------|
| **M1** | **Field-Test Closure of v0.1.0** | Close every not-run / deferred / partial v0.1.0 field-test capability (CLI, HTTP/MCP, adapters, critique-mode, escalation/explain/replan, never-exercised caps, cross-dimension, budget/termination, model sweeps, Q3/Q4 audits) + failure-clustering and positive-control analysis | [#85–98](https://github.com/deghosal-2026/planner-critic-engine/issues/85), [#172–173](https://github.com/deghosal-2026/planner-critic-engine/issues/172) | [part1](wbs-v0.2.0-part1-field-test-closure.md) | **In Progress** (#85–93, #97–98 done; #172–173 pending) |
| M2 | Deterministic Loop Efficiency | Topological auto-repair, deterministic precondition closer, oscillation/auto-converge — cut LLM revision cost deterministically | [#130](https://github.com/deghosal-2026/planner-critic-engine/issues/130), #131, #152 | [part2](wbs-v0.2.0-part2-loop-framework.md) | Planned |
| M3 | Extensibility Framework | Domain Pack protocol, OPA/Rego/CEL policy engine, pytest-planner-critic | [#129](https://github.com/deghosal-2026/planner-critic-engine/issues/129), #139, #156 | [part2](wbs-v0.2.0-part2-loop-framework.md) | Planned |
| **M4** | **Domain Packs + Scaffolding** | SecOps / supply-chain / FinOps / data-eng packs + `init --template` + inverse-rollback synthesizer | [#140–143](https://github.com/deghosal-2026/planner-critic-engine/issues/140), #155, #160 | [part3](wbs-v0.2.0-part3-domain-packs.md) | Planned |
| M5 | Security & Trust Oracle (SWE-bench) | SWE-bench Verified corpus → critic validation → injection harness → gate regression → standing-rule promotion + label-migration harness | [#123–127](https://github.com/deghosal-2026/planner-critic-engine/issues/123), [#171](https://github.com/deghosal-2026/planner-critic-engine/issues/171) | [part4](wbs-v0.2.0-part4-security-oracle.md) | Planned |
| M6 | Enterprise-Scale Safety | Dynamic posture, run budgets, state locking, precondition ledger, blast-radius quotas, secret/PII redaction, gate rationale metadata | [#132](https://github.com/deghosal-2026/planner-critic-engine/issues/132), #149–151, #158, #159, [#174](https://github.com/deghosal-2026/planner-critic-engine/issues/174) | [part5](wbs-v0.2.0-part5-enterprise-safety.md) | Planned |
| M7 | Developer & Interactive Surfaces | TUI, `diagnose`, `studio`, IDE extensions, `plancritic check` | [#136](https://github.com/deghosal-2026/planner-critic-engine/issues/136), #137, #153, #154, #157, #162 | [part6](wbs-v0.2.0-part6-developer-surfaces.md) | Planned |
| M8 | Enterprise Integration & Adoption | GitHub Action/GitLab, Backstage, AutoGen, Slack, webhook notifier, fleet dashboard | [#128](https://github.com/deghosal-2026/planner-critic-engine/issues/128), #133–135, #138, #161 | [part7](wbs-v0.2.0-part7-integration-adoption.md) | Planned |
| M9 | Fleet Observability & Scale Validation | Fleet dashboard + new §3.x scale field-test corpora (IDP, MAO, SRE, SCP, FinOps) | [#144–148](https://github.com/deghosal-2026/planner-critic-engine/issues/144) | [part8](wbs-v0.2.0-part8-scale-validation.md) | Planned |
| **M10** | **Release Activities** | Packaging, security posture (OpenSSF Silver), release-gate sweep, migration, release notes, final quality gate, tag/ship | [#163–169](https://github.com/deghosal-2026/planner-critic-engine/issues/163) | [part9](wbs-v0.2.0-part9-release.md) | Planned |

## 2. Dependency Graph

```
M1 (Field-Test Closure) — proven base
  └─► M2 (Loop Efficiency)             [independent]
  ├──► M3 (Extensibility Framework)    [foundation]
  │      ├──► M4 (Domain Packs)        [needs M3 framework]
  │      └──► (pytest plugin, policy engine consumed downstream)
  ├──► M5 (Security Oracle)            [parallelizable with M3–M6]
  │      └──► (feeds M9 scale + M4 heuristic packs)
  └──► M6 (Enterprise Safety)          [parallel; needs M4 pack registries for quotas/rollback]
         ├──► M7 (Developer Surfaces)  [parallel]
         ├──► M8 (Integration/Adoption)[parallel]
         └──► M9 (Scale Validation)    [needs M1-M4 + packs]
                └──► M10 (Release)     [needs all preceding]
```

**Hard ordering:** M1 → M3 → M4 → M10. **Parallel:** M2, M5, M6, M7, M8 (after M1). M9 needs M4; M10 needs everything.

## 3. GitHub Issue Ranges

> All 0.2.0 issues are attached to the **0.2.0-M1…0.2.0-M10** GitHub milestones. Titles carry the `[0.2.0-Mx]` prefix reflecting the milestone, so the prefix on an issue is authoritative for its milestone. Flip each task's checkbox when its issue closes.

| Milestone | Issue range | API / surface scope |
|-----------|-------------|---------------------|
| M1 Field-Test Closure | [#85–#98](https://github.com/deghosal-2026/planner-critic-engine/issues/85), [#172–#173](https://github.com/deghosal-2026/planner-critic-engine/issues/172) | close v0.1.0 field-test + audit gaps; failure-shape clustering, positive control |
| M2 Loop Efficiency | [#130](https://github.com/deghosal-2026/planner-critic-engine/issues/130), #131, #152 | loop controller auto-fix |
| M3 Extensibility Framework | [#129](https://github.com/deghosal-2026/planner-critic-engine/issues/129), #139, #156 | domain-pack / policy / pytest |
| M4 Domain Packs | [#140–#143](https://github.com/deghosal-2026/planner-critic-engine/issues/140), #155, #160 | 4 packs + scaffolding + rollback synth |
| M5 Security Oracle | [#123–#127](https://github.com/deghosal-2026/planner-critic-engine/issues/123), [#171](https://github.com/deghosal-2026/planner-critic-engine/issues/171) | SWE-bench security chain + label-migration harness |
| M6 Enterprise Safety | [#132](https://github.com/deghosal-2026/planner-critic-engine/issues/132), #149–#151, #158, #159, [#174](https://github.com/deghosal-2026/planner-critic-engine/issues/174) | posture/budget/state/ledger/quota/redact + gate rationale |
| M7 Developer Surfaces | [#136](https://github.com/deghosal-2026/planner-critic-engine/issues/136), #137, #153, #154, #157, #162 | TUI/diagnose/studio/IDE/check |
| M8 Integration & Adoption | [#128](https://github.com/deghosal-2026/planner-critic-engine/issues/128), #133–#135, #138, #161 | CI/Backstage/AutoGen/Slack/webhook/dashboard |
| M9 Scale Validation | [#144–#148](https://github.com/deghosal-2026/planner-critic-engine/issues/144) | fleet field-test corpora |
| M10 Release Activities | [#163–#169](https://github.com/deghosal-2026/planner-critic-engine/issues/163) | packaging/security/sweep/migration/docs/gate/ship |

## 4. Posture Toward v0.1.0 WBS

- **v0.1.0 WBS is frozen history** (`docs/wbs/v0.1.0/`). Do not edit those files; they record shipping commits for the 0.1.0 release.
- This index is the **active** WBS. The rest of the docs tree ([`docs/design`](../design), [`docs/architecture`](../architecture), [`docs/reference`](../reference), [`docs/field-test`](../field-test)) is upgraded **in place** for v0.2.0.

## 5. Design Documents to Author

The v0.1.0 WBS authored D1–D19. v0.2.0 adds/updates design docs for the new subsystems. As each milestone builds its subsystem, the implementer writes the design doc capturing the as-built behavior.

| # | Doc | Path | Authored in | Contents |
|---|-----|------|-------------|----------|
| D20 | Domain Pack framework | `docs/design/domain-pack-design.md` | M3 | `DomainPack` protocol, pack format, engine integration |
| D21 | Policy engine (OPA/Rego/CEL) | `docs/design/policy-engine-design.md` | M3 | `PolicyEngine`, `RegoGate`/`CelGate`, policy-pack format |
| D22 | Deterministic loop auto-fix | `docs/design/deterministic-autofix-design.md` | M2 | topo auto-repair, precondition closer, oscillation signature |
| D23 | SWE-bench security oracle | `docs/field-test/corpus/swebench-security/` | M5 | corpus spec, loader, metrics |
| D24 | Enterprise safety | `docs/design/enterprise-safety-design.md` | M6 | posture resolver, run budget, state lock, ledger, quota |
| D25 | Developer surfaces | `docs/design/developer-surfaces-design.md` | M7 | TUI, diagnose rules, studio, `plancritic check` |
| D26 | Integration surfaces | `docs/design/integration-surfaces-design.md` | M8 | CI runner, Backstage, Slack/webhook notifier |
| D27 | Release notes v0.2.0 | `docs/reference/release-notes-v0.2.0.md` | M10 | changelog, breaking changes, upgrade path |
| D28 | API reference update | `docs/reference/api.md` | M7–M8 | new CLI/HTTP/MCP/pack commands |

## 6. Standard Milestone Exit Gate

**Every milestone** closes with the same gate (mirrors v0.1.0). The per-milestone part files may add extra checks; these four are non-negotiable:

- [ ] **Code review passed** — every `.py` file in the milestone reviewed; findings resolved
- [ ] **Test coverage > 95%** — `pytest --cov=planner_critic --cov-fail-under=95`
- [ ] **Lint clean** — `ruff check .` 0 errors AND `mypy --strict` 0 errors
- [ ] **Comments + docstrings in all code** — module docstring, function/method docstrings, inline comments on non-obvious logic

Plus the `#1` invariant carried from v0.1.0: **hermetic by default** — CI never calls a paid LLM; deterministic gates stay free; a deterministic-gate blocker is never overridden by the LLM critic.