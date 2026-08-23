# OMLX Real-LLM Field Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add opt-in **field tests** that exercise the full critique loop against a real **local OMLX** LLM, covering all three critique strategies: **all heuristic** (gates only), **LLM + heuristic** (deterministic-first), and **all LLM** (llm-every-revision). Field tests do **not** run in CI — they are a local-model release sweep (see WBS M9).

**Architecture:** These tests are *opt-in and hermetic-safe*: they skip by default and only run when a local OMLX endpoint is configured via `PC_OMLX_BASE_URL`. They drive the real `OpenAICompatibleProvider` + `LLMCritic` + loop against a live local model, asserting a seeded goal flaw is surfaced as a blocker. A `heuristic-only` critique mode is added so "gates only, no LLM" is a first-class, testable strategy (today the engine only has `deterministic-first` and `llm-every-revision`).

**Tech Stack:** Python 3.12, pytest (+ markers + fixture-based gating), httpx (already a dep), `OpenAICompatibleProvider`, `LLMCritic`, `run_loop`, OMLX OpenAI-compatible endpoint.

## Global Constraints

- Field tests do **not** run in CI. They are skipped unless `PC_OMLX_BASE_URL` is set, and executed as part of the local-model field sweep (M9) — see issues #74, #75, #76. (The **containerized** twin of these three modes — a reproducible local LLM running in Docker with the engine's CLI/HTTP/MCP surfaces — is tracked separately in WBS M8 `test_loop_real_llm.py`, issue #82.)
- Hermetic default: `python -m pytest` MUST NOT require a network or a running LLM. Field-test files are skipped unless `PC_OMLX_BASE_URL` is set.
- No paid LLM, ever: the field tests only hit a locally configured OMLX endpoint.
- Same repo conventions: strict mypy on `src/`, ruff clean, coverage gate `--cov-fail-under=95`, milestone names never used in file/document names.
- Reuse existing seams: `OpenAICompatibleProvider`, `LLMCritic`, `run_loop`; do NOT add a new transport.
- Coverage: field-test files must not be required to reach 95% in the default (hermetic) run; they are excluded from the mandatory coverage threshold.

---

## File Structure

- **Modify:** `src/planner_critic/critique/mode.py` — add `heuristic-only` as a third `CriticMode`; `should_invoke_llm` returns always-False for it; `validate_mode` accepts it.
- **Modify:** `src/planner_critic/loop/_controller.py` — no change needed: `should_invoke_llm` already gates the audit call; `heuristic-only` flowing through it means gates only.
- **Modify:** `src/planner_critic/critique/__init__.py` — re-export unchanged (CriticMode already exported).
- **Create:** `tests/test_omlx_field_test.py` — opt-in real-LLM tests for the three modes.
- **Create:** `tests/test_mode_heuristic_only.py` (or extend `tests/test_critique.py`) — unit tests for the new `heuristic-only` mode.
- **Modify:** `pyproject.toml` — register `omlx` pytest marker; add the coverage omission for the opt-in file.

---

### Task 1 — Add the `heuristic-only` critique mode (gates only, no LLM)

**Files:**
- Modify: `src/planner_critic/critique/mode.py`
- Test: `tests/test_critique.py` (append the mode tests)

**Interfaces:**
- Consumes: `Finding`, `Severity` (existing).
- Produces: `CriticMode` extended to `Literal["heuristic-only", "deterministic-first", "llm-every-revision"]`; `should_invoke_llm("heuristic-only", _) -> False`; `validate_mode("heuristic-only")` accepted.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_critique.py`:

```python
def test_heuristic_only_never_invokes_llm() -> None:
    """heuristic-only mode never calls the LLM, even with no gate blockers."""
    assert should_invoke_llm("heuristic-only", []) is False
    assert should_invoke_llm("heuristic-only", [_b_finding()]) is False


def test_validate_mode_accepts_heuristic_only() -> None:
    """validate_mode accepts the new heuristic-only mode."""
    assert validate_mode("heuristic-only") == "heuristic-only"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_critique.py -k heuristic -v`
Expected: FAIL (mypy/type-level: `"heuristic-only"` not in `CriticMode`; runtime: `validate_mode` raises `ValueError`).

- [ ] **Step 3: Implement the mode**

Edit `src/planner_critic/critique/mode.py`:

```python
CriticMode = Literal[
    "heuristic-only", "deterministic-first", "llm-every-revision"
]


def should_invoke_llm(mode: CriticMode, findings: list[Finding]) -> bool:
    if mode == "llm-every-revision":
        return True
    if mode == "heuristic-only":
        return False
    return not any(f.severity is Severity.BLOCKER for f in findings)
```

And in `validate_mode`, add `"heuristic-only": "heuristic-only"` to the `known` dict.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_critique.py -k heuristic -v`
Expected: PASS.

- [ ] **Step 5: Run full suite + lint + mypy + commit**

```bash
pytest -q
ruff check src tests
mypy src
git add src/planner_critic/critique/mode.py tests/test_critique.py
git commit -m "feat(critique): add heuristic-only mode (gates only, no LLM)"
```

---

### Task 2 — Register the `omlx` marker and exclude the opt-in file from the coverage gate

**Files:**
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: none.
- Produces: pytest recognizes `@pytest.mark.omlx`; the opt-in file is excluded from the 95% coverage gate so hermetic runs stay green.

- [ ] **Step 1: Edit `pyproject.toml`**

In `[tool.pytest.ini_options]` add a markers line, and in `[tool.coverage.run]` omit the file:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --cov=planner_critic --cov-fail-under=95"
markers = ["omlx: field test requiring a real local OMLX LLM (skipped unless PC_OMLX_BASE_URL is set; does not run in CI)"]

