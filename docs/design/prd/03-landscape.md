# 03 — Landscape & Identity

> Sub-document of the [PlannerCritic Engine PRD](../PRD.md). What exists, what's missing, and our wedge.

## 3.1 The planner-critic / plan-review landscape

The planner-critic loop is **ubiquitous as research and prompt, and nearly absent as product.**

| Project | Type | What it does | Our wedge |
|---|---|---|---|
| **PlanCritic** (Burns, Hughes, Sycara '24) | Research + code | LLM translates NL specs → PDDL; RLHF reward model + genetic algorithm scores/revises plans (disaster-recovery domain) | Research artifact in one PDDL domain; not a model-agnostic engine; closest name collision |
| **LangGraph plan-and-execute** | Framework example | Planner → Executor → Re-planner loop | No independent critic, no typed plan schema, no approval gate, no escalation |
| **Microsoft AutoGen** | Multi-agent framework | Group-chat Planner/Writer/Editor/Reviewer agents | Critic is an unbounded app-level conversation pattern; no plan artifact semantics; no bounded loop |
| **GitHub Copilot CLI "Rubber Duck"** | Product (closed, OSS client) | Second GPT model reviews plans pre-execution; closes 74.7% of the Sonnet↔Opus gap | Closed single-surface; not a standalone engine; no bounded loop/escalation/store |
| **Claude Code / OpenAI Codex plan mode** | Product | Read-only plan → human approve/reject → execute | Human is the critic (expensive); no LLM prereview, no revision loop, no versioning |
| **`codex-skill`** (cathrynlavery) | OSS plugin | Hook sends plan to another model for review | Single-role, no loop/budget/escalation; a plugin, not an engine |
| **Voyager** (MineDojo) | Research + OSS | Self-verification *after* execution; revises skill library | Verify *after* acting; same-model; no pre-execution plan gate |
| **Reflexion** (Shinn et al.) | Research + OSS | Verbal self-reflection: evaluate → reflect → retry | Same-model, after-failure; no separate critic before acting |
| **Self-Refine / Tree-of-Thoughts / Plan-and-Solve** | Research prompting | Single-model iterative self-feedback; NL plan decomposition | Purely prompts/papers, not productized loops |
| **SWE-agent ("From Plan to Action")** | OSS research agent | Default plan embedded in system prompt; studies plan compliance | Proved a *bad plan hurts more than no plan*; planning is the binding constraint |
| **APB (Agent Planning Benchmark)** | Research benchmark | Diagnostic separating planning vs execution failure | Created the planning-vs-execution taxonomy we plug into |

## 3.2 The gap (what nobody ships)

1. **The plan is not a first-class artifact.** Framework examples and CLIs treat the plan as a transient message. No existing OSS exposes the plan as a *typed, versioned, inspectable, persisted* object with per-step structure and full revision history.
2. **No bounded revise-until-approved loop with escalation semantics.** Loops are either unbounded conversation (AutoGen) or single-round human approve/reject (Claude/Codex). Nobody implements: `plan v1 → critique → v2 → ... → max_attempts OR stall-detection → human escalation`.
3. **Critic audit dimensions are not structured.** Every system's critique is free-text or story-quality feedback. No product issues a per-subtask **typed audit** across the six heuristic families with a machine-readable verdict.
4. **Model-architecture know-how lives in guidance, not code.** The consensus (separate model family; bounded loop; escalate on non-convergence) is codified in blog patterns and at most one closed CLI feature (Copilot's Rubber Duck). The standalone-OSS window is open.
5. **After-the-fact vs before-the-act.** Voyager/Reflexion verify *after* execution; the cheaper pre-execution gate exists only in closed CLIs. A standalone, model-agnostic engine that gates before any tool call runs is unclaimed territory.
6. **Nothing is benchmark/instrumentation-friendly.** APB just created the planning-vs-execution diagnostic; a critique engine emitting structured verdicts plugs directly into that instrumentation gap.

## 3.3 PlannerCritic vs the crowd (identity)

1. **Standalone, model-agnostic engine** — the draft-critique-revise loop as a reusable library, not a framework plugin or a prompt. Works with any OpenAI-compatible model and any of the six major frameworks.
2. **Plan as a first-class artifact** — typed schema, versioned, diffable, persisted, with critique history — not a transient conversation message. *"The plan is a PR, and the critic is the reviewer."*
3. **Bounded loop with real termination semantics** — revision budget + convergence detection + regression guard + budget — no unbounded improve-until-happy, no rubber-stamp.
4. **Structured, low-cost critique** — deterministic gates always on, LLM critic on the drafts that survive them; severity-graded typed findings, not free-text vibes. Optionally full-depth LLM critique per revision when the audit justifies it.
5. **Escalation as a feature** — minimal, precise human questions with full revision context and direct plan patching — the EU-AI-Act / OWASP ASI08 compliance story, productized.
6. **Planning-vs-execution forensics** — tagged failure classification and missed-critique feedback — an instrumentation surface no one else ships.

## 3.4 Sources

- arxiv.org/abs/2412.00300 (PlanCritic) · 2305.16291 (Voyager) · 2303.11366 (Reflexion) · 2303.17651 (Self-Refine) · 2305.04091 (Plan-and-Solve) · 2405.15793 (SWE-agent) · 2604.12147 (From Plan to Action) · 2507.02778 (self-correction blind spot)
- agentpatterns.ai/patterns/agent-design/critic-agent-plan-review
- github.com/langchain-ai/langgraph (plan-and-execute) · github.com/github/copilot-cli (Rubber Duck) · github.com/cathrynlavery/codex-skill · github.com/microsoft/autogen