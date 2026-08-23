<div align="center">

# PlannerCritic Engine

[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![PyPI](https://img.shields.io/badge/pypi-v0.2.1-blue)](https://pypi.org/project/planner-critic/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000)](https://github.com/astral-sh/ruff)
[![Type checked](https://img.shields.io/badge/mypy-strict-blue)](https://github.com/python/mypy)
[![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen)](https://github.com/deghosal-2026/planner-critic-engine/actions)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/14184/badge)](https://www.bestpractices.dev/projects/14184)
[![Field Test](https://img.shields.io/badge/field%20test-170%20goals%2C%200%20failures-brightgreen)](docs/field-test/v0.2.1/field-test-results-0.2.1.md)

**Hierarchical task planning with an independent LLM critic. A planner decomposes a goal into a structured plan; a critic audits every subtask; the plan is revised until approval — or escalated to a human.**

</div>

> [!NOTE]
> **Status:** v0.2.1 released · [PyPI](https://pypi.org/project/planner-critic/) · `pip install planner-critic`
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

| Feature | Description | Added |
|---------|-------------|-------|
| **Risk tolerance** | `balanced` (findings are advisory warnings) or `strict` (zero tolerance, fail-closed) | v0.1.0 |
| **Deterministic gates** | 7 injection-immune gates — ordering, branch-sanity, rollback, verification, preconditions, branch-tasks, high-risk completeness | v0.1.0 |
| **Escalation management** | Human-in-the-loop with override, patch, and restart decisions | v0.1.0 |
| **Convergence detection** | Early termination when the planner stops making progress — saves LLM calls | v0.1.0 |
| **Provider registry** | Pluggable LLM providers (OpenRouter, OpenAI, oMLX, Ollama) via TOML config | v0.1.0 |
| **StructuredEnforcer** | Retry mechanism for LLM JSON output — fail-closed after 3 retries | v0.1.0 |
| **Plan versioning** | Every revision is a persisted artifact with diff support | v0.1.0 |
| **Deterministic auto-repair** | Topological re-ordering + precondition closure — fixes ordering/dependency defects without LLM cost (#130, #131) | v0.2.0 |
| **Oscillation detection** | Detects structural cycling and auto-converges (#152) | v0.2.0 |
| **Domain Pack framework** | Domain-specific gate packs (SecOps, Supply Chain, FinOps, Data Eng) with `plancritic init --template` (#139, #140–143) | v0.2.0 |
| **Policy-as-Code engine** | OPA/Rego + CEL policy evaluation — deterministic gates for custom compliance (#129, #156) | v0.2.0 |
| **Security oracle** | SWE-bench-derived security corpus validates gates against human ground truth (#123–127) | v0.2.0 |
| **Enterprise safety** | Dynamic posture, run budgets, state locking, precondition ledger, blast-radius quotas, secret/PII redaction (#149–151, #158, #159) | v0.2.0 |
| **Developer surfaces** | `plancritic check`, `diagnose`, `domains`, `policy`, `templates` CLI + `@guardrail` decorator + seed Rego library (#137, #153, #162) | v0.2.0 |
| **CI/CD integrations** | GitHub Action, GitLab CI template, AutoGen adapter, webhook notifier (#128, #134, #161) | v0.2.0 |
| **Probe system** | Health probes for pre-execution precondition validation (DB, deploy, env, HTTP) | v0.2.0 |
| **Drift observability** | Finding-drift detection — track how findings change across revisions (#181) | v0.2.0 |
| **pytest plugin** | `pytest-planner-critic` — use gate assertions in your test suite (#156) | v0.2.0 |

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
plancritic plan <goal.json>                # Plan a goal
plancritic critique <plan.json>            # Critique a plan
plancritic check --plan <plan.json>        # Quality check a plan
plancritic diagnose <plan-id>              # Diagnose plan issues
plancritic domains list                    # List available domain packs
plancritic policy check <plan.json>        # Evaluate Rego/CEL policies
plancritic templates list                  # List scaffold templates
plancritic field-test run --goals <dir>    # Run field test
plancritic eval --regression               # Security oracle regression
plancritic findings list                   # List plan findings
plancritic lessons                         # List learned lesson codes
plancritic plan replay <plan-id>           # Replay plan history
plancritic escalate list                   # List escalations
plancritic demo                            # Run demo scenario
plancritic quickstart                      # Quickstart demo
plancritic init [--dir]                    # Scaffold config + store
plancritic providers add/list/rm           # Manage LLM providers
plancritic migrate <old> <new>             # Migrate schema
plancritic serve                           # Start HTTP server
plancritic quota show                      # Show blast-radius quotas
```

See [API Reference](docs/reference/api.md) for full CLI docs, HTTP endpoints, and MCP tools.

---

## Field Test

170 goals across 40 domains, all run against a real LLM (gpt-4o-mini via OpenRouter):

| Metric | Result |
|--------|--------|
| Balanced goals approved | **73/73 (100%)** |
| Strict goals escalated | **97/97 (100%)** |
| Adversarial goals escalated | **8/8 (100%)** |
| True failures | **0** |
| Deterministic gate passes | **170/170 (100%)** |
| Security oracle (SWE-bench) | **7/7 correct, 35/35 flawed blocked, 21 traps** |
| **Scorecard A (pre-amended)** | **PASS** |
| **Scorecard B (pass\* semantics)** | **100%** |

Full results: [field-test-results-0.2.0.md](docs/field-test/v0.2.0/field-test-results-0.2.0.md)

---

## Documentation

| Doc | Path | Contents |
|-----|------|----------|
| **Field Test Results v0.2.0** | [results](docs/field-test/v0.2.0/field-test-results-0.2.0.md) | BLUF, conclusions, per-goal data, scorecards, blocker analysis |
| **Field Test Results v0.1.0** | [results](docs/field-test/v0.1.0/field-test-results-0.1.0.md) | v0.1.0 results for reference |
| **Field Test Plan** | [plan](docs/field-test/README.md) | Corpus, invariant assertions, execution guide |
| **Release Notes v0.2.0** | [release-notes](docs/reference/release-notes-v0.2.0.md) | What's new, breaking changes, upgrade path |
| **Release Notes v0.1.0** | [release-notes](docs/reference/release-notes-v0.1.0.md) | v0.1.0 release notes for reference |
| **Architecture** | [architecture](docs/architecture/architecture-v0.1.0.md) | Component diagram, module map, data flow |
| **API Reference** | [api](docs/reference/api.md) | CLI cheat-sheet, HTTP endpoints, MCP tools |
| **Design Decisions** | [decisions](docs/design/design-decisions.md) | DD-01..N decision records |
| **Domain Pack Design** | [domain-packs](docs/design/domain-pack-design.md) | Domain pack protocol, pack format, engine integration |
| **Policy Engine Design** | [policy-engine](docs/design/policy-engine-design.md) | OPA/Rego/CEL integration |
| **Enterprise Safety Design** | [enterprise-safety](docs/design/enterprise-safety-design.md) | Posture, budgets, state, ledger, quotas, redaction |
| **Developer Surfaces Design** | [developer-surfaces](docs/design/developer-surfaces-design.md) | CLI commands, decorator, seed Rego |
| **Integration Surfaces Design** | [integration](docs/design/integration-surfaces-design.md) | CI runners, AutoGen, notifier |
| **Security** | [security](SECURITY.md) | Security policy, OWASP, OpenSSF |
| **WBS Index (v0.2.0)** | [wbs](docs/wbs/v0.2.0/wbs-v0.2.0-index.md) | Milestone overview, dependency graph |

---

## Project Layout

```
planner-critic-engine/
├── docs/                    Documentation
│   ├── architecture/          System architecture and spec
│   ├── design/                PRD, design spec, design decisions
│   ├── field-test/            Field test plan + results (170 goals, 40 domains)
│   ├── reference/             API reference, quickstart, release notes
│   └── wbs/                   Work breakdown structure (M1–M10)
├── src/planner_critic/       Engine source
│   ├── adapters/               AutoGen, CrewAI, LangGraph, OpenAI Agents, PydanticAI adapters
│   ├── cli/                    21 CLI commands
│   ├── critique/               LLM critic with severity guardrail
│   ├── domains/                Domain-specific gate packs (SecOps, Supply Chain, FinOps, Data Eng)
│   ├── eval/                   Security oracle, injection harness, regression, label migration
│   ├── gates/                  7 deterministic gates
│   ├── llm/                    Provider registry, transport, logging
│   ├── loop/                   Plan revision loop, auto-repair, convergence, oscillation
│   ├── probe/                  Health probes (DB, deploy, env, HTTP)
│   ├── schema/                 Goal and plan schemas
│   ├── server/                 HTTP + MCP servers
│   └── store/                  SQLite plan store with versioning
├── tests/                    Test suite (field test + 90 deterministic tests)
├── .github/                  Issue templates, PR template, CI workflows
├── CHANGELOG.md               Release history
├── CONTRIBUTING.md            How to contribute
├── SECURITY.md                Security policy + OWASP + OpenSSF
└── pyproject.toml             Package metadata
```

---

## Known Gaps (v0.3.0)

The authoritative register of known failure modes and load-bearing assumptions — each classified as an intentional trade-off or a claim still needing evidence — lives in [docs/reference/failure-modes.md](docs/reference/failure-modes.md). Summary:

- **Planner capability gap** — strict mode = escalation for non-trivial plans (intentional posture; see register F-01).
- **Local model support for planner** — Qwen3-4B JSON valid; critic role still too weak (F-09).
- **TUI / studio / IDE surfaces** — deferred to v0.3.0 (F-11).
- **Backstage developer portal plugin** — deferred to v0.3.0 (F-12).
- **Adaptive revision cap** — detect strict goals and reduce cap to 1, saving LLM calls (F-10).

See [CHANGELOG.md](CHANGELOG.md) for full details.

---

## License

MIT — see [LICENSE](LICENSE).