[tool.coverage.run]
branch = true
source = ["planner_critic"]
omit = [
    "src/planner_critic/_cli.py",
    "tests/test_omlx_field_test.py",
]
```

- [ ] **Step 2: Verify**

Run: `python -m pytest -q`
Expected: all previous tests still pass; a bare `pytest --markers` lists `omlx`.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "test: register omlx marker, exclude opt-in field-test file from coverage gate"
```

---

### Task 3 — Opt-in fixture + the three real-LLM critique-loop tests

**Files:**
- Create: `tests/test_omlx_field_test.py`

**Interfaces:**
- Consumes: `PC_OMLX_BASE_URL` env var (required); `OpenAICompatibleProvider`, `LLMCritic`, `run_loop`, `LoopConfig`, `make_goal`, `ScriptedPlanner`, `approval`, `Finding/Severity`.
- Produces: three pytest tests, each gated on the `omlx` marker + a fixture that skips when `PC_OMLX_BASE_URL` is unset.

- [ ] **Step 1: Write the file**

```python
"""Real local OMLX field tests (opt-in, hermetic-safe, not run in CI).

These exercise the full critique loop against a real local model. They are
SKIPPED unless ``PC_OMLX_BASE_URL`` is set (default hermetic CI never runs
them). Coverage is excluded via pyproject so the default 95% gate is green.

Three critique strategies are covered:
  - all heuristic   (mode="heuristic-only")       -> gates only, no LLM
  - LLM + heuristic (mode="deterministic-first")  -> gates then LLM
  - all LLM         (mode="llm-every-revision")   -> LLM on every revision
"""

from __future__ import annotations

import os

import pytest

from conftest import ScriptedPlanner, make_goal, make_plan, make_task
from planner_critic.critique import LLMCritic
from planner_critic.llm.transport_openai import OpenAICompatibleProvider
from planner_critic.loop import LoopConfig, run_loop

OMLX_URL = os.environ.get("PC_OMLX_BASE_URL", "")
OMLX_MODEL = os.environ.get("PC_OMLX_MODEL", "llama3.2")


def _require_omlx() -> None:
    """Skip unless a local OMLX endpoint is configured."""
    if not OMLX_URL:
        pytest.skip("PC_OMLX_BASE_URL not set; skipping real-LLM field test")


def _provider() -> OpenAICompatibleProvider:
    """A provider pointed at the configured local OMLX endpoint (no key)."""
    return OpenAICompatibleProvider(
        name="omlx", base_url=OMLX_URL, model=OMLX_MODEL, timeout=120.0
    )


def _risky_plan(goal_id: str) -> make_plan:
    """A single high-risk task with NO verification/rollback: a gate blocker.

    ``risk_class="critical"`` plus no ``verification``/``rollback`` triggers
    the ``missing_verification`` and ``missing_rollback`` deterministic gates,
    so ``heuristic-only`` must block it without any LLM involvement.
    """
    return make_plan(
        plan_id="omlx-plan",
        goal_id=goal_id,
        version=1,
        tasks=[make_task("t1", risk_class="critical")],
    )


@pytest.mark.omlx
@pytest.mark.parametrize(
    "mode",
    ["heuristic-only", "deterministic-first", "llm-every-revision"],
    ids=["all-heuristic", "llm-plus-heuristic", "all-llm"],
)
def test_critique_loop_three_modes(mode: str) -> None:
    """The full loop runs over a real OMLX model in each of the three modes."""
    _require_omlx()
    goal = make_goal(
        goal_id="omlx-" + mode,
        tolerance="strict",
    )
    plan = _risky_plan(goal.id)
    planner = ScriptedPlanner([plan] * 3)  # deterministic fake planner

    critic = LLMCritic(goal=goal, provider=_provider())
    config = LoopConfig(mode=mode, revision_cap=2)

    result = run_loop(goal, planner, critic, config=config)

    # strict tolerance + a critical-risk task with no safety steps must NEVER
    # approve; it must escalate (to a human) in every mode.
    assert result.status == "escalated", result
```

- [ ] **Step 2: Run with OMLX configured**

Run: `PC_OMLX_BASE_URL=http://127.0.0.1:PORT/v1 python -m pytest tests/test_omlx_field_test.py -v`
Expected: three tests run and pass against the local model.

- [ ] **Step 3: Run hermetic (unset) to confirm skip**

Run: `python -m pytest tests/test_omlx_field_test.py -v`
Expected: three tests **skipped**, not failed.

- [ ] **Step 4: Commit**

```bash
git add tests/test_omlx_field_test.py
git commit -m "test: add opt-in OMLX real-LLM field tests for the three critique modes"
```

---

## Self-Review

- **Spec coverage:** all three modes (all-heuristic / LLM+heuristic / all-LLM) are covered by Task 3's parametrized test; `heuristic-only` mode existence is covered by Task 1 + used by Task 3; hermetic-safety by Task 2's marker+omit + Task 3's skip guard.
- **Placeholder scan:** the Task 3 code block intentionally contains a `...` note — this must be filled with a concrete `ScriptedPlanner`/`PlanVersion` fixture before execution. The Task 3 body calls `make_goal(... tolerance="strict")` and `_provider`; ensure the `blood_radius`/`risk_class` on the scripted plan is `critical` so `heuristic-only` yields a gate blocker (`missing_verification`) independent of the LLM.
- **Lint/coverage:** files added under `tests/` are S101-exempt per existing config; the opt-in file is coverage-omitted so the default gate stays green when skipped.