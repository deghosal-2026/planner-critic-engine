# Docker Integration Test — Learnings (WBS #82)

> **Date:** 2026-08-19 · **Milestone:** M8 #82 · **Model:** DeepSeek V4 Flash (OpenRouter)

---

## What we built

A containerized real-LLM loop test (`tests/docker/test_loop_real_llm.py`) that
exercises the full engine stack — `docker compose` → `engine-http` (FastAPI) →
LLM provider (OpenRouter) — against two goals:

1. **Adversarial goal** (critical-risk, strict tolerance) — must NEVER approve.
2. **Normal goal** (deploy to staging, balanced tolerance) — must terminate cleanly.

A standalone debug script (`tests/docker/debug_loop.py`) sends a single goal,
pretty-prints the full LLM response, and saves evidence to `docs/test/docker/`.

---

## Key learnings

### 1. LLM preconditions must be specified in the prompt

**Problem:** The LLM returned `"precheck-db passed"` (a string) for the
`preconditions` field instead of a structured `Precondition` object
(`{description, fact, established_by}`).

**Root cause:** The `_PLANNER_SYSTEM_PROMPT` in `cli/plan.py` said
`"optional preconditions"` but never showed the object shape. The LLM guessed.

**Fix:** Updated the prompt to include a precondition object in the example and
an explicit instruction: `"preconditions MUST be objects with description, fact,
established_by fields — NEVER strings."`

**Lesson:** Every structured field in the LLM output must have its shape shown
in the prompt example. Don't assume the model will infer nested object schemas.

### 2. max_tokens=4096 is too low for real plans

**Problem:** The LLM response was truncated (`finish_reason=length`) on plans
with 8+ tasks and detailed rollback/verification fields.

**Fix:** Increased `max_tokens` from 4096 to 16384 in `transport_openai.py`.

**Lesson:** Structured JSON plans are token-heavy. The default 4096 is fine for
unit tests with fake providers but truncates real LLM output. 16384 is a safe
default for v0.1.0.

### 3. The transport had no logging — tests were undebuggable

**Problem:** When a test failed, there was no way to see what the LLM actually
returned. The HTTP server logs only showed `POST /plan 200 OK`.

**Fix:** Added `logging` to `OpenAICompatibleProvider.complete()`:
- `logger.error` on HTTP >= 400 or malformed response (includes raw body)
- `logger.debug` on success (includes model, finish_reason, content preview)

**Lesson:** Every external call must log enough context to debug a failure
without re-running it. The raw response body is the single most useful artifact.

### 4. A standalone debug script is essential

**Problem:** pytest fixtures make LLM calls silently. The test hangs for
minutes with no output, and you can't inspect the response until the fixture
completes (or times out).

**Fix:** Created `tests/docker/debug_loop.py` — sends one goal, prints the full
response, saves evidence. Run it before the test suite to verify the LLM path
works.

**Lesson:** Integration tests against external services need a manual debug
entry point. Don't rely solely on pytest for first-time verification.

### 5. Test assertions must match actual LLM behavior

**Problem:** The original test asserted that the adversarial goal would produce
deterministic gate blocker codes (`missing_verification`, `missing_rollback`).
In reality, the LLM planner produced a plan *with* verification/rollback (passing
the gates), but the LLM critic caught deeper issues
(`llm_unsafe_sequencing`, `llm_weak_rollback`).

**Fix:** Changed the assertion to check for any blocker-severity finding
(regardless of source), not specific gate codes. The invariant is "never
approved," not "blocked by a specific gate."

**Lesson:** Don't over-constrain assertions on LLM behavior. Test the invariant
(the plan is never approved), not the specific path the LLM took to get there.

### 6. Module-scoped fixtures avoid duplicate LLM spend

**Problem:** The original test sent the same goal multiple times (once per test
function), each taking 1-2 minutes and costing tokens.

**Fix:** Module-scoped `adversarial_result` and `normal_result` fixtures make
one LLM call each; all tests in that module assert on the cached body.

**Lesson:** LLM integration tests must cache the response at the widest scope
possible. One call per goal, not one call per assertion.

### 7. Progress output during long fixtures

**Problem:** Module-scoped fixtures that call the LLM hang silently. pytest
shows the test name but no progress.

**Fix:** `_post_plan()` prints to stderr: `"[adversarial] sending POST /plan..."`
and `"[adversarial] done — status=escalated reason=regression_thrashing"`.

**Lesson:** Long-running fixtures must print progress. `print(..., file=sys.stderr,
flush=True)` is the simplest way.

---

## Evidence files

All saved in `docs/test/docker/`:

