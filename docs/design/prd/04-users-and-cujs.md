# 04 — Target Users & Critical User Journeys

> Sub-document of the [PlannerCritic Engine PRD](../PRD.md). Who it's for, and the journeys that define the feature set.

## 4.1 Target users

**Primary persona — Agent Platform Engineer / AI Engineer building multi-step agents.** Builds agents (LangGraph, PydanticAI, CrewAI, OpenAI SDK, MCP, raw Python) that handle multi-step, high-stakes goals where acting on a bad plan is expensive. Wants a planning layer in front of execution without rewiring the framework.

**Secondary personas:**
- **Agent framework adopters** — want a planning/critique layer their framework can consume as a library or MCP tool.
- **SRE / reliability engineers** — want pre-execution gates and plan-vs-execution failure classification for production agents.
- **Researchers / students** — experimenting with structured critique and self-correction loops; want a well-typed artifact to instrument.
- **OSS maintainers** — safe defaults, cheap local-model path, anonymous-by-default, extensible heuristic.

**Primary non-negotiable for all personas: minimal time-to-first-approved-plan** → low-friction install, a registered provider, one non-trivial goal, a visible critique→revise→approve round-trip.

**Not for:**
- Simple single-shot agents that answer questions in one call.
- Teams building demos where a wrong plan has no real consequence.
- Users who want full autonomy with no human-in-the-loop escalation path.

---

## 4.2 Critical User Journeys (CUJs)

Twelve critical journeys, each with a gate / decision / acceptance criteria. North star for the feature set.

### CUJ 1 — Register a provider and plan a goal ("15 lines to a plan")

As an engineer, I register my model endpoint (local or paid), submit a goal with constraints, and get a typed, structured plan I can see immediately.

**Acceptance criteria (P0):**
- `plancritic providers add <name> --transport openai-compatible --base-url ... --model ...` works; provider list persists and loads on restart.
- `plancritic plan "<goal>" --constraints ...` returns a typed plan (tasks, deps, ordering, verification, rollback) as JSON/YAML and prints a readable rendering.
- Works with a local OpenAI-compatible endpoint (OMLX/Ollama) with zero paid spend; works with any configured provider.
- The goal carries constraints + `risk_tolerance` + optional `budget`.

### CUJ 2 — The critic catches a real flaw (the "aha" moment)

As an engineer, I run a goal through planner+critic and watch the critic flag a genuine structural gap the planner missed — a missing verification step, an unsafe ordering, an unverified dependency — with a severity grade and a precise reason.

