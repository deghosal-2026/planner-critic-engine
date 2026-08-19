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
