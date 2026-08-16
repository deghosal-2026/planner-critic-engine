# 06 — Security Compliance Baseline

> Sub-document of the [Design overview](../README.md). Mirrors the agent-tooltrust model: three public checklists, self-auditable, status published.

PlannerCritic Engine targets three concrete baselines. **Target: medium across all three.**

## 6.1 OWASP Agentic AI Top 10 — Target: Partial v0.1 → Broader v0.2

| OWASP Risk | PlannerCritic mitigation | Feature IDs | Coverage |
|---|---|---|---|
| **ASI01: Agent Goal Hijack** | Goal schema is typed & validated; deterministic gates audit structure, not goal semantics; the original goal is recorded in the plan store | F-01, F-12, F-09 | v0.1 ✅ |
| **ASI05: Unexpected Code Execution** | Fail-closed: an unapproved plan can never reach an executor | F-73 | v0.1 ✅ |
| **ASI08: Cascading Failures** | Independent critic reviews the plan before execution; loop bounded by revision cap + convergence + regression guard + budget | F-04, F-05, F-06, F-07, F-13 | v0.1 ✅ |
| **ASI09: Human-Agent Trust Exploitation** | Escalation to a human with a minimal, precise question; resolution audited in plan history | F-30, F-34 | v0.1 ✅ |
| **ASI10: Insufficient Monitoring & Logging** | Plan versions, critique history, escalations, execution traces, reason codes stored and queryable | F-09, F-50, F-77 | v0.1 ✅ |
| **ASI02: Tool Misuse** | Execution-time re-gate re-verifies preconditions before each step; adapters gate, they do not execute | F-46 | v0.1 ✅ |
| ASI03/04/06/07 | Out of direct scope (data leakage, supply chain, prompt injection at the tool layer) — covered by sibling repos (ToolTrust) | — | defer |

**v0.1: 6/10 direct coverage (ASI01/02/05/08/09/10). v0.2: ASI10 enriched via automated missed-critique promotion.**

## 6.2 OpenSSF Best Practices Badge — Target: Passing (floor)

| Criterion | Requirement | PlannerCritic action | Milestone |
|---|---|---|---|
| Passing (baseline) | Basic OSS hygiene | MIT license, SECURITY.md, CONTRIBUTING, CI, tests, .gitignore (already scaffolded) | v0.1 ✅ |
| Branch protection | PR review required | GitHub branch protection on `main` | v0.1 |
| Signed releases | Cryptographically signed artifacts | Sigstore / PyPI trusted publishing | v0.2 |
| Dynamic analysis | Fuzzer in CI | Property-based fuzzer for plan-schema / loop-controller | v0.2 |
| Silver (aspirational) | 2+ independent reviewers | Post-community maturity | Post v0.3 |

## 6.3 Custom PlannerCritic Security Baseline — Essential (v0.1) → Hardened (v0.2)

| Tier | Posture | Key requirements | Target |
|---|---|---|---|
| **Essential** | balanced | Deterministic gates always on; fail-closed; plan store versioning; escalation round-trip; per-goal budget; OpenSSF Passing; OWASP ASI01/02/05/08/09/10; reason codes; field-test gate | v0.1 ✅ |
| **Hardened** | strict | All Essential + automated missed-critique → standing-rule promotion; adversarial field matrix; OpenSSF Silver; property-based fuzzing | v0.2 |
| **Certified** (aspirational) | strict | All Hardened + tamper-evident plan store; external security review | v0.3+ |

`plancritic baseline check` (P1) audits a deployment against its chosen tier.

## 6.4 Summary

| Baseline | v0.1 | v0.2 (MEDIUM target) | Aspirational |
|---|---|---|---|
| OWASP Agentic Top 10 | 6/10 | 6/10 enriched | broader via siblings |
| OpenSSF Best Practices | Passing | Silver | Gold |
| PlannerCritic Security Baseline | Essential | Hardened | Certified (v0.3+) |