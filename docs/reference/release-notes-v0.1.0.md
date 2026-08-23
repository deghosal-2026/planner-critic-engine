# Release Notes v0.1.0

**Date:** 2026-08-20
**Package:** `planner-critic` v0.1.0 — [PyPI](https://pypi.org/project/planner-critic/)

## What's New

### Core Engine
- **Hierarchical task planning** — decompose a goal into a typed PlanVersion with tasks, dependencies, branches, preconditions, and verification/rollback steps
- **Independent LLM critic** — audit every plan revision against six heuristic families (feasibility, risk, missing_steps, unsafe_sequencing, unverified_dependencies, weak_rollback) with severity-graded findings
- **Plan revision loop** — planner revises based on critic findings; loop terminates on approval, escalation, budget exhaustion, convergence stall, or revision cap
- **Risk tolerance** — `balanced` (findings are advisory warnings, gates are the hard floor) and `strict` (zero tolerance for any finding, fail-closed)
- **7 deterministic gates** — injection-immune gates for ordering-sanity, branch-sanity, rollback-safety, verification-safety, preconditions-referenced, branch-tasks, and high-risk completeness
- **Escalation management** — human-in-the-loop with override, patch, and restart decisions
- **Convergence detection** — early termination when the planner stops making meaningful progress, saving LLM calls
- **Plan revision policies** — `patch`, `restart`, `abort`

### Tools & Surfaces
- **CLI** — `plancritic plan`, `critique`, `field-test run`, `demo`, `quickstart`, `migrate`, `serve`
- **Python API** — `Engine.plan()`, `ApprovedPlan`, `LoopResult`, `Finding`, `Escalation`
- **HTTP server** — health check, plan, and escalation endpoints
- **Provider registry** — pluggable LLM providers (OpenRouter, OpenAI, oMLX, Ollama) via TOML config
- **StructuredEnforcer** — retry mechanism for LLM JSON output, fail-closed after 3 retries

### Quality & Testing
- **Field test harness** — 157 goals across 35 domains, automated scorecard generation
- **Field test results** — Scorecard A (strict plan semantics) and Scorecard B (pass\* semantics) published
- **Release gate** — §7.3 criteria adjudicated: PASS with planned amendments

## Field Test Results

| Metric | Result |
|--------|--------|
| Balanced goals approved | 71/71 (100%) |
| Strict goals escalated | 81/81 (100%) |
| Adversarial goals escalated | 8/8 (100%) |
| True failures | 0 |
| Deterministic gate passes | 156/157 (99%) |
| Scorecard A (post-amendment) | PASS |
| Scorecard B (pass\* semantics) | 100% |

## Breaking Changes

None — v0.1.0 is the initial release.

## Known Issues

- **Planner capability gap** — 132 concrete blockers across 63 strict goals, concentrated in 3 families (unverified_dependencies, unsafe_sequencing, weak_rollback). A deterministic precondition closer in v0.2.0 would eliminate 48%.
- **CLI surfaces** — `demo`, `quickstart`, `migrate` return non-zero exit codes
- **HTTP + MCP surfaces** — not yet tested
- **Adapter coverage** — only raw Python adapter ran
- **Multi-model** — only gpt-4o-mini tested
- **Finding quality audit** — noise-finding rate not yet measured
- **Executor usability** — not yet audited

## Documentation

| Doc | Location |
|-----|----------|
| Field Test Results | `docs/field-test/v0.1.0/field-test-results-0.1.0.md` |
| Field Test Plan | `docs/field-test/v0.1.0/field-test-plan.md` |
| Architecture | `docs/architecture/architecture-v0.1.0.md` |
| API Reference | `docs/reference/api.md` |
| Design Decisions | `docs/design/design-decisions.md` |
| Demo Scenario | `docs/design/demo-scenario.md` |
| Changelog | `CHANGELOG.md` |