# 01 — Why (Business Requirements)

> Sub-document of the [PlannerCritic Engine PRD](../PRD.md). Covers the market context, the pain we remove, and why this matters for the OSS portfolio.

## 1.1 The market context

The agent ecosystem has spent enormous energy on **execution** — tools, memory, orchestration, retrieval — and almost none on **planning quality**. Agents are judged by whether they can *do* a task; the failures that actually matter happen before a single tool call: the agent decided to act on a plan that was incomplete, wrongly ordered, or built on an unverified assumption.

- **Agents fail ~1 in 3 attempts.** Stanford's 2026 AI Index reports agents fail roughly one in three attempts on structured benchmarks (OSWorld rose to 66.3% — still within ~6 points of humans). The gap is closing on *execution*, but the *planning* layer is where the expensive, hard-to-detect failures live.
- **Planning failures are the most expensive class.** Industry analyses (APEX-Agents, 2026) attribute the largest share of agent failure to **planning failures** — not because they're frequent, but because there is **no error signal**: the plan *looked* fine at step zero and collapsed at step three, after state had already diverged. You discover a planning failure mid-execution, when rollback is expensive or impossible.
- **A bad plan hurts more than no plan at all.** "From Plan to Action" (arXiv 2604.12147, 16,991 SWE-agent trajectories, 4 LLMs, 8 plan settings) measured that a *bad* plan degrades performance more than having no plan, while a *standard* plan improves issue resolution. Planning is the binding constraint over execution.
- **Plan quality is fixable cheaply.** The Agent Planning Benchmark (APB) showed that a single refinement round moved models from 22% → 60% on holistic planning — plan quality, not execution, is often the lever.
- **Multi-step workflows compound per-step failure.** At a 20% per-tool failure rate, a 5-step workflow has only a **32.8% chance of completing** without a tool error. Every step the planner added without justification multiplies risk; every step it ordered wrong is a guaranteed future failure.

### 1.1.1 Why single-pass planning is blind

A goal like "migrate this service to the new auth provider" decomposes in one hidden chain-of-thought pass; three steps in, the agent discovers the DB schema was never checked, or an outage window was never coordinated. There is no draft to review, no reviewer to catch the gap, no structured escalation — just a failed run and a partial state change to clean up.

### 1.1.2 Why self-review is agreement with extra steps

The self-correction blind spot is real and measured: across 14 LLMs, same-model review fails to correct errors in the model's own output at an average **64.5% rate** (arXiv 2507.02778). The critic must be a *different* role — and, ideally, a different model family — or it inherits the producer's failure modes.

### 1.1.3 Why a cross-model critic pays for itself

GitHub Copilot CLI's "Rubber Duck" critic — a second GPT-model reviewing plans pre-execution — **closed 74.7% of the gap** to Opus-alone, and shipped to GA in June 2026. The pattern works; nobody has productized it as a standalone, model-agnostic OSS engine. Voyager's ablation reinforces the value of verification: removing self-verification let buggy code accumulate in the skill library; with it, the agent mined 3.3× more items and 15.3× faster tech-tree progress.

### 1.1.4 Why regulators now demand plan review

OWASP's 2026 Top 10 for Agentic Applications (ASI08, Cascading Failures) explicitly recommends: *"Separate planning from execution — an independent governance agent reviews and signs off on plans before execution begins."* The EU AI Act makes human oversight a legal obligation for high-stakes decisions. Escalation-to-human is a **compliance feature**, not a design weakness.

---

## 1.2 The pain we remove

| Status quo (today) | Pain |
|---|---|
| Single-pass chain-of-thought decomposition | Hidden, single-pass, uninspectable plan; hard subproblems silently skipped; failure discovered mid-execution after state diverged |
| Same-model "self-review" | 64.5% blind-spot rate — the producer's failure modes are inherited; rubber-stamp with extra steps |
| Framework plan-and-execute examples (LangGraph, AutoGen) | Plan is a transient message, not a typed/versioned/inspectable artifact; no approval gate; unbounded loops |
| Human-only plan mode (Claude Code, Codex) | Human is the critic (expensive, all-or-nothing approve/reject); no LLM prereview, no revision loop primitives, no audit trail |
| Roll-your-own plan review inline in app code | Logic scattered, untested, no convergence semantics, no escalation manager, no plan store |
| Post-execution verification (Voyager, Reflexion) | Catches failures *after* state is mutated; the cheap pre-execution catch window is missed |

---

## 1.3 Why it matters for the pilot & OSS goals

- **For agent builders:** a pre-execution quality gate that catches structural plan failures — missing steps, unsafe ordering, unverified dependencies — before state is mutated, across *any* model and *any* framework they already use.
- **For operators of high-stakes agents:** escalate the genuinely ambiguous decisions to a human with a precise question; keep a versioned, diffable plan + critique history for diagnosis and compliance ("was this a planning failure or an execution failure?" is answerable from the store).
- **For the solo-build OSS portfolio:** a Tier-1, high-engagement problem — planning is ranked the **#1 agentic hard problem** in the Agentic AI Ideas catalog — with a sharp article series ("Why Your Agent Needs a Code Review for Its Plans", "The Draft-Critique-Revise Loop: How Humans Plan, Productized for LLMs", "Escalation Is a Feature"), and strong family compatibility with the shipped stack:
  - **EvalForge** measures planning quality
  - **ToolTrust** gates tool calls (the approved plan's steps are what ToolTrust authorizes)
  - **LessonExtractor** consumes missed-critique feedback into standing rules
  - **AgentLab** is the execution backend for approved plans

### 1.3.1 The portfolio compounding story

PlannerCritic is the **planning** layer in a coherent agentic infrastructure stack: *eval → observe → enforce → **plan** → persist → communicate → manage → isolate → secure*. It is the first project that sits *in front of* execution, making the others more valuable — EvalForge can score plans, ToolTrust gates the steps an approved plan authorized, LessonExtractor learns from plans that failed despite critique. No other project in the catalog closes this loop.

---

## 1.4 Grounded in (sources)

- Stanford 2026 AI Index — ~1-in-3 agent failures (hai.stanford.edu/ai-index)
- "From Plan to Action" (arXiv 2604.12147) — a bad plan hurts more than none
- Self-correction blind spot (arXiv 2507.02778) — 64.5% average across 14 LLMs
- Copilot CLI "Rubber Duck" — 74.7% gap closed (github.blog, 2026)
- Voyager ablation (arXiv 2305.16291) — self-verification accumulates correct skills
- APB / Agent Planning Benchmark — one refinement round: 22% → 60%
- OWASP Top 10 for Agentic Applications 2026 (ASI08, ASI01, ASI09)
- EU AI Act — human oversight obligation for high-risk systems