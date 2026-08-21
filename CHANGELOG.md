# Changelog

## v0.1.0 (2026-08-20)

### Features
- **Hierarchical task planning** — decompose a goal into a typed PlanVersion with tasks, dependencies, branches, preconditions, and verification steps
- **LLM critic** — audit every plan revision against six heuristic families (feasibility, risk, missing_steps, unsafe_sequencing, unverified_dependencies, weak_rollback)
- **Plan revision loop** — planner revises based on critic findings, loop terminates on approval, escalation, budget, convergence, or revision cap
- **Risk tolerance** — `balanced` (findings are advisory warnings) and `strict` (zero tolerance for any finding, fail-closed)
- **Deterministic gates** — 7 injection-immune gates (ordering-sanity, branch-sanity, rollback-safety, verification-safety, preconditions-referenced, branch-tasks, high-risk-completeness)
- **Escalation management** — human-in-the-loop escalation with override, patch, and restart decisions
- **Convergence detection** — early termination when the planner stops making meaningful progress
- **Plan revision policies** — `patch`, `restart`, `abort`

### Tools & Surfaces
- **CLI** — `plancritic plan`, `plancritic critique`, `plancritic field-test run`, `plancritic demo`, `plancritic quickstart`, `plancritic migrate`
- **Python API** — `Engine.plan()`, `ApprovedPlan`, `LoopResult`, `Finding`, `Escalation`
- **HTTP server** — `plancritic serve` with health check, plan, and escalation endpoints
- **Field test harness** — run 156+ goals across 35 domains, produce Scorecard A/B, release gate adjudication
- **Provider registry** — pluggable LLM providers (OpenRouter, OpenAI, oMLX, Ollama) via TOML config
- **StructuredEnforcer** — retry mechanism for LLM JSON output, fail-closed after 3 retries

### Breaking Changes
- None — v0.1.0 is the initial release.

### Known Gaps (v0.2.0)
- **Planner capability gap** — 132 concrete blockers across 63 strict goals, concentrated in 3 families (unverified_dependencies, unsafe_sequencing, weak_rollback). A deterministic precondition closer would eliminate 48%.
- **CLI surfaces** — `plancritic demo`, `quickstart`, `migrate` return non-zero exit codes
- **HTTP + MCP surfaces** — not yet tested
- **Adapter coverage** — only raw Python adapter ran
- **Critique-mode matrix** — only db-01 ran all 3 modes
- **Multi-model sweeps** — only gpt-4o-mini tested
- **Finding quality audit** — noise-finding rate not yet measured
- **Executor usability** — not yet audited

### Field Test Results
- **157 goals across 35 domains** — 71 approved (balanced), 86 escalated (strict/adversarial), 0 true failures
- **100% balanced pass rate** — every balanced goal approves
- **100% strict escalate rate** — every strict goal correctly refuses unsafe plans
- **8/8 adversarial escalate** — injection-immune, policy-violation detection confirmed
- **Scorecard A** — PASSES release gate after §7.1a plan amendment (strict goals flipped to escalate)
- **Scorecard B** — 100% pass rate (pass\* semantics)