| File | Contents |
|------|----------|
| `*_debug_adversarial.json` | Full request + response for adversarial goal |
| `*_debug_normal.json` | Full request + response for normal goal |
| `*_adversarial.json` | Test-run evidence for adversarial goal |
| `*_normal_goal.json` | Test-run evidence for normal goal |
| `debug-adversarial.log` | Debug script output (adversarial) |
| `debug-normal.log` | Debug script output (normal) |
| `test-run.log` | pytest output |

---

## Configuration changes made

| File | Change | Why |
|------|--------|-----|
| `docker-compose.yml` | `PC_OMLX_*` → `PC_OPENAI_*` env vars | Support cloud LLM providers (OpenRouter) |
| `src/planner_critic/server/http_serve.py` | `bootstrap_config()` reads `PC_OPENAI_API_KEY` | Pass API key to provider registry |
| `src/planner_critic/llm/transport_openai.py` | `max_tokens` 4096 → 16384 | Prevent truncated plans |
| `src/planner_critic/llm/transport_openai.py` | Added logging | Debug LLM failures |
| `src/planner_critic/cli/plan.py` | Prompt includes precondition shape | LLM returns structured objects |

---

## Round 2 — Core design fixes (the loop never converged with a real LLM)

> **Date:** 2026-08-19 (round 2) · **Provider:** OpenRouter `openai/gpt-4o-mini` + local oMLX `Qwen3.5-9B-MLX-4bit`

### Problem

After round 1 the loop *ran* but never converged with a real LLM:

- **Normal goal** (balanced, deploy-to-staging) escalated with `revision_cap_reached` — never approved.
- **Adversarial goal** (strict, abort) escalated with `regression_thrashing` — false signal.

The loop's termination logic was designed for a **deterministic** critic and broke under LLM non-determinism.

### Root causes + fixes

#### 8. LLM blockers must not be hard blockers under `balanced` tolerance

**Problem:** `resolve_threshold` treated *every* blocker — including LLM critic blockers — as a hard disqualifier under both `strict` and `balanced`. An LLM critic on a non-trivial plan almost always finds *something* (`llm_unsafe_sequencing`, `llm_weak_rollback`, …), so a normal goal could never reach `meets_threshold == True`.

**Fix:** `approval.py` now classifies LLM critic blockers as **acknowledged warnings** under `balanced` (they carry into the approved record), while deterministic-gate blockers remain hard under both tolerances. Under `strict`, LLM blockers still block (fail-closed for high-risk goals). A new `Finding.is_llm_finding` property (`heuristic_family is not None`) is the discriminator.

**Lesson:** Deterministic findings (reproducible, injection-immune) and LLM findings (probabilistic, unbounded) need different weight in the approval decision. Treat gate blockers as law and LLM blockers as advisory under permissive tolerances.

#### 9. Regression/convergence must ignore LLM blocker keys

**Problem:** `regression_detected` fired when the LLM critic flagged a *different* blocker task/reason on revision N than on N-1. With a non-deterministic critic this is normal variance, not thrashing. `circling_blockers` had the mirror problem: it required *identical* blocker sets across revisions, which an LLM almost never produces, so `stalled` degraded to `near_zero_diff` only.

**Fix:** Both `regression.py` and `convergence.py` now key only on **deterministic-gate** blocker keys (`not f.is_llm_finding`). LLM blockers are excluded from regression/stalled detection entirely.

**Lesson:** Termination heuristics that compare finding sets across revisions must filter to the reproducible subset. Comparing non-deterministic sets produces false positives (regression) and false negatives (stalled).

#### 10. `_safe_audit` was raising instead of degrading

**Problem:** The docstring said a critic error maps to an empty list (gates remain the immune layer). The code raised `PlanningError`, killing the loop on any transient LLM failure (timeout, 429, truncation).

**Fix:** `_safe_audit` and `_safe_audit_diff` now `return []` on exception and log a warning. The loop continues with gate findings only.

**Lesson:** Code must match its docstring. The "free, immune layer" promise only holds if a critic failure actually falls back to gates.

#### 11. Truncated responses must be retriable, not terminal

**Problem:** `finish_reason != "stop"` raised `ProviderTimeout` (terminal), and the `StructuredEnforcer` did not wrap `provider.complete()` in try/except, so `ProviderTimeout` propagated without triggering the bounded retry that exists for `BadJSONError`. A single truncation killed the whole planning attempt.

**Fix:** Truncated responses now raise `BadJSONError` (retriable). The enforcer wraps `provider.complete()` in try/except so any `ProviderError` subtype is retried up to `max_retries + 1` times before fail-closed.

**Lesson:** Every retriable failure must raise a `ProviderError` subclass the enforcer catches. `ProviderTimeout` for a non-timeout condition is a misclassification that bypasses retry.