**Acceptance criteria (P1, but the project isn't real without it):**
- Demo corpus includes ≥1 goal where the first draft is critiqued with a *correct* blocker (a seeded flaw) that the planner actually fixes in revision.
- Findings are structured (heuristic family, severity, task reference, reason code) — not free text.
- `plancritic plan show <id> --findings` renders the critique.

### CUJ 3 — Critique in the low-cost mode doesn't break (deterministic-first)

As an operator on a budget, I run the same goal in `deterministic-first` mode and confirm every plan still passes the free deterministic gates, with the LLM critic only invoked on surviving drafts.

**Acceptance criteria (P0):**
- Deterministic gates: schema validity, dependency-cycle detection, ordering sanity, verification-step presence, rollback presence — all free, no LLM call.
- `critic.mode=llm-every-revision` switches the full six-heuristic LLM critique on; same engine, one config flag.
- Diff-aware critique (F-78): on revision N>1, only changed tasks + dependents are re-audited (cost optimization).

### CUJ 4 — The loop converges (or escalates at the right moment)

As a user, I watch the planner revise under critique until approval — or, on a genuinely ambiguous goal, escalate with a precise question instead of guessing or stalling.

**Acceptance criteria (P0):**
- Revision cap (default 3, configurable) escalates when exceeded.
- Convergence detection escalates early when revisions circle the same blockers or diffs converge to near-zero between versions.
- Regression guard escalates when a revision *introduces* a new blocker.
- Budget hit escalates rather than spending more.
- Approved plans meet the per-goal threshold (strict = zero warnings; balanced = warnings acknowledged).
- The loop controller is **deterministic on identical inputs** (CI-asserted, F-74).

### CUJ 5 — Escalate to a human, human resolves, agent continues

As an operator, when the loop escalates I see the goal, the current plan, the blocker, the critique trail, and the revision history; I approve (optionally patching the plan) or deny; the loop resumes with the resolution recorded.

**Acceptance criteria (P0 for CLI + MCP, P1 for web UI):**
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
- `plancritic plan show <id> --graph` renders the task DAG as Mermaid (F-75).

### CUJ 7 — Replay a plan trace (the demo/article workhorse)

As an engineer or presenter, I replay a stored plan's full draft→critique→revise→approve/escalate trace step-by-step, for demos, debugging, and articles.

**Acceptance criteria (P0):**
- `plancritic replay <plan_id>` walks the stored version history, printing each plan version, its findings, and the loop decision that followed.
- `--step <n>` jumps to a revision; `--format json` for scripting/animation.

### CUJ 8 — Wire into my framework ("integrate in one afternoon")

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

Every adapter: audit trail for plan approval + any re-gate decision, and field-test validated (CUJ 11).

### CUJ 9 — Execution-time re-gate ("the plan was right, then the world moved")

As an operator, I bind an approved plan to its executor; before each step executes, the critic optionally re-checks whether the step's preconditions still hold, and a stale step triggers a replan instead of blind execution.

**Acceptance criteria (P0):**
- Adapter supports `re-gate: before-each-step | off`. In `before-each-step`, the step's stated preconditions are re-verified against current context.
- A false precondition produces a replan request, not a blind step execution.
- The re-gate decision is recorded in the plan's execution trace.

### CUJ 10 — Diagnose a failed run (planning vs execution)

As a reliability engineer, given a failed agent run tied to an approved plan, I can classify the failure as planning or execution, and see any critique that missed it flagged for improvement.

**Acceptance criteria (P0):**
- A plan–execution link records a `planning` / `execution` classification on failure (via CLI or adapter).
- A planning failure that the critic missed surfaces as a "missed critique" record with the relevant critique history.
- The record feeds a suggested deterministic check (operator-visible recommendation; automated promotion feeds LessonExtractor in v0.2+).

### CUJ 11 — Field test ("it actually works in real agent loops")

As a contributor or reviewer, I watch PlannerCritic's draft→critique→revise→escalate behavior in real running contexts across every supported framework, driven by a hermetic CI gate and a local-model release sweep. Field tests are a release gate.

**Acceptance criteria (P0, gating release):**
- **Hermetic CI gate (no paid LLM):** deterministic gates + loop controller + convergence/regression/budget semantics asserted with fake providers in CI. Never flakes, never costs money.
- **Release field sweep (local model):** `plancritic field-test` drives the domain-agnostic goal corpus (migration, rollout, refactor, incident-response) through real planner/critic LLM calls via OMLX/Ollama across all six framework adapters; assert: a seeded flaw in each goal's first draft is caught; revision converges to approval (or escalates cleanly on known-ambiguous goals); escalation round-trips; re-gate detects a stale precondition; a planning failure is classified and a missed critique is recorded.
- Every adapter is exercised in its native framework; a field-test report (`docs/field-test/`) records goals × frameworks × expected/actual × pass/fail, regenerated each release.
- Any P0 miss blocks the release.

### CUJ 12 — Extend the critique heuristics ("one heuristic pack, one PR")

As a domain expert, I define a new critique heuristic family (or a deterministic rule) using a documented schema, validate it, and the engine applies it — no engine core changes.

**Acceptance criteria (P1):**
- `plancritic heuristics add` flow: define a heuristic family (name, when to apply, deterministic check or LLM prompt) via a pack schema; `plancritic heuristics validate && test` passes without engine changes.
- A one-page "how to contribute a heuristic pack" doc is the only reference needed.