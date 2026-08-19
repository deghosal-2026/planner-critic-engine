# D13 — Design Decision Log

> **Authored in:** M1 (Core Engine) · **Status:** Active · **WBS:** D13 · **Refs:** [PRD 05 §2.4 design-decision log](../design/prd/05-features.md)

Log every design decision with status (Accepted / Proposed / Rejected), context, drivers, the alternate considered, the outcome, and consequences. New entries are appended; statuses change in place.

## M1 Entries

### DD-01 — The core engine is fully model- and framework-agnostic

- **Status:** Accepted
- **Context:** The system must serve raw Python, LangGraph, PydanticAI, CrewAI, OpenAI Agents SDK, and MCP (the tooltrust six), and be testable without any model provider.
- **Drivers:** testability (hermetic CI, no paid LLM); portability across 6 adapter surfaces; the core justifies its existence by owning mechanics, not brands.
- **Alternative considered:** Build the core inside one framework (e.g. only PydanticAI). Rejected: an engine married to one adaptation layer can only ever serve that layer.
- **Outcome:** `roles.py` defines `PlannerRole` / `CriticRole` protocols with plain typed JSON I/O. The core (`schema`, `gates`, `loop`) imports **no** LLM SDK, no framework adapter, no store. M1 ships no provider or adapter at all.
- **Consequences:** Providers/adapters are strictly opt-in M2 modules; the hermetic test suite runs green with fully scripted roles.

### DD-02 — Fail-closed determinism before any model spend

