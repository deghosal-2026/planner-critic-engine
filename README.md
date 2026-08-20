<div align="center">

# PlannerCritic Engine

[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000)](https://github.com/astral-sh/ruff)
[![Type checked](https://img.shields.io/badge/mypy-strict-blue)](https://github.com/python/mypy)

**Hierarchical task planning with an LLM critic. A planner decomposes a goal into a typed plan; a critic audits every subtask before execution; the plan is revised until approval — or escalated to a human.**

</div>

> [!NOTE]
> **Status:** Design phase (pre-release). Private repo; will be made public under OSS.
> **License:** MIT

---

## Why

Planning is the weakest part of agent systems. Most agents act too early, skip hard subproblems, and start executing a plan that was never reviewed. A single-pass decomposition embeds silent assumptions, and the first sign of trouble arrives mid-execution — after state has already diverged.

Single-pass planning fails silently on multi-step goals, and a model "reviewing" its own plan is agreement with extra steps. There is no draft to review, no independent reviewer to catch the gap, and no structured escalation.

PlannerCritic Engine closes this gap by treating planning as a first-class, productized artifact rather than a hidden chain-of-thought side effect.

---

## What It Is

### The Draft → Critique → Revise → Escalate Loop

```
 Goal + Constraints → PLANNER → typed plan → CRITIC → findings
                        ↑  │                        │
                        │  └────── revise ←──────────┘
                        │                             │
                        └──────── approved plan ──────┘
                                     │
                                  ESCALATE (if no convergence)
```

- **Draft** — a planner LLM decomposes a goal into a structured, typed plan: tasks, dependencies, ordering, verification steps, and rollback points.
- **Critique** — a separate critic LLM audits every subtask against six heuristic families: feasibility, risk, missing steps, unsafe sequencing, unverified dependencies, weak rollback — producing severity-graded findings.
- **Revise** — the planner revises in response, in a bounded loop with a revision budget and convergence detection, preserving draft history.
- **Escalate** — if the loop cannot converge, a human gets a minimal, precise question about exactly what is blocking approval.

The plan is a persisted, versioned artifact — you can diff revisions, see which critiques drove which changes, and trace whether a failed run was a planning failure or an execution failure.

---

## What It Is Not

- It does **not** execute the plan — an existing runner consumes the approved plan.
- It does **not** guarantee plan correctness — it reduces risk, it cannot eliminate it.
- It does **not** replace execution engines or agent frameworks (LangGraph, CrewAI, etc.).

---

## Scope (MVP 0.1.0)

- Typed goal schema with constraints and risk tolerance
- Structured plan representation (tasks, deps, ordering, verification, rollback)
- Separate planner and critic LLM calls with distinct prompts and model selection
- Six critique heuristic families with severity-graded findings
- Bounded revise-until-approved loop with revision budget
- Human escalation with minimal questions
- Plan versioning and diff

**Nice-to-have:** web UI for plan review and revision diffs, execution-engine adapter (AgentLab).

---

## Layout

```
planner_critic_engine/
docs/             Documentation
docs/architecture/   System architecture and spec
docs/design/         PRD, design spec, design decisions
docs/field-test/     Field test plan + results
  field-test-plan.md          Field test plan (65 goals, 10 domains, 30 capabilities)
  field-test-results-0.1.0.md Field test results v0.1.0 (BLUF, conclusions, data)
  goals/                      65 real-world goal scenarios across 10 domains
  reports/0.1.0/full-sweep/   Full sweep traces, LLM logs, per-goal evidence
docs/wbs/             Work breakdown structure (M1–M10)
docs/reference/       API reference, quickstart
tests/            Test suite
examples/         Sample goal: draft → critique → revise trace
```

---

## Documentation

| Doc | Path | Contents |
|-----|------|----------|
| **Field Test Plan** | `docs/field-test/field-test-plan.md` | 65-goal corpus, 30 capabilities, invariant assertions, execution design |
| **Field Test Results v0.1.0** | `docs/field-test/field-test-results-0.1.0.md` | BLUF, conclusions, observations, surprises, learnings, per-goal data, evidence |
| **Docker Integration** | `docs/field-test/docker-integration.md` | Containerized engine + CLI/HTTP/MCP vs local LLM |
| **Architecture v0.1.0** | `docs/architecture/architecture-v0.1.0.md` | Component diagram, module map, data flow |
| **WBS Index** | `docs/wbs/v0.1.0/wbs-v0.1.0-index.md` | Milestone overview, dependency graph, issue ranges |
| **Design Decisions** | `docs/design/design-decisions.md` | DD-01..N decision records |
| **API Reference** | `docs/reference/api.md` | CLI cheat-sheet, HTTP endpoints, MCP tools |

---

## Planned Articles

- "Why Your Agent Needs a Code Review for Its Plans"
- "The Draft-Critique-Revise Loop: How Humans Plan, Productized for LLMs"
- "Escalation Is a Feature: Teaching Agents When to Ask a Human"

---

## License

MIT — see [LICENSE](LICENSE).