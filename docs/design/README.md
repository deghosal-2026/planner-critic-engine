# Design — PlannerCritic Engine

> This README is the **overview and index** for the product requirements (the `prd/` sub-docs), plus the future design-spec, decisions, and demo-scenario. Start here.

**Version:** 0.2 (Draft)
**Date:** 2026-08-16
**Owner:** Debashish Ghosal
**Repo:** `deghosal-2026/planner-critic-engine` (private → OSS)
**Package:** `planner-critic` / import `planner_critic` / CLI `plancritic`

---

## Executive Summary

PlannerCritic Engine is a **hierarchical planning system with an independent LLM critic**. A *planner* LLM decomposes a goal into a typed plan — tasks, dependencies, ordering, verification steps, and rollback points. A separate *critic* LLM audits every subtask before execution across six heuristic families — feasibility, risk, missing steps, unsafe sequencing, unverified dependencies, weak rollback — producing severity-graded findings. The planner revises in a **bounded revise-until-approved loop** until the critic approves or the system **escalates to a human** with a minimal, precise question.

The insight that justifies the project: **planning is the weakest part of agent systems, and single-pass planning is blind.** Agents act too early, skip hard subproblems, and execute plans nobody reviewed. A model "reviewing" its own plan is agreement with extra steps (64.5% blind-spot rate). PlannerCritic separates the draft role from the critique role so a plan survives an independent adversarial pass — the way a code review works — before anything executes. A cross-model critic measurably pays for itself (Copilot "Rubber Duck" closed 74.7% of the gap to Opus-alone).

The plan is a **first-class, versioned, inspectable artifact** — you can diff revisions, see which critiques drove which changes, replay the trace, render the task DAG, and trace whether a failed run was a planning failure or an execution failure.

**Core architectural principle:** PlannerCritic Engine is **fully LLM- and framework-agnostic**. The core engine owns the mechanics (plan schema, critique heuristics, loop controller, convergence detection, escalation manager, plan store) and speaks plain typed JSON. Two pluggable surfaces hang off it: an **LLM provider layer** (config-driven registry; the OpenAI-compatible transport is the first implementation, built *on top of* the registry) and **framework adapters** (raw Python, LangGraph, PydanticAI, CrewAI, OpenAI Agents SDK, MCP — the tooltrust six). The engine never knows which model or framework called it.

---

## Scope Snapshot (decided 2026-08-16)

- **Delivery surfaces:** Python library + CLI + MCP server + HTTP service (full blast); React web UI in v0.2
- **LLM providers:** config-driven registry built first; OpenAI-compatible transport built on it; per-goal spend budget enforced by the loop controller
- **Critique:** dual-mode — `deterministic-first` (default, free gates before LLM critic) → `llm-every-revision` (option); six heuristic families; diff-aware critique on revisions N>1
- **Loop:** revision cap + convergence detection + regression guard + budget-hit escalation
- **Approval:** per-goal threshold via `risk_tolerance` (strict = zero warnings; balanced = warnings acknowledged)
- **Escalation:** CLI + MCP tools in v0.1; AIDE-style web UI in v0.2
- **Adapters:** the tooltrust six, *with* execution-time re-gate (`before-each-step | off`)
- **Plan store:** pluggable interface; SQLite default, Postgres-ready
- **Forensics:** planning-vs-execution failure tagging + missed-critique → suggested deterministic check (feeds LessonExtractor)
- **Viz & observability:** plan-graph export (Mermaid), trace replay, reason-code catalog
- **Demo:** domain-agnostic sample corpus (migration, rollout, refactor, incident-response) with seeded flaws
- **Field test:** hermetic CI gate (no paid LLM) + local-model (OMLX/Ollama) release sweep
- **Security:** OWASP Agentic Top 10 (ASI01/02/05/08/09/10), OpenSSF Passing floor, PlannerCritic Essential → Hardened baseline

**v0.1.0 is feature-rich by design** — the first release ships the core engine, both critique modes, all six adapters with re-gate, planning-vs-execution forensics, plan-graph viz, trace replay, diff-aware critique, reason codes, and the security baseline. See [prd/09-roadmap.md](prd/09-roadmap.md).

---

## PRD Document Map

| # | Sub-document | Covers |
|---|---|---|
| 01 | [prd/01-why.md](prd/01-why.md) | Why — market context, the pain, OSS goals, sources |
| 02 | [prd/02-architecture.md](prd/02-architecture.md) | What — core engine, provider layer, critique engine, loop, plan schema, non-goals, demo corpus |
| 03 | [prd/03-landscape.md](prd/03-landscape.md) | Landscape & identity — competitive table, the gap, our wedge |
| 04 | [prd/04-users-and-cujs.md](prd/04-users-and-cujs.md) | Target users + 12 CUJs |
| 05 | [prd/05-features.md](prd/05-features.md) | Feature set (F-01…F-79) + interface surfaces |
| 06 | [prd/06-security-baseline.md](prd/06-security-baseline.md) | OWASP / OpenSSF / PlannerCritic baselines |
| 07 | [prd/07-success-metrics.md](prd/07-success-metrics.md) | Success criteria & reliability |
| 08 | [prd/08-risks.md](prd/08-risks.md) | Risks & open questions |
| 09 | [prd/09-roadmap.md](prd/09-roadmap.md) | Milestone roadmap (v0.1.0 → v0.4.0) |

## Other Design Documents

- `design-spec.md` — Technical design spec (to be written)
- `design-decisions.md` — v0.1.0 decision records (to be written)
- `demo-scenario.md` — Demo scenario walkthrough (to be written)

---

## Connected

- **Vault:** [[projects/High/146-PlannerCritic.md]] · [[projects/Agentic-AI-Ideas/01-Multi-Agent-Reasoning.md]] · [[_6-MONTH-PLAN.md]]
- **Siblings:** EvalForge (measures planning quality) · ToolTrust (gates tool calls) · LessonExtractor (consumes missed-critique feedback) · AgentLab (execution backend)
- **Grounded in:** "From Plan to Action" (arXiv 2604.12147 — a bad plan hurts more than none) · self-correction blind spot (arXiv 2507.02778 — 64.5%) · Copilot CLI Rubber Duck (74.7% gap closed) · OWASP 2026 Top 10 ASI08 · Stanford 2026 AI Index (~1-in-3 agent failures) · APB (one refinement round: 22% → 60%)