<div align="center">

# PlannerCritic Engine

[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![PyPI](https://img.shields.io/badge/pypi-v0.1.0-blue)](https://pypi.org/project/planner-critic/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000)](https://github.com/astral-sh/ruff)
[![Type checked](https://img.shields.io/badge/mypy-strict-blue)](https://github.com/python/mypy)
[![Coverage](https://img.shields.io/badge/coverage-87%25-brightgreen)](https://github.com/deghosal-2026/planner-critic-engine/actions)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)
[![OpenSSF](https://img.shields.io/badge/OpenSSF-Passing-brightgreen)](SECURITY.md)
[![Field Test](https://img.shields.io/badge/field%20test-157%20goals%2C%200%20failures-brightgreen)](docs/field-test/field-test-results-0.1.0.md)

**Hierarchical task planning with an independent LLM critic. A planner decomposes a goal into a structured plan; a critic audits every subtask; the plan is revised until approval — or escalated to a human.**

</div>

> [!NOTE]
> **Status:** v0.1.0 released · [PyPI](https://pypi.org/project/planner-critic/) · `pip install planner-critic`
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

### Key Features

| Feature | Description |
|---------|-------------|
| **Risk tolerance** | `balanced` (findings are advisory warnings) or `strict` (zero tolerance, fail-closed) |
| **Deterministic gates** | 7 injection-immune gates — ordering, branch-sanity, rollback, verification, preconditions, branch-tasks, high-risk completeness |
| **Escalation management** | Human-in-the-loop with override, patch, and restart decisions |
| **Convergence detection** | Early termination when the planner stops making progress — saves LLM calls |
| **Provider registry** | Pluggable LLM providers (OpenRouter, OpenAI, oMLX, Ollama) via TOML config |
| **StructuredEnforcer** | Retry mechanism for LLM JSON output — fail-closed after 3 retries |
| **Plan versioning** | Every revision is a persisted artifact with diff support |

### What It Is Not

- It does **not** execute the plan — an existing runner consumes the approved plan.
- It does **not** guarantee plan correctness — it reduces risk, it cannot eliminate it.
- It does **not** replace execution engines or agent frameworks (LangGraph, CrewAI, etc.).

---

## Quick Start

### Install

```bash
pip install planner-critic
```

Requires Python 3.11+.

### Configure an LLM provider

Create a config file (or set an env var for the API key):

```toml
# plancritic.toml
[roles]
planner = "local"
critic = "local"

[providers.local]
transport = "openai-compatible"
base_url = "https://openrouter.ai/api/v1"      # or your provider
model = "openai/gpt-4o-mini"
api_key = "${OPENROUTER_API_KEY}"               # or set in your shell
max_tokens = 16384
timeout_s = 300.0
```

### Run your first plan

```bash
plancritic plan path/to/goal.json --config plancritic.toml
plancritic demo       # run the bundled demo scenario
plancritic quickstart # create and run a sample goal
```

Requires an LLM provider (OpenRouter, OpenAI, or a local model). See the [User Guide](docs/reference/quickstart.md) for a full walkthrough.

---

## CLI

```bash
plancritic plan <goal.json>              # Plan a goal
plancritic critique <plan.json>          # Critique a plan
plancritic field-test run --goals <dir>   # Run field test
plancritic demo                          # Run demo scenario
plancritic quickstart                    # Quickstart demo
plancritic migrate <old> <new>           # Migrate config
plancritic serve                         # Start HTTP server
```

See [API Reference](docs/reference/api.md) for full CLI docs, HTTP endpoints, and MCP tools.

---

## Field Test

157 goals across 35 domains, all run against a real LLM (gpt-4o-mini via OpenRouter):

| Metric | Result |
|--------|--------|
| Balanced goals approved | **71/71 (100%)** |
| Strict goals escalated | **81/81 (100%)** |
| Adversarial goals escalated | **8/8 (100%)** |
| True failures | **0** |
| Deterministic gate passes | **156/157 (99%)** |
| **Scorecard A (post-amendment)** | **PASS** |
| **Scorecard B (pass\* semantics)** | **100%** |

Full results: [field-test-results-0.1.0.md](docs/field-test/field-test-results-0.1.0.md)

---

## Documentation

| Doc | Path | Contents |
|-----|------|----------|
| **Field Test Results v0.1.0** | [results](docs/field-test/field-test-results-0.1.0.md) | BLUF, conclusions, per-goal data, scorecards, blocker analysis |
| **Field Test Plan** | [plan](docs/field-test/field-test-plan.md) | 156-goal corpus, 35 capabilities, invariant assertions |
| **Architecture v0.1.0** | [architecture](docs/architecture/architecture-v0.1.0.md) | Component diagram, module map, data flow |
| **API Reference** | [api](docs/reference/api.md) | CLI cheat-sheet, HTTP endpoints, MCP tools |
| **Design Decisions** | [decisions](docs/design/design-decisions.md) | DD-01..N decision records |
| **Demo Scenario** | [demo](docs/design/demo-scenario.md) | End-to-end walkthrough |
| **WBS Index** | [wbs](docs/wbs/v0.1.0/wbs-v0.1.0-index.md) | Milestone overview, dependency graph |

---

## Project Layout

```
planner-critic-engine/
├── docs/                    Documentation
│   ├── architecture/          System architecture and spec
│   ├── design/                PRD, design spec, design decisions
│   ├── field-test/            Field test plan + results (157 goals, 35 domains)
│   ├── reference/             API reference, quickstart
│   └── wbs/                   Work breakdown structure (M1–M10)
├── src/planner_critic/       Engine source
│   ├── cli/                    CLI commands
│   ├── critique/               LLM critic with severity guardrail
│   ├── gates/                  7 deterministic gates
│   ├── llm/                    Provider registry, transport, logging
│   ├── loop/                   Plan revision loop, convergence detection
│   └── server/                 HTTP server
├── tests/                    Test suite
├── .github/                  Issue templates, PR template, CI workflows
├── CHANGELOG.md               Release history
├── CONTRIBUTING.md            How to contribute
├── SECURITY.md                Security policy + OWASP + OpenSSF
└── pyproject.toml             Package metadata
```

---

## Known Gaps (v0.2.0)

- **Planner capability gap** — 132 concrete blockers across 63 strict goals. A deterministic precondition closer would eliminate 48%.
- CLI, HTTP, adapter surfaces — partial coverage
- Multi-model sweeps — only gpt-4o-mini tested
- Finding quality audit — not yet measured
- Executor usability — not yet audited

See [CHANGELOG.md](CHANGELOG.md) for full details.

---

## License

MIT — see [LICENSE](LICENSE).