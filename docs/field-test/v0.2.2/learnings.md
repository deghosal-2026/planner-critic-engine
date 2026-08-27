# Field Test Learnings — v0.2.2

> **Date:** 2026-08-27 · **Status:** In progress
> **Predecessor:** [v0.2.1 field test results](../v0.2.1/field-test-results-0.2.1.md)

---

## L-1: `restores_state` field breaks LLM planner output

**Discovered:** 2026-08-27 during P2 goals sweep (acc-01, acc-02)

**Symptom:** Two accessibility goals (acc-01-wcag-remediation, acc-02-a11y-enforcement) failed with `planning_unavailable`. The LLM planner produced valid JSON but Pydantic validation rejected it.

**Root cause:** The `restores_state` field on `RollbackStep` (added in #245) is typed as `list[str] | None`. The LLM doesn't know the schema and returns a plain string (e.g., `"restore components to pre-fix state"`) instead of a list (`["restore components to pre-fix state"]`). Pydantic's strict validation rejects the string, causing the plan to fail validation after 3 retry attempts.

**Impact:** Any goal where the LLM planner generates a rollback step with `restores_state` as a string instead of a list will fail. This affects all goals, not just accessibility — it's luck of the draw which goals trigger it based on LLM output.

**Fix:** Add a Pydantic field validator on `RollbackStep.restores_state` that coerces a string to a single-element list: `"foo"` → `["foo"]`. This makes the field lenient for LLM-produced plans while keeping the typed contract for code-produced plans.

**Lesson:** New optional schema fields must be lenient about LLM-produced values. The LLM doesn't read the schema definition — it infers the format from the prompt. A `list[str]` field will often be produced as a plain string by the LLM. Either:
1. Add a validator that coerces string → list (preferred for backward compatibility)
2. Or type the field as `str | list[str] | None` and handle both in the gate

---

## L-2: Docker LLM-dependent tests are impractical for local MLX

**Discovered:** 2026-08-27 during M5 Docker integration test (#266)

**Symptom:** Docker tests that require an LLM provider (test_adversarial_goal_never_approved, test_rpc_plan_vs_mlx, test_plan_vs_mlx, test_critique_vs_mlx) either hang for minutes (local MLX is slow) or fail with auth errors (OpenRouter key not in Docker env).

**Root cause:** The Docker container runs isolated from the host. Local MLX on port 8000 is accessible via `host.docker.internal:8000`, but the 9B model is too slow for the 300s timeout, and the 4B model can't produce valid structured JSON (known F-09 limitation).

**Fix:** Disabled all LLM-dependent Docker tests with `@pytest.mark.skip`. The Docker tests now cover infrastructure only (build, health, CLI, HTTP, MCP wiring, escalation). LLM coverage is in the M5 field test sweep ($0.49, 170 goals).

**Lesson:** Docker integration tests should test infrastructure, not LLM behavior. LLM behavior is non-deterministic, slow, and model-dependent — it belongs in the field test sweep, not in the Docker test suite.

---

## L-3: `run-field.py` was hardcoded to v0.2.1 results path

**Discovered:** 2026-08-27 during P2 goals sweep

**Symptom:** Running `run-field.py --goals-sweep --goals ...` without `--output` wrote results to `results/0.2.1/` instead of `results/0.2.2/`.

**Root cause:** `RESULTS_ROOT` constant in `run-field.py` was hardcoded to `REPO_ROOT / "results" / "0.2.1"`. The `--output` flag overrides this, but the default was wrong.

**Fix:** Updated `RESULTS_ROOT` to `REPO_ROOT / "results" / "0.2.2"`.

**Lesson:** Version-specific paths should not be hardcoded in shared scripts. Either parameterize the version or derive it from `__version__`.

---

## L-4: Benchmark scripts were scattered across versioned directories

**Discovered:** 2026-08-27 during M5 setup

**Symptom:** Benchmark scripts lived under `docs/field-test/v0.2.1/scripts/` and `docs/field-test/v0.2.2/scripts/`, making it unclear which to use.

**Fix:** Moved all benchmark scripts to the central `docs/field-test/scripts/` directory. Versioned directories under `docs/field-test/` now contain only results documents (field-test-plan.md, field-test-results.md), not scripts.

**Lesson:** Scripts are code, not documentation. They should live in one place. Results are data — those go in versioned directories.