#### 12. MCP and HTTP used different planner prompts

**Problem:** `server/mcp.py` had a 4-line stub `ProviderPlanner` prompt that didn't describe the schema. `cli/plan.py` had the improved prompt with field shapes and the precondition-object rule. MCP goals got garbage plans (`preconditions` as strings); HTTP goals worked.

**Fix:** Deleted `ProviderPlanner` from `mcp.py`; both surfaces now use `_build_roles` / `_CLIPlanner` from `cli/plan.py`.

**Lesson:** Two code paths doing the same job must share one implementation. A stub prompt duplicated from the real one will drift.

#### 13. `replan_policy` was dead config

**Problem:** The goal schema defined `replan_policy: abort|patch|restart`, and the adversarial fixture set `abort`. The loop never read it — a goal with `abort` still entered the revise loop.

**Fix:** `_run` now escalates immediately (`replan_aborted`) when `goal.replan_policy == ABORT` and the threshold is not met, without revising. Added `REPLAN_ABORTED` reason code.

**Lesson:** Every field in the schema must be enforced somewhere, or remove it. Dead config gives users false control.

#### 14. `chat_template_kwargs` is vLLM-specific, not OpenAI-compatible

**Problem:** The transport always sent `chat_template_kwargs: {enable_thinking: False}` — a vLLM/Qwen extension. OpenAI and OpenRouter silently ignore it, but strict OpenAI-compatible servers (Azure) reject it with 400.

**Fix:** Moved to `ProviderSpec.suppress_thinking` (opt-in, default off). The transport's `extra_payload` only includes it when the spec enables it.

**Lesson:** Provider-specific fields don't belong in the default payload. Make them opt-in via config.

#### 15. `len(content)` called before the `isinstance(content, str)` guard

**Problem:** The success log line called `len(content)` before checking `isinstance(content, str)`. A non-string `content` (int) crashed the transport with `TypeError` instead of raising `BadJSONError`.

**Fix:** Reordered: type-check first, log second.

**Lesson:** Guard before you use. Logging order matters.

### Verification (live, OpenRouter `openai/gpt-4o-mini`)

| Goal | Before | After |
|------|--------|-------|
| Adversarial (strict, abort) | `regression_thrashing` (false) | `replan_aborted` — never approved ✓ |
| Normal (balanced) | `revision_cap_reached` (never converged) | `approved` on revision 1 ✓ |

Docker suite: **18 passed, 1 skipped** (the skip was a test bug — wrong response path; fixed). Unit suite: **462 passed**. mypy + ruff clean.

### Round 2 evidence files

| File | Contents |
|------|----------|
| `20260819T234615_debug_adversarial.json` | Adversarial: escalated, `replan_aborted`, 4 findings |
| `20260819T234629_debug_normal.json` | Normal: **approved**, 4 acknowledged warnings |
| `run-adversarial.log` | Debug script output (adversarial, OpenRouter) |
| `run-normal.log` | Debug script output (normal, OpenRouter) |

### Round 2 configuration changes

| File | Change | Why |
|------|--------|-----|
| `src/planner_critic/approval.py` | LLM blockers → warnings under `balanced` | Let normal goals converge |
| `src/planner_critic/types.py` | `Finding.is_llm_finding` property | Discriminate gate vs LLM findings |
| `src/planner_critic/loop/regression.py` | Gate-only blocker keys | Stop false thrashing |
| `src/planner_critic/loop/convergence.py` | Gate-only blocker keys | Make stalled detection meaningful |
| `src/planner_critic/loop/_controller.py` | `_safe_audit` returns `[]` on failure; `replan_policy=abort` escalates | Match docstring; enforce policy |
| `src/planner_critic/llm/transport_openai.py` | Truncation → `BadJSONError`; `extra_payload` opt-in; type-guard order | Retriable failures; strict OpenAI; crash fix |
| `src/planner_critic/llm/structured.py` | Wrap `provider.complete` in try/except | Retry transient provider errors |
| `src/planner_critic/llm/registry.py` | `max_tokens`/`timeout_s`/`suppress_thinking` on `ProviderSpec` | Config-driven transport tuning |
| `src/planner_critic/server/mcp.py` | Use shared `_CLIPlanner` | One prompt, both surfaces |
| `src/planner_critic/server/http.py` | Cache planner/registry/loop_config; gates-only critique without goal | Reuse connections; correct standalone critique |
| `src/planner_critic/cli/plan.py` | `revise` prompt surfaces `suggested_fix` | LLM knows what to change |
| `src/planner_critic/reason_codes.py` | `REPLAN_ABORTED` | Stable code for abort escalation |