- **Status:** Accepted
- **Context:** §2.6 requires deterministic checks to precede the LLM critic so free, injection-immune checks resolve as much as possible before spend; approval must fail closed (a malformed plan is a blocker).
- **Drivers:** cost discipline (don't pay a model to re-find a schema error); injection-immunity (a gate cannot be prompted); fail-closed semantics for a planning engine.
- **Alternative considered:** LLM-first critique with gates as advisory. Rejected: advisory gates reintroduce exactly the blind-spot the project exists to fix.
- **Outcome:** `run_deterministic_gates` runs 8 gates on every revision before the critic; `strict` tolerance defers on any warning, `balanced` on any blocker. Malformed critic output is dropped and logged, never trusted.
- **Consequences:** Every M1 acceptance scenario is deterministic and fully scripted; the LLM critic is a drop-in, not a dependency of the core's correctness.

### DD-03 — Immutable, versioned, parent-linked plans + allocation-stable findings

- **Status:** Accepted
- **Context:** Revisions must be diffable for forensics and loop convergence must be computable deterministically; findings that panic/regress must be comparable across revisions.
- **Drivers:** replay must show *which critique drove which change* (parent chain); regression guard needs stable identity `(reason_code, task_id)`; `strict/frozen` models guarantee an approved plan is a stable value.
- **Alternative considered:** Mutable plan objects with in-place fixes. Rejected: mutation destroys the audit trail and makes convergence detection unsound.
- **Outcome:** `PlanVersion` is a frozen Pydantic model; new revisions get `id`, incremented `version`, and `parent_version`. Task allocations are stable — `findings` carry `task_id` — so `regression_detected` and `circling_blockers` compare the same identity space across revisions.
- **Consequences:** The plan is a first-class versioned artifact per PRD; M2 diff-aware critique will emit changed-task unions into the critique context on the same identity space.

## M2 Entries

### DD-04 — Provider config is TOML, registry-first (providers in config, not code)

- **Status:** Accepted
- **Context:** §2.4 requires a registry-first provider layer: the engine loads whatever is configured, and a config edit — not a code change — swaps local OMLX/Ollama for a paid provider.
- **Drivers:** cost control (paid providers only when explicitly registered); operator ergonomics (swap endpoints without redeploying); the OpenAI-compatible transport must be the first concrete impl *on top of* the registry, not instead of it.
- **Alternative considered:** Code-level provider registration (a Python API to register transports). Rejected: requires redeploy and forks the config; TOML keeps a single source of truth that `plancritic providers` and the engine both read.
- **Outcome:** `llm/registry.py` reads/writes `plancritic.toml` (`[providers."name"]` specs + `[roles]` role→provider mapping). `plancritic providers add/list/rm` persists the file. A missing config yields an empty registry (roles unbound → `PlanningError`), never a crash.
- **Consequences:** M2 ships the registry + one transport; future transports (Anthropic/Gemini) are new `[providers]` entries on the same protocol.

### DD-05 — Plan store is a side channel: down → warn + continue in memory

- **Status:** Accepted
- **Context:** §7.2 makes the plan store explicitly a side channel — planning continues in memory if the store is down, with a warning, and persists when healthy.
- **Drivers:** the store must never block planning (reliability); forensics lose data only during an outage, never corrupt it; Postgres-ready means the protocol is DB-agnostic.
- **Alternative considered:** The store as a hard dependency of the loop. Rejected: a store outage would halt planning, violating §7.2 and the fail-open-availability (fail-closed-*safety*) split.
- **Outcome:** `PlanStore` protocol; `InMemoryStore` (never fails) is the test/default; `SQLiteStore` raises `StoreUnavailable` on any DB failure; `warn_and_continue` logs the warning. The loop is untouched by store failures.
- **Consequences:** Store writes are best-effort until the store recovers; M2 integration tests assert the loop result is usable even when the store is down.

### DD-06 — EnvProbe is read-only by contract, recorded in the trace, never gate-critical

- **Status:** Accepted
- **Context:** §2.8 probes ground preconditions in live state; §2.4 says deterministic gates never depend on a probe (a probe's result may change between runs).
- **Drivers:** determinism (gates must be pure functions of the plan); safety (probes observe, never mutate); re-gating (M4) needs the recorded result at execution time.
- **Alternative considered:** Probes as inputs to deterministic gates. Rejected: breaks the determinism contract — the same plan could pass or fail a gate depending on live state.
- **Outcome:** `probe/base.py` defines `ProbeRequest`/`ProbeResult` and the `Probe` protocol; `run_probe` dispatches to built-ins (`env_var`, `http_check` real; `db_query`, `deploy_status` M2 stubs). A probe failure is recorded as `ok=False`, never raised. Deterministic gates ignore probes entirely.
- **Consequences:** Probe results enrich execution-time re-gating and the execution trace; M2 probes run read-only and are recorded, satisfying the hermetic no-network test contract via injectable httpx clients.

## M3 Entries

### DD-07 — Deterministic-first is the default critique mode

- **Status:** Accepted
- **Context:** §2.5 makes `deterministic-first` the default: free, injection-immune gates run before any model spend; the LLM critic only fires on drafts that survive the gates.
- **Drivers:** cost discipline (don't pay a model to re-find a schema error); injection-immunity; the critique engine must stay testable with zero LLM (hermetic CI).
- **Alternative considered:** `llm-every-revision` as the default for audit depth. Rejected: full-depth audit is the option, not the baseline — it spends on drafts the gates already rejected.
- **Outcome:** `CriticMode` gains a third value `heuristic-only` (gates only, no LLM); `deterministic-first` remains the default; `should_invoke_llm(mode, findings)` is a pure dispatch. A gate blocker short-circuits the model in deterministic-first.
- **Consequences:** Three critique strategies are first-class and field-testable against a real local model (see `docs/field-test/omlx-critique-modes-field-test.md`); the default path is cheap and hermetic.

### DD-08 — Diff-aware scope is changed tasks + transitive dependents

- **Status:** Accepted
- **Context:** §2.5.3 asks for a cost optimization: on revision N>1 re-audit only what changed rather than the whole plan; a full re-critique stays available via `llm-every-revision`.
- **Drivers:** budget alignment (fewer tokens per revision); correctness (a change to task X can invalidate its dependents, so scope must include them); determinism (scope is computed from the plan diff, never from the model).
- **Alternative considered:** Re-audit changed tasks only, without dependents. Rejected: a changed dependency edge silently stale-audits downstream tasks.
- **Outcome:** `critique/diff.py` computes `changed_tasks` from `PlanDiff` (added + changed ids) and expands via `dependent_closure` (transitive dependents through the dependency DAG). `audit_scope` returns the full plan on the root revision. The loop calls `audit_diff` in deterministic-first mode and `audit` in llm-every-revision.
- **Consequences:** `llm-every-revision` always does a full audit (no scope reduction); the diff scope is a pure function of plan history, preserving determinism.

## M4 Entries

### DD-09 — Replan policy defaults to `patch`

- **Status:** Accepted
- **Context:** §2.7b defines three replan policies — `patch`, `restart`, `abort` — and requires a sensible default for goals that don't explicitly set one.
- **Drivers:** the most common failure mode is a single step that goes wrong (transient infrastructure issue, a precondition not met, a step that was underspecified); `patch` fixes that with minimal churn. `restart` is expensive (re-decompose the entire goal) and `abort` halts everything.
- **Alternative considered:** `restart` as the default for safety (fresh plan every time). Rejected: restarts are disproportionately expensive for small failures, and the fail-closed boundary already prevents a bad patch from reaching an executor (deterministic gates re-run on every patch).
- **Outcome:** `Goal.replan_policy` defaults to `ReplanPolicy.PATCH`. The goal can override via the `replan_policy` field. `replan()` reads `goal.replan_policy` and switches on it: `patch` stamps the next version; `restart` stamps the next version (still preserves lineage); `abort` raises `ReplanAbort`.
- **Consequences:** Every planner must handle a `patch` request (producing a new `PlanVersion` with remaining steps). For manual/reviewer-initiated patches (the escalation patch flow), the CLI supplies the patch directly via `--patch <file>`.

### DD-10 — Escalation precision contract: one resolvable question per escalation

- **Status:** Accepted
- **Context:** §2.1 requires the escalation to present a "minimal precise single question" to the human reviewer. The escalation must be resolvable with a single decision (approve or deny), not a laundry list of open issues.
- **Drivers:** reviewer ergonomics (a single question can be answered in seconds; a list is deferred); actionability (each escalation is a concrete choice, not a status report); fail-closed precision (if an escalation had multiple blockers, the reviewer might only address one — leaving the plan in an inconsistent state).
- **Alternative considered:** Escalations that summarize all open blockers with a multi-part question. Rejected: multi-issue escalations create ambiguity — "approve" might mean "I accept the risk of all blockers" or "I'm overriding only the first one". A single question forces a single decision, and the patch flow handles the case where the reviewer wants to fix one specific blocker without accepting others.
- **Outcome:** The `EscalationManager.create()` enforces:
  1. The escalation's `question` is non-blank.
  2. The escalation references exactly one `blocker_finding_id` (the loop's `_escalate` already picks the first blocker).
  3. No second open escalation is allowed for the same plan (one precise question at a time).

  The store keying by `plan_id` enforces the "one per plan" constraint at the persistence layer. A resolved escalation (approved or denied) is a terminal state — the same escalation cannot be resolved twice.
- **Consequences:** Reviewers see exactly one question per escalation. Complex failures with multiple blockers result in multiple sequential escalations — the first resolved (possibly via patch) may clear the second automatically. The escalation + patch flow replaces the need for multi-issue escalations.

## M5 / M6 Entries

### DD-11 — Adapter gate-not-execute boundary: the adapter serializes for *your* executor, it does not become the executor

- **Status:** Accepted
- **Context:** §2.3 requires the six adapters to gate and serialize approved plans, but never run the plan themselves. The framework's own executor runs the plan; the adapter just ensures it's approved first.
- **Drivers:** separation of concerns (the engine owns approval, the framework owns execution); adaptability (the adapter should work with any executor the framework provides); security (if the adapter became the executor, a bug in the adapter could bypass the approval gate).
- **Alternative considered:** Adapters that wrap the framework's executor, running each step and checking approval internally. Rejected: couples the adapter to the framework's execution model, making it fragile across framework versions.
- **Outcome:** Every adapter calls `Engine.plan(goal)`, caches the `ApprovedPlan`, and gates each step/tool call against the cached plan. The adapter never calls `execute()` or `run()` — it returns the approved plan for the framework's own executor. The re-gate (`check_preconditions`) is advisory (off by default) and the adapter surfaces stale preconditions without blocking execution.
- **Consequences:** Adapters are thin (30–80 lines each) and framework-version-independent. The audit trail records every gate decision. A user who wants the adapter to also execute must wrap it themselves.

### DD-12 — Explain narrative format: templated with reason-code spine

- **Status:** Accepted
- **Context:** CUJ 15 requires the explain narrative to identify the outcome-changing factor from the text alone. The narrative must be ≤10s to render and deterministic.
- **Drivers:** actionability (the reader must understand *why* without reading the plan); speed (deterministic template rendering is instant); determinism (no LLM variance in the explain output).
- **Alternative considered:** LLM-generated narrative (summarize the plan history with a model). Rejected: non-deterministic, slow, expensive, and violates the hermetic CI contract. A templated approach is free, instant, and deterministic.
- **Outcome:** `explain.py` uses `REASON_CODE_DESCRIPTIONS` from `reason_codes.py` as the narrative spine. Each revision's findings are mapped to template sentences: "Revision {N} was revised: {reason}." / "Revision {N} was escalated: {blocker description}." The actionability test asserts that a seeded blocker produces a narrative containing the blocker's description.
- **Consequences:** The explain narrative is always deterministic and zero-cost. Adding a new reason code automatically adds a new narrative template. The explain engine is testable with zero LLM (hermetic).

## M8 Entries

### DD-13 — Host MLX as the benchmark local LLM (deviation from WBS's containerized LLM)

> **Ref:** [D19 — Docker integration design](docker-integration-design.md) (DD-M8-1)

- **Status:** Accepted
- **Context:** The WBS proposed a containerized `llm` service (OMLX/Ollama) in the compose topology. MLX is macOS-only and cannot be containerized; the host already runs `Qwen3.5-9B-MLX-4bit` at `http://127.0.0.1:8000/v1`; the M9 field sweep targets local models regardless of runtime.
- **Drivers:** reuses the proven M7 thinking-mode/truncation transport fix; keeps compose/CI footprint small (two engine services, no model pull); keeps the gate truly free (no GPU in CI).
- **Alternative considered:** Containerized Ollama model service, replicated in CI. Rejected: heavy image/model pulls in CI, GPU-less hosted runners cannot run MLX, and the WBS already permits an opt-in workflow for heavy model images.
- **Outcome:** Compose has exactly two services (`engine-http`, `engine-mcp`). Both reach host MLX through `host.docker.internal:8000/v1`, wired purely via `PC_OMLX_BASE_URL` / `PC_OMLX_MODEL` env — the same image runs against Ollama/vLLM later with zero code change. CI is opt-in via `workflow_dispatch`.
- **Consequences:** The containerized LLM portion of the M8 gate is deliberately re-scoped to "containers + a real local LLM on the host." The real-LLM loop test SKIPs cleanly when the host endpoint is unreachable, keeping the hermetic suite green on non-MLX hosts.

### DD-14 — Container glue wraps existing sprint surfaces; no new server framework

> **Ref:** [D19 — Docker integration design](docker-integration-design.md) (DD-M8-2)

- **Status:** Accepted
- **Context:** M5/M6 shipped transport-agnostic servers: `PlannerCriticHTTPServer.handle_request` + `create_fastapi_app` (HTTP) and `handle_tool`/`list_tools`/`run_stdio` (MCP). The containers need runnable entrypoints, not a second server implementation.
- **Drivers:** reuse; no new HTTP/MCP library dependency; the servers are already thin and framework-independent.
- **Alternative considered:** Introduce FastMCP / a web framework in the runtime image. Rejected: duplicates the existing dispatch logic and bloats the image for no behavioral gain.
- **Outcome:** `engine-http` mounts `create_fastapi_app` under uvicorn (FastAPI is an optional extra); `engine-mcp` exposes the existing `list_tools`/`handle_tool` logic over a minimal HTTP JSON-lines transport so the MCP client test can connect over TCP (stdio is unusable across containers). Both add `/healthz`.
- **Consequences:** The MCP-over-HTTP adapter is a thin shim, unit-testable hermetic-ally; the container tests exercise the same call paths as the CLI/HTTP surfaces.