# 05 — Feature Set

> Sub-document of the [Design overview](../README.md). The full feature inventory.
>
> Priority scale: **P0** (v0.1.0): must have; **P1** (v0.2.0); **P2** (v0.3.0+); **P3** backlog.
>
> **v0.1.0 is feature-rich by design** — the first release ships the core engine, both critique modes, all six adapters *with* execution-time re-gate, planning-vs-execution forensics, plan-graph viz, trace replay, diff-aware critique, reason codes, and the security baseline. The web UI, Postgres store, and non-OpenAI transports are the v0.2 deltas.

## 5.1 Core engine (model- and framework-agnostic)
| ID | Feature | Priority | Notes |
|---|---|---|---|
| F-01 | Goal schema (constraints + `risk_tolerance` + `budget`) | P0 | Typed JSON schema |
| F-02 | Plan schema: tasks, deps, ordering, verification, rollback | P0 | Typed, validated; the artifact everything audits |
| F-03 | Planner role (LLM) — decompose goal → typed plan | P0 | Via provider layer |
| F-04 | Critic role (LLM) — six heuristic families, severity-graded findings | P0 | feasibility, risk, missing steps, unsafe sequencing, unverified deps, weak rollback |
| F-05 | Loop controller — revise-until-approved, revision cap (default 3) | P0 | Cap configurable |
| F-06 | Convergence detection — same blockers circling / near-zero diff → early escalate | P0 | |
| F-07 | Regression guard — new blocker introduced by a revision → escalate | P0 | |
| F-08 | Approval threshold from `risk_tolerance` (strict/balanced) | P0 | balanced = warnings acknowledged |
| F-09 | Pluggable plan store (SQLite default, Postgres-ready interface) | P0 | versioned plans, diffs, critique history |
| F-10 | `deterministic-first` critique mode (default) | P0 | free gates before LLM critic |
| F-11 | `llm-every-revision` critique mode (option, config `critic.mode`) | P0 | full six-heuristic critique per revision |
| F-12 | Deterministic critique gates: schema validity, dependency cycles, ordering sanity, verification presence, rollback presence | P0 | zero-LLM-cost |
| F-13 | Per-goal spend budget (max tokens / calls / revisions) enforced by the loop controller → escalate on budget hit | P0 | cost safety on paid providers |
| F-74 | Determinism contract for the loop controller (same inputs → same loop decisions) | P0 | CI-assertable |

## 5.2 LLM provider layer
| ID | Feature | Priority | Notes |
|---|---|---|---|
| F-20 | `LLMProvider` protocol (name, base_url, model, transport, api_key) | P0 | Registry-first: built before any concrete transport |
| F-21 | Config-driven provider registry (`plancritic providers add/list/rm`) | P0 | persists config |
| F-22 | OpenAI-compatible transport (first implementation of the protocol) | P0 | OMLX/Ollama/vLLM/OpenRouter/OpenAI |
| F-23 | Separate provider/model for planner vs critic | P0 | recommended different family for the critic |
| F-24 | Structured-output enforcement (plans and findings parse into typed schemas) | P0 | retries on schema-mismatch |
| F-25 | Anthropic + Google (Gemini) transports | P1 | same protocol, new registration |

## 5.3 Escalation
| ID | Feature | Priority | Notes |
|---|---|---|---|
| F-30 | Escalation manager — minimal precise question, blocker focus | P0 | |
| F-31 | Escalation CLI (`escalate list/approve/deny`, patching) | P0 | v0.1 |
| F-32 | Escalation MCP tools (list/approve/deny) | P0 | v0.1 |
| F-33 | AIDE-style web UI: goal + plan + blocker + critique trail + revision history + inline editing | P1 | v0.2 React viewer on the store |
| F-34 | Resolution recorded in plan history; patched plans re-submitted to critic | P0 | |

## 5.4 Framework adapters (the tooltrust six)
| ID | Feature | Priority | Notes |
|---|---|---|---|
| F-40 | Raw Python adapter | P0 | library objects, no framework dep |
| F-41 | LangGraph adapter | P0 | pre-execution node / callback + per-step re-gate |
| F-42 | PydanticAI adapter | P0 | guard + per-step re-check |
| F-43 | CrewAI adapter | P0 | task interceptor + per-step re-check |
| F-44 | OpenAI Agents SDK adapter | P0 | runner hook / guardrail + per-step re-check |
| F-45 | MCP server (planner/critic/escalation tools) | P0 | any MCP agent |
| F-46 | Execution-time re-gate (`before-each-step | off`) | P0 | precondition drift → replan |

