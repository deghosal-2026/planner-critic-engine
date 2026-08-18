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