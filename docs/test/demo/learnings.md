# Demo LLM Exercise — Learnings

What the `init → plan` gate run against the local oMLX models (Aug 18) taught us.

## Context

Goal: close the M7 exit-gate item "`init` example goal → `plan` gives immediate
first approved plan" (CUJ 1) against the real CLI + a real local LLM
(oMLX server on `localhost:8000`, OpenAI-compatible transport).

## Phase 1 — Free-form prompt (no schema)

### Expected
The local LLM decomposes the migration goal into a valid PlanVersion; the loop
approves it on revision 1.

### Found

| Model | Response | Result |
|-------|----------|--------|
| `Qwen3.5-4B-4bit` | `[1.1]` (5 bytes) | fails parse — not a JSON object |
| `Qwen3.5-9B-MLX-4bit` | 2297 bytes of plausible JSON | fails `PlanVersion` validation — 19 missing required fields (e.g. `tasks` inside `branches`) |

Both runs: `StructuredEnforcer` retries a bounded number of times, then fails
closed with `PlanningError(planning_unavailable)`. Exit 1.

### Surprise
The 9B model **understood the domain** — it even fixed the seeded flaw (added
backup + verify steps the goal's `_seeded_flaw` said were missing). The failure
was purely schema-shape: `task_id` vs `id`, `rollback` as object vs
`rollback_steps`, etc. The LLM plans well but doesn't emit the exact contract.

## Phase 2 — Schema-in-prompt

Injected `PlanVersion.model_json_schema()` into the system prompt.

### Found
- decompose now produces **valid PlanVersion** (6 tasks, 71.7s) ✅
- Loop ran 3 revisions but didn't converge (2 findings → 5 findings → timeout)
- Each call took 70-90s

### Why so slow?
Discovered via a direct `curl` test: **Qwen3.5 has thinking mode on by default**.
The model spent all its tokens on `"Thinking Process:\n1. Analyze the Request..."`
monologue and hit `finish_reason: length` before producing JSON. That's why the
4B returned `[1.1]` (truncated thinking) and the 9B took 70-90s per call.

## Phase 3 — Transport fixes

Three bugs in `transport_openai.py`:

1. **No `max_tokens`** — oMLX defaults to 300, so thinking ate everything.
2. **No `enable_thinking: false`** — Qwen3.5 thinking mode bloated every call.
3. **60s timeout** — too short for a 9B model even without thinking.

Fixed: `max_tokens=4096`, `enable_thinking=False`, `timeout=180s`.

## Phase 4 — Example-based prompt + transport fixes

Replaced the bloated full-schema prompt with a compact example showing exact
field names + the rollback-on-high-risk pattern.

### Result (completed run, 163.4s)

| Stage | Time | Findings |
|-------|------|----------|
| v1 decompose | 33.2s | 2 deterministic (missing verification on high-risk tasks) |
| v2 revise | 29.2s | 6 LLM critic (weak verification, unsafe sequencing, weak rollback) |
| v3 revise | 52.2s | (hit revision cap) |
| **Result** | | **ESCALATED** (`converged_stalled`), exit 0 |

The engine behaved correctly throughout: valid plans produced, critic findings
surfaced, revision cap hit, escalation raised. No crash, no bad output accepted.

### The plan itself was good
5 tasks: pre-check → backup → migrate → verify → notify. Proper dependencies,
verification steps on all high/critical tasks, rollback actions throughout. The
LLM critic was just too aggressive for the 9B model to fully satisfy in 3
revisions — each revision fixed the previous findings but the critic found new
nuances (weak verification logic, unverified backup integrity, etc.).

## Verdict

**Expected:** `init → plan` produces an approved plan (exit 0, `status=approved`).
**Got:** `init → plan` produced an escalated plan (exit 0, `status=escalated`, reason `converged_stalled`). The loop ran 3 revisions; the LLM critic found new issues each round; the revision cap was hit; the engine escalated instead of approving.
**Gate: NOT PASSED.** The engine behaved correctly (fail-closed via escalation), but no approved plan was produced.

## Key learnings (consolidated)

1. **Thinking mode was the silent killer.** Qwen3.5 defaults to thinking-on;
   without `enable_thinking: false` the model burns its token budget on internal
   monologue and never produces output. This was invisible until a direct `curl`
   test revealed it.
2. **The transport needed `max_tokens`.** Without it, oMLX's 300-token default
   truncated every response. This is a real bug in `transport_openai.py` — fixed.
3. **Example-based prompts beat full JSON schemas.** The full schema (3-6k
   tokens) slowed the model and didn't help it produce valid output. A compact
   example with exact field names was faster and more effective.
4. **The 9B model plans well but can't converge under the strict critic.** Each
   revision fixed the previous findings but the LLM critic found new nuances.
   The loop correctly escalated (`converged_stalled`) rather than accepting a
   flawed plan — fail-closed working as designed.
5. **The hermetic path works; the real-LLM path is hard but functional.**
   `plancritic demo` (scripted roles) reproduces the full loop perfectly. The
   real-LLM path now produces valid plans and runs to completion, but converging
   to approval needs either a stronger model or a less aggressive critic prompt.
6. **M6's CUJ-1 test (#54) is not equivalent to the CLI gate.** It drives the
   Engine with scripted roles; it never exercised the real transport. Closing
   the gate needs an end-to-end LLM run.
7. **Process hygiene.** Logs dumped in the repo root are wrong; artifacts belong
   under `docs/test/demo/`. Per-model responses should be captured on first run,
   not retroactively. Always `curl` the endpoint directly before assuming the
   code is broken.

## Recommendations

1. **The transport fixes are real bug fixes** — commit `max_tokens=4096`,
   `enable_thinking=False`, `timeout=180s` in `transport_openai.py`. These
   benefit every local-LLM user, not just the demo.
2. **Re-scope the M7 gate** — "init → plan gives immediate first approved plan"
   should be hermetic-only for M7. The real-LLM convergence test belongs in M9
   field test, where model-prompt tuning is the actual work.
3. **For M9 field test:** tune the critic prompt to be less aggressive, or raise
   the revision cap, or use a stronger model. The 9B + strict critic + 3-revision
   cap is a convergence trap.
4. **Add an integration test** that goes through the real transport/enforcer, so
   "covered by test" means "works end-to-end."
5. **Record the transport fixes + thinking-mode discovery** in D13 (design
   decisions).

## Open follow-ups

- Commit the `transport_openai.py` fixes (max_tokens, enable_thinking, timeout).
- Decide whether the M7 gate is re-scoped (hermetic) or deferred to M9 field test.
- Optionally record these as a design note in D13 (design decisions).

## Aug 19 follow-up

- Verified the hermetic path is not the problem: `plancritic demo` and the demo
  test files complete quickly.
- Confirmed the remaining "hangs" are real-LLM runs, not loop-controller
  infinite loops. The saved artifacts show both stuck runs stopped at provider
  call boundaries:
  - `demo-run-quickstart.log` stops immediately after `engine.plan starting...`
    which is before the first `planner.decompose()` call returned.
  - `demo-run-schema-prompt.log` stops during the third LLM-backed revise call.
- Confirmed the transport fixes are already in code:
  `max_tokens=4096`, `enable_thinking=False`, `timeout=180s`.
- Added one more fail-closed guard in `transport_openai.py`: when the provider
  returns `finish_reason != "stop"`, PlannerCritic now raises immediately
  instead of treating the response as ordinary content. This closes the observed
  truncation case where the 4B model returned `[1.1]` with `finish_reason=length`.
- Practical conclusion: the loop was not hanging; the local provider was
  returning truncated/stalled completions, and the transport was not surfacing
  truncation early enough.