## 5.5 Execution feedback (planning vs execution)
| ID | Feature | Priority | Notes |
|---|---|---|---|
| F-50 | Plan–execution link + `planning`/`execution` failure tagging | P0 | record + classification |
| F-51 | Missed-critique record ("critic said fine; execution disagrees") + critique history snapshot | P0 | data model at v0.1 |
| F-52 | Suggested deterministic check surfaced to operator | P0 | feeds LessonExtractor v0.2+ |

## 5.6 Delivery surfaces & tooling
| ID | Feature | Priority | Notes |
|---|---|---|---|
| F-60 | PyPI package `planner-critic` (import `planner_critic`) | P0 | |
| F-61 | CLI `plancritic`: providers, plan, critique, approve/deny, plans/diff, replay, field-test, baseline | P0-P1 | |
| F-62 | FastAPI HTTP service (plan submit, escalate, query, approve) | P0 | for non-Python hosts |
| F-63 | SQLite plan store (shipped default) | P0 | |
| F-64 | Postgres store (behind the same interface) | P1 | |
| F-65 | Domain-agnostic sample goal corpus (migration, rollout, refactor, incident-response) | P0 | examples/ |
| F-66 | Demo trace with a seeded flaw → caught → revised → approved/escalated | P0 | the "aha" narrative |
| F-67 | Hermetic CI field-test gate (fake providers) | P0 | never calls a paid LLM |
| F-68 | Local-model release field sweep (`plancritic field-test`, OMLX/Ollama) | P0 | release gate |

## 5.7 Observability, viz & extensibility
| ID | Feature | Priority | Notes |
|---|---|---|---|
| F-75 | Plan graph export — render the task DAG as Mermaid + JSON (`plancritic plan show <id> --graph`) | P0 | demos/articles/debugging |
| F-76 | `plancritic replay <plan_id>` — replay the draft→critique→revise→approve/escalate trace; `--step`, `--format json` | P0 | demo/article workhorse |
| F-77 | Reason-code catalog — stable machine-readable `reason_code` per finding & loop decision; for SIEM/observability + agent replan | P0 | mirrors tooltrust reason codes |
| F-78 | Diff-aware critique — on revision N>1, re-audit only changed tasks + dependents | P0 | cost optimization aligned with budget |
| F-79 | Critique heuristic packs — config-defined heuristic families; community can add families via a pack schema + validator (`plancritic heuristics add`) | P1 | extensibility story |

## 5.8 Reliability & degraded modes
| ID | Feature | Priority | Notes |
|---|---|---|---|
| F-70 | Provider failure (timeout/error) → deterministic `planning_unavailable` failure mode per role | P0 | fail-closed: no plan execution on unverified plan |
| F-71 | Structured-output schema-mismatch retry with bounded retries, then failure | P0 | |
| F-72 | Store failure → clear error; plan store is a side channel, plan/critique continues in-memory with warning | P1 | |
| F-73 | Fail-closed default: unapproved plan cannot be handed to an executor | P0 | |

## 5.9 Interface surfaces (reference)

**CLI (`plancritic`)**
| Command | Purpose | P |
|---|---|---|
| `providers add/list/rm` | manage the LLM provider registry | P0 |
| `plan "<goal>" --constraints ...` | decompose a goal → typed plan | P0 |
| `critique <plan>` | run the critic on a plan version | P0 |
| `escalate list` / `approve <id>` / `deny <id>` [--patch ...] | escalation round-trip | P0 |
| `plans list` / `show <id>` / `diff <v1> <v2>` / `show <id> --graph` | versioned plan store + graph | P0 |
| `replay <plan_id>` | replay a plan trace | P0 |
| `heuristics add/validate/test` | critique-heuristic packs | P1 |
| `field-test` | release field sweep | P0 |
| `baseline check` | security baseline self-audit | P1 |

**HTTP (FastAPI)**
| Method | Path | Purpose | P |
|---|---|---|---|
| POST | `/plan` | submit a goal → plan | P0 |
| POST | `/critique` | critique a plan version | P0 |
| GET | `/escalations` | list pending escalations | P0 |
| POST | `/escalations/{id}/approve` · `/deny` | resolve an escalation (with optional patch) | P0 |
| GET | `/plans` · `/plans/{id}` · `/plans/{id}/diff?v2=` · `/plans/{id}/graph` | store queries, diffs, graph | P0 |

**MCP server tools**
| Tool | Purpose | P |
|---|---|---|
| `plan` | decompose a goal into a typed plan | P0 |
| `critique` | critique a plan version | P0 |
| `escalate_list` / `escalate_approve` / `escalate_deny` | resolution from the agent's own workspace | P0 |