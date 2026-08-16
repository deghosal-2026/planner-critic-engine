# PlannerCritic Engine — Product Requirements Document (PRD)

**Version:** 0.1 (Draft)
**Date:** 2026-08-16
**Status:** Draft (for review)
**Owner:** Debashish Ghosal
**Repo:** `deghosal-2026/planner-critic-engine` (private → OSS)
**Package:** `planner-critic` / import `planner_critic` / CLI `plancritic`

---

## 1. Executive Summary

PlannerCritic Engine is a **hierarchical planning system with an independent LLM critic**. A *planner* LLM decomposes a goal into a typed plan — tasks, dependencies, ordering, verification steps, and rollback points. A separate *critic* LLM audits every subtask before execution across six heuristic families — feasibility, risk, missing steps, unsafe sequencing, unverified dependencies, weak rollback — producing severity-graded findings. The planner revises in a **bounded revise-until-approved loop** until the critic approves or the system **escalates to a human** with a minimal, precise question.

The insight that justifies the project: **planning is the weakest part of agent systems, and single-pass planning is blind.** Agents act too early, skip hard subproblems, and execute plans nobody reviewed. A model "reviewing" its own plan is agreement with extra steps. PlannerCritic separates the draft role from the critique role so a plan survives an independent adversarial pass — the way a code review works — before anything executes.

The plan is a **first-class, versioned, inspectable artifact** — you can diff revisions, see which critiques drove which changes, and trace whether a failed run was a planning failure or an execution failure.

**Core architectural principle (decided 2026-08-16):** PlannerCritic Engine is **fully LLM- and framework-agnostic**. The core engine owns the mechanics (plan schema, critique heuristics, loop controller, convergence detection, escalation manager, plan store) and speaks plain typed JSON. Two pluggable surfaces hang off it: an **LLM provider layer** (config-driven registry; any model/transport plugs in via a thin protocol — the OpenAI-compatible transport is the first implementation, built *on top of* the registry) and **framework adapters** (raw Python, LangGraph, PydanticAI, CrewAI, OpenAI Agents SDK, MCP — the same six-agent-adapters pattern that shipped in agent-tooltrust). The engine never knows which model or framework called it.

**Scoping snapshot (decided 2026-08-16):** Python library + CLI + MCP server + HTTP service (full blast); pluggable plan-store interface with SQLite default and Postgres-ready; dual-mode critique (`deterministic-first` default → `llm-every-revision` option); per-goal approval thresholds via goal `risk_tolerance`; loop = revision cap + convergence detection + regression guard; escalation = all three surfaces (CLI + MCP tools in v0.1, React web UI in v0.2); execution-trace tagging with planning-vs-execution classification and missed-critique → suggested-check feedback; domain-agnostic sample goal corpus; hermetic CI gate (no paid LLM) + local-model (OMLX/Ollama) field-test release gate.

---

## 2. Why (Business Requirements)

### 2.1 The market context

- The agent ecosystem has spent enormous energy on **execution** — tools, memory, orchestration, retrieval — and almost none on **planning quality**. Agents are judged by whether they can *do* a task; the failures that matter happen before a single tool call: the agent decided to act on a plan that was incomplete, wrongly ordered, or built on an unverified assumption.
- Stanford's 2026 AI Index: agents **fail ~1 in 3 attempts** on structured benchmarks (OSWorld rose to 66.3%, still within ~6 points of humans). Industry analyses attribute the largest share of agent failure to **planning failures** — the most expensive and hardest-to-detect class, because there is no error signal: the plan *looked* fine at step zero and collapsed at step three.
- **Single-pass plans are silent time bombs.** A goal like "migrate this service to the new auth provider" decomposes in one hidden chain-of-thought pass; three steps in, the agent discovers the DB schema was never checked, or an outage window was never coordinated. There is no draft to review, no reviewer to catch the gap, no structured escalation — just a failed run and a partial state change to clean up.
- **Self-review is agreement with extra steps.** The self-correction blind spot is real: across 14 LLMs, same-model review fails to correct errors in the model's own output at an average **64.5% rate** — the critic must be a *different* role and, ideally, a different model family.
- **A cross-model critic measurably pays for itself.** GitHub Copilot CLI's "Rubber Duck" critic (a second GPT-model reviewing plans pre-execution) closed **74.7% of the gap** to Opus-alone, and shipped to GA in June 2026. The pattern works; nobody has productized it as a standalone OSS engine.
- **Regulators and security guidance now demand plan review.** OWASP's 2026 Top 10 for Agentic Applications (ASI08, Cascading Failures) explicitly recommends: *"Separate planning from execution — an independent governance agent reviews and signs off on plans before execution begins."* The EU AI Act makes human oversight a legal obligation for high-stakes decisions. Escalation-to-human is a compliance feature, not a design weakness.

### 2.2 The pain we remove

| Status quo (today) | Pain |
|---|---|
| Single-pass chain-of-thought decomposition | Hidden, single-pass, uninspectable plan; hard subproblems silently skipped; failure discovered mid-execution after state diverged |
| Same-model "self-review" | 64.5% blind-spot rate — the producer's failure modes are inherited; rubber-stamp with extra steps |
| Framework plan-and-execute examples (LangGraph, AutoGen) | Plan is a transient message, not a typed/versioned/inspectable artifact; no approval gate; unbounded loops |
| Human-only plan mode (Claude Code, Codex) | Human is the critic (expensive, all-or-nothing approve/reject); no LLM prereview, no revision loop primitives, no audit trail |
| Roll-your-own plan review inline in app code | Logic scattered, untested, no convergence semantics, no escalation manager, no plan store |

### 2.3 Why it matters for the pilot & OSS goals

- **For agent builders:** a pre-execution quality gate that catches structural plan failures — missing steps, unsafe ordering, unverified dependencies — before state is mutated, across *any* model and *any* framework they already use.
- **For operators of high-stakes agents:** escalate the genuinely ambiguous decisions to a human with a precise question; keep a versioned, diffable plan + critique history for diagnosis and compliance ("was this a planning failure or an execution failure?" is answerable).
- **For the solo-build OSS portfolio:** a Tier-1, high-engagement problem (planning is ranked the #1 agentic hard problem in the Agentic AI Ideas catalog) with a sharp article series ("Why Your Agent Needs a Code Review for Its Plans"), and strong family compatibility with the shipped stack (EvalForge measures planning quality, ToolTrust gates tool calls, LessonExtractor consumes missed-critique feedback).

---

## 3. What We Are Building (Core Value)

**A pre-execution planning-quality engine for any LLM and any agent framework that:**

1. **Decomposes** a goal into a structured, typed plan — tasks, dependencies, ordering, verification steps, rollback points — via a planner LLM role.
2. **Audits** the plan via an *independent* critic role across six heuristic families, returning severity-graded findings (`blocker` / `warning` / `info`).
3. **Revises** in a bounded loop with a revision budget, convergence detection, and a regression guard (a revision that *introduces* a new blocker escalates).
4. **Escalates** to a human with a minimal, precise question when the loop cannot converge — showing the goal, the current plan, the blocker, the critique trail, and the revision history, with direct plan patching before approval.
5. **Stores** every plan version with diffs and critique history in a pluggable store (SQLite default, Postgres-ready).

**The core engine is model- and framework-agnostic.** It speaks plain typed JSON. Two pluggable surfaces reveal its power:

### 3.1 LLM provider layer (built registry-first)

- **`LLMProvider` protocol** — a thin interface (`complete(messages, tool_schemas)` → structured output) that any model/transport implements: `name`, `base_url`, `model`, `transport` type, optional `api_key`.
- **Config-driven registry** — providers are defined in config, not code: `plancritic providers add <name> --transport openai-compatible --base-url ... --model ...`. The engine loads whatever is configured. This is built *first*; the OpenAI-compatible transport is the first concrete implementation *on top of* it.
- **Cost control** — the default config points at local/cheap endpoints (OMLX, Ollama, vLLM). Paid providers are only used when explicitly registered. The planner and critic can use *different* providers/models (a different family for the critic is recommended, per the blind-spot research).
- CI never calls a paid LLM: the hermetic gate is deterministic-only.

### 3.2 Critique engine (dual-mode)

| Mode | Default | Behavior | Cost |
|------|---------|----------|------|
| **`deterministic-first`** | ✅ | Free deterministic gates (schema validity, dependency cycles, ordering sanity, verification-step presence, rollback presence) run first; the LLM critic only fires on drafts that pass the deterministic gates | Low — LLM calls only for survivable drafts |
| **`llm-every-revision`** | option | Full six-heuristic LLM critique on every draft | High — full audit depth per revision |

Same engine, one config knob (`critic.mode`). Users with cheap/audit-critical goals choose `llm-every-revision`; everyone else gets the low-cost default.

### 3.3 Approval & loop semantics

- **Per-goal approval threshold** (from the goal schema's `risk_tolerance` field): `strict` = zero warnings tolerated; `balanced` = warnings tolerated but must be explicitly acknowledged in the final plan. No blockers may ever remain.
- **Loop termination:** (a) critic approves (threshold met) ✓, (b) revision cap reached (default 3, configurable) → escalate, (c) **convergence detection** — revisions circling the same blockers, or plan diffs converging to near-zero between versions → escalate early, (d) **regression guard** — a revision introduces a *new* blocker → escalate (planner is thrashing).

### 3.4 Execution feedback (planning vs execution)

- An approved plan can be linked to later executions and **tagged** `planning` / `execution` on failure.
- A tagged failure that the critic *missed* is **recorded with its critique history** ("the critic said this was fine; execution proved otherwise") and **surfaces a suggested deterministic check** to the operator.
- This feeds LessonExtractor (Week 8 flagship): the missed-critique records become a standing-rule corpus. The data model captures the miss at v0.1; automated promotion is a v0.2+ concern.

### Terminal-state definition ("done" for v0.1.0)

A working `v0.1.0` you can `pip install planner-critic`, register a provider (`plancritic providers add ...`), give it a non-trivial goal, watch the critic flag a real gap in the planner's first draft, see the planner revise to approval — or escalate cleanly with a precise question when it can't — with every plan version and critique stored and diffs inspectable, and a field-test matrix green across all six frameworks against a local model.

---

## 4. Landscape & Identity (from research)

| Project | Type | What it does | Our wedge |
|---|---|---|---|
| **PlanCritic** (Burns '24) | Research | LLM covers NL specs → PDDL; RLHF reward model + GA revises plans | Research artifact (disaster-recovery PDDL domain), not a model-agnostic engine |
| **LangGraph plan-and-execute** | Framework example | Planner → Executor → Re-planner | No independent critic, no typed plan schema, no approval gate, no escalation |
| **AutoGen** | Multi-agent framework | Group-chat Planner/Writer/Editor/Reviewer | Critic is an unbounded app-level conversation pattern; no plan artifact semantics |
| **Copilot CLI "Rubber Duck"** | Product (closed, OSS client) | Second GPT model reviews plans pre-execution; closes 74.7% of the Opus gap | Closed single-surface; not a standalone engine; no bounded loop/escalation/store |
| **Claude/Codex plan mode** | Product | Read-only plan → human approve → execute | Human is the critic; no LLM prereview, no revision loop, no versioning |
| **`codex-skill`** | OSS plugin | Hook sends plan to another model for review | Single-role, no loop/budget/escalation; plugin, not engine |
| **Voyager / Reflexion / Self-Refine** | Research | Post-execution self-verification / reflection | Verify *after* acting; same-model; no pre-execution plan gate |
| **SWE-agent ("From Plan to Action")** | Research | Default plan embedded in prompt | Study proved a *bad plan hurts more than no plan*; planning is the binding constraint |

### 4.1 PlannerCritic vs the crowd

1. **Standalone, model-agnostic engine** — the draft-critique-revise loop as a reusable library, not a framework plugin or a prompt. Works with any OpenAI-compatible model and any of the six major frameworks.
2. **Plan as a first-class artifact** — typed schema, versioned, diffable, persisted, with critique history — not a transient conversation message. "The plan is a PR, and the critic is the reviewer."
3. **Bounded loop with real termination semantics** — revision budget + convergence detection + regression guard — no unbounded improve-until-happy, no rubber-stamp.
4. **Structured, low-cost critique** — deterministic gates always on, LLM critic on the drafts that survive them; severity-graded typed findings, not free-text vibes. Optionally full-depth LLM critique per revision when the audit justifies it.
5. **Escalation as a feature** — minimal, precise human questions with full revision context and direct plan patching — the EU-AI-Act / OWASP ASI08 compliance story, productized.
6. **Planning-vs-execution forensics** — tagged failure classification and missed-critique feedback — an instrumentation surface no one else ships.

---

## 5. Target Users

**Primary persona — Agent Platform Engineer / AI Engineer building multi-step agents.** Builds agents (LangGraph, PydanticAI, CrewAI, OpenAI SDK, MCP, raw Python) that handle multi-step, high-stakes goals where acting on a bad plan is expensive. Wants a planning layer in front of execution without rewiring the framework.

**Secondary personas:**
- **Agent framework adopters** — want a planning/critique layer their framework can consume as a library or MCP tool.
- **SRE / reliability engineers** — want pre-execution gates and plan-vs-execution failure classification for production agents.
- **Researchers / students** — experimenting with structured critique and self-correction loops; want a well-typed artifact to instrument.
- **OSS maintainers** — anonymous default off, safe defaults, cheap local-model path.

**Primary non-negotiable for all personas: minimal time-to-first-approved-plan** → low-friction install, a registered provider, one non-trivial goal, a visible critique→revise→approve round-trip.

---

## 6. Critical User Journeys (CUJs)

Ten critical journeys, each with a gate / decision / acceptance criteria. North star for the feature set.

### CUJ 1 — Register a provider and plan a goal ("15 lines to a plan")

As an engineer, I register my model endpoint (local or paid), submit a goal with constraints, and get a typed, structured plan I can see immediately.

**Acceptance criteria (P0):**
- `plancritic providers add <name> --transport openai-compatible --base-url ... --model ...` works; provider list persists and loads on restart.
- `plancritic plan "<goal>" --constraints ...` returns a typed plan (tasks, deps, ordering, verification, rollback) as JSON/YAML and prints a readable rendering.
- Works with a local OpenAI-compatible endpoint (OMLX/Ollama) with zero paid spend; works with any configured provider.
- The goal carries constraints + `risk_tolerance`.

### CUJ 2 — The critic catches a real flaw (the "aha" moment)

As an engineer, I run a goal through planner+critic and watch the critic flag a genuine structural gap the planner missed — a missing verification step, an unsafe ordering, an unverified dependency — with a severity grade and a precise reason.

**Acceptance criteria (P1, but the project isn't real without it):**
- Demo corpus includes ≥1 goal where the first draft is critiqued with a *correct* blocker (a seeded flaw) that the planner actually fixes in revision.
- Findings are structured (heuristic family, severity, task reference, reason) — not free text.

### CUJ 3 — Critique in the low-cost mode doesn't break (deterministic-first)

As an operator on a budget, I run the same goal in `deterministic-first` mode and confirm every plan still passes the free deterministic gates, with the LLM critic only invoked on surviving drafts.

**Acceptance criteria (P1):**
- Deterministic gates: schema validity, dependency-cycle detection, ordering sanity (a dependency that references a later task), verification-step presence, rollback presence for high-blast-radius steps — all free, no LLM call.
- `critic.mode=llm-every-revision` switches the full six-heuristic LLM critique on; the same engine, one config flag.

### CUJ 4 — The loop converges (or escalates at the right moment)

As a user, I watch the planner revise under critique until approval — or, on a genuinely ambiguous goal, escalate with a precise question instead of guessing or stalling.

**Acceptance criteria (P0):**
- Revision cap (default 3, configurable) escalates when exceeded.
- Convergence detection escalates early when revisions circle the same blockers or diffs converge to near-zero between versions.
- Regression guard escalates when a revision *introduces* a new blocker.
- Approved plans meet the per-goal threshold (strict = zero warnings; balanced = warnings acknowledged).

### CUJ 5 — Escalate to a human, human resolves, agent continues

As an operator, when the loop escalates I see the goal, the current plan, the blocker, the critique trail, and the revision history; I approve (optionally patching the plan) or deny; the loop resumes with the resolution recorded.

**Acceptance criteria (P0 for CLI, P1 for web UI):**
- `plancritic escalate list` shows pending escalations with full context; `plancritic approve <id> [--patch ...]` / `plancritic deny <id>` resolve them.
- Resolution is recorded in the plan's history; a patched plan is re-submitted to the critic.
- MCP tools expose list/approve/deny so the resolution can happen from the agent's own workspace.
- Web UI (v0.2): AIDE-style context panel — goal + current plan + blocker + critique trail + revision history + inline plan editing.

### CUJ 6 — Inspect the plan and its history (plan as a versioned artifact)

As a reviewer, I can diff plan revisions, see which critiques drove which changes, and answer "was this failure planning or execution?" from the store.

**Acceptance criteria (P0):**
- `plancritic plan show <id>`, `plancritic plan diff <v1> <v2>`, `plancritic plans list` over the store (SQLite default).
- Critique history is stored per revision; each resolution and escalation is recorded.
- Store interface is pluggable; SQLite default, Postgres-ready behind the same interface.

### CUJ 7 — Wire into my framework ("integrate in one afternoon")

As an engineer, I hook PlannerCritic into any of the six frameworks with an idiomatic adapter and get a pre-execution plan gate without breaking the agent loop.

**Acceptance criteria (P0):**

| Framework | Integration point | Gate experience |
|-----------|-------------------|-----------------|
| **Raw Python** | library: `plancritic.plan(goal)` → `ApprovedPlan` / `EscalationNeeded` | clean objects, no framework dependency |
| **MCP** | PlannerCritic exposes `plan`, `critique`, `escalate-list`, `escalate-approve` MCP tools | any MCP agent calls plan/critique through its own tool stack |
| **LangGraph** | pre-execution node / callback on the tool executor | approved plan becomes the steps' input; re-gate before each step |
| **PydanticAI** | `@plancritic.guard` on the agent or a plan-review tool | gate before first tool call; sub-task re-check before each step |
| **CrewAI** | task-creator/task-interceptor wrapper | plan gates task scheduling; sub-task re-check on preconditions |
| **OpenAI Agents SDK** | runner-level hook / tool guardrail | first-tool-call gate; per-step re-check |

Every adapter: audit trail for plan approval + any re-gate decision, and field-test validated (CUJ 9).

### CUJ 8 — Execution-time re-gate ("the plan was right, then the world moved")

As an operator, I bind an approved plan to its executor; before each step executes, the critic optionally re-checks whether the step's preconditions still hold, and a stale step triggers a replan instead of blind execution.

**Acceptance criteria (P1):**
- Adapter supports `re-gate: before-each-step | off`. In `before-each-step`, the step's stated preconditions are re-verified against current context.
- A false precondition produces a replan request, not a blind step execution.
- The re-gate decision is recorded in the plan's execution trace.

### CUJ 9 — Field test ("it actually works in real agent loops")

As a contributor or reviewer, I watch PlannerCritic's draft→critique→revise→escalate behavior in real running contexts across every supported framework, driven by a hermetic CI gate and a local-model release sweep. Field tests are a release gate.

**Acceptance criteria (P0, gating release):**
- **Hermetic CI gate (no paid LLM):** deterministic gates + loop controller + convergence/regression semantics asserted with fake providers in CI. Never flakes, never costs money.
- **Release field sweep (local model):** `plancritic field-test` drives the domain-agnostic goal corpus (migration, rollout, refactor, incident-response) through real planner/critic LLM calls via OMLX/Ollama across all six framework adapters; assert: a seeded flaw in each goal's first draft is caught; revision converges to approval (or escalates cleanly on known-ambiguous goals); escalation round-trips; re-gate detects a stale precondition.
- Every adapter is exercised in its native framework; a field-test report (`docs/field-test/`) records goals × frameworks × expected/actual × pass/fail, regenerated each release.
- Any P0 miss blocks the release.

### CUJ 10 — Diagnose a failed run (planning vs execution)

As a reliability engineer, given a failed agent run tied to an approved plan, I can classify the failure as planning or execution, and see any critique that missed it flagged for improvement.

**Acceptance criteria (P1):**
- A plan–execution link records a `planning` / `execution` classification on failure (via CLI or adapter).
- A planning failure that the critic missed surfaces as a "missed critique" record with the relevant critique history.
- The record feeds a suggested deterministic check (an operator-visible recommendation; automated promotion feeds LessonExtractor in v0.2+).

---

## 7. Feature Set

> Priority scale: **P0** (v0.1.0): must have; **P1** (v0.2.0); **P2** (v0.3.0+); **P3** backlog.

### 7.1 Core engine (model- and framework-agnostic)
| ID | Feature | Priority | Notes |
|---|---|---|---|
| F-01 | Goal schema (constraints + `risk_tolerance`) | P0 | Typed JSON schema |
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

### 7.2 LLM provider layer
| ID | Feature | Priority | Notes |
|---|---|---|---|
| F-20 | `LLMProvider` protocol (name, base_url, model, transport, api_key) | P0 | Registry-first: built before any concrete transport |
| F-21 | Config-driven provider registry (`plancritic providers add/list/rm`) | P0 | persists config |
| F-22 | OpenAI-compatible transport (first implementation of the protocol) | P0 | OMLX/Ollama/vLLM/OpenRouter/OpenAI |
| F-23 | Separate provider/model for planner vs critic | P0 | recommended different family for the critic |
| F-24 | Structured-output enforcement (plans and findings parse into typed schemas) | P0 | retries on schema-mismatch |
| F-25 | Anthropic + Google (Gemini) transports | P1 | same protocol, new registration |

### 7.3 Escalation
| ID | Feature | Priority | Notes |
|---|---|---|---|
| F-30 | Escalation manager — minimal precise question, blocker focus | P0 | |
| F-31 | Escalation CLI (`escalate list/approve/deny`, patching) | P0 | v0.1 |
| F-32 | Escalation MCP tools (list/approve/deny) | P0 | v0.1 |
| F-33 | AIDE-style web UI: goal + plan + blocker + critique trail + revision history + inline editing | P1 | v0.2 React viewer on the store |
| F-34 | Resolution recorded in plan history; patched plans re-submitted to critic | P0 | |

### 7.4 Framework adapters (the tooltrust six)
| ID | Feature | Priority | Notes |
|---|---|---|---|
| F-40 | Raw Python adapter | P0 | library objects, no framework dep |
| F-41 | LangGraph adapter | P0 | pre-execution node / callback + per-step re-gate |
| F-42 | PydanticAI adapter | P0 | guard + per-step re-check |
| F-43 | CrewAI adapter | P0 | task interceptor + per-step re-check |
| F-44 | OpenAI Agents SDK adapter | P0 | runner hook / guardrail + per-step re-check |
| F-45 | MCP server (planner/critic/escalation tools) | P0 | any MCP agent |
| F-46 | Execution-time re-gate (`before-each-step | off`) | P1 | precondition drift → replan |

### 7.5 Execution feedback
| ID | Feature | Priority | Notes |
|---|---|---|---|
| F-50 | Plan–execution link + `planning`/`execution` failure tagging | P1 | record-only at v0.1 |
| F-51 | Missed-critique record ("critic said fine; execution disagrees") + critique history snapshot | P1 | data model at v0.1 |
| F-52 | Suggested deterministic check surfaced to operator | P1 | feeds LessonExtractor v0.2+ |

### 7.6 Delivery surfaces & tooling
| ID | Feature | Priority | Notes |
|---|---|---|---|
| F-60 | PyPI package `planner-critic` (import `planner_critic`) | P0 | |
| F-61 | CLI `plancritic`: providers, plan, critique, approve/deny, plans/diff, field-test | P0-P1 | |
| F-62 | FastAPI HTTP service (plan submit, escalate, query, approve) | P0 | for non-Python hosts |
| F-63 | SQLite plan store (shipped default) | P0 | |
| F-64 | Postgres store (behind the same interface) | P1 | |
| F-65 | Domain-agnostic sample goal corpus (migration, rollout, refactor, incident-response) | P0 | examples/ |
| F-66 | Demo trace with a seeded flaw → caught → revised → approved/escalated | P0 | the "aha" narrative |
| F-67 | Hermetic CI field-test gate (fake providers) | P0 | never calls a paid LLM |
| F-68 | Local-model release field sweep (`plancritic field-test`, OMLX/Ollama) | P0 | release gate |

### 7.7 Reliability & degraded modes
| ID | Feature | Priority | Notes |
|---|---|---|---|
| F-70 | Provider failure (timeout/error) → deterministic `planning_unavailable` failure mode per role | P0 | fail-closed: no plan execution on unverified plan |
| F-71 | Structured-output schema-mismatch retry with bounded retries, then failure | P0 | |
| F-72 | Store failure → clear error; plan store is a side channel, plan/critique continues in-memory with warning | P1 | |
| F-73 | Fail-closed default: unapproved plan cannot be handed to an executor | P0 | |
| F-74 | Determinism contract for the loop controller (same inputs, same loop decisions) | P1 | CI-assertable |

---

## 8. Non-Goals (v1.0)

- **Executing the plan itself** — PlannerCritic plans and critiques; an existing runner executes. The adapters gate, re-gate, and serialize; they do not run the plan.
- **Replacing execution engines or agent frameworks** (LangGraph, CrewAI, etc.).
- **Guaranteeing plan correctness** — it reduces risk; it cannot eliminate it (the critic shares the planner's blind spots as an LLM).
- **Arbitrary multi-planner architectures** — starts as one planner + one critic.
- **Automatic goal intake from unstructured chat without a goal schema.**
- Exhaustive model-family support at v0.1 — the OpenAI-compatible transport covers most real deployments; Anthropic/Gemini are v0.2 transports on the same protocol.
- **Full LessonExtractor** — missed-critique records and suggested checks ship; automated standing-rule promotion is the Week 8 flagship's job.

---

## 9. Success Criteria & Metrics

Product-level success (by v0.1.0 release):
1. **Adoption friction:** `pip install planner-critic` → register provider → first approved plan < 10 minutes for a reader (target < 5 min with the demo trace).
2. **Blocker-detection rate:** on the demo corpus's seeded-flaw goals, the critic surfaces the seeded flaw in ≥ 90% of runs (across provider backends in the field sweep).
3. **Loop correctness:** every goal either converges to a threshold-satisfying approval or escalates with a precise question — 100% on the deterministic CI gate; ≥ 95% on the live field sweep.
4. **Escalation precision:** escalations carry a single minimal question resolvable with one decision (approve/deny/patch) — audited in tests.
5. **Framework coverage:** all six adapters exercise plan → approve → (re-gate) → execute in their native frameworks in the field-test report.
6. **Cost:** the entire HTTP/CLI/deterministic test suite runs with $0 LLM spend (hermetic CI gate); the field sweep runs on a local model.
7. **Forensics value:** plan–execution failure classification and missed-critique records are queryable from the store for any approved plan.
8. **Determinism:** loop-controller decisions are deterministic on identical inputs (CI-asserted).

OSS community (post-launch): 25+ stars, 3 external contributors, 1+ external framework-ecosystem adoption per quarter.

---

## 10. Reliability & Support

- **Fail-closed contract:** an unapproved plan can never reach an executor; a provider failure produces a distinct `planning_unavailable` failure mode per role; no "guess and continue" path.
- **Determinism:** the loop controller is deterministic on identical inputs; the LLM is only ever advisory in the critique/planner roles and its structured output is schema-revalidated.
- **Cheap by design:** deterministic gate first, local model default, hermetic CI gate — no paid LLM on the default path or in CI.
- Plane store is a side channel (planning continues in memory if the store is down, with a warning); persisted when healthy.
- Support doc, CONTRIBUTING gate (tests/coverage/mypy), CHANGELOG policy (per portfolio convention).

---

## 11. Risks & Open Questions

- **Critic shares the planner's blind spots** (both are LLMs) — mitigated by separate roles, recommended different model family, bounded loop, regression guard, and the missed-critique feedback loop.
- **Critic can be net-negative** (research: a critic re-reading the same context with the same model family can disrupt more than it recovers) — mitigated by typed rubric + deterministic gates + per-goal thresholds; validate on the field corpus before deployment.
- **Converging too easily or too rarely** — the convergence detector + regression guard bound both; thresholds tuneable.
- **Designing escalations that are genuinely minimal, not nagging** — the single-question + full-context panel is the design; audited for precision in tests.
- **Scope of v0.1 is large** (engine + provider registry + two critique modes + six adapters + CLI + MCP + HTTP + stores + field test) — sequenced inside the WBS so the engine is testable before the breadth lands; risk is schedule, not architecture.
- **Planner and critic as separate model families at v0.1** — technically cheap (config), but the *default* demo should pick a free/local pairing that demonstrates cross-family critique.
- **Fairness of the demo corpus** — the seeded-flaw goals must be genuinely hard (blade-length ordering, unverified deps) so the critic's catch is credible, not staged.

---

## 12. Roadmap (Milestone Sketch)

- **v0.1.0 (P0):** core engine (F-01–F-12), provider registry + OpenAI-compatible transport (F-20–F-24), both critique modes, escalation CLI + MCP tools (F-30–F-32, F-34), six adapters with gate (F-40–F-45), SQLite store (F-63), CLI + HTTP service (F-61–F-62), sample-goal corpus + demo trace (F-65–F-66), hermetic CI gate + field sweep (F-67–F-68), fail-closed modes (F-70–F-73). **Shipped when CUJs 1–9 (P0) pass and the field-test matrix is green.**
- **v0.2.0 (P1):** execution feedback (F-50–F-52), re-gate (F-46), AIDE web UI (F-33), Postgres store (F-64), Anthropic/Gemini transports (F-25), determinism contract (F-74), automated missed-critique → standing-rule promotion interface for LessonExtractor.
- **v0.3.0 (P2):** multi-planner variants (deliberate, on user request), planning-quality eval suite via EvalForge, fleet escalation analytics, plan-shape recommendation.
- **v0.4.0 (P3):** SwarmOS coordination integration, community packs of critique heuristics, escalation-approval-rate dashboards.

---

## 13. Connected

- Vault: [[projects/High/146-PlannerCritic.md]] · [[projects/Agentic-AI-Ideas/01-Multi-Agent-Reasoning.md]] · [[_6-MONTH-PLAN.md]]
- Siblings: EvalForge (measures planning quality), ToolTrust (gates tool calls), LessonExtractor (consumes missed-critique feedback), AgentLab (execution backend)
- **Grounded in:** "From Plan to Action" (arXiv 2604.12147 — a bad plan hurts more than none), self-correction blind spot (arXiv 2507.02778 — 64.5%), Copilot CLI Rubber Duck (74.7% gap closed), OWASP 2026 Top 10 ASI08, Stanford 2026 AI Index (~1-in-3 agent failures)