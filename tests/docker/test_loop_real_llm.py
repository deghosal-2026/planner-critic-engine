"""Containerized real-LLM loop smoke test (WBS #82).

A **minimal** smoke test that sends one adversarial goal to the containerized
engine and asserts the fail-closed invariant: a critical-risk plan under strict
tolerance is never approved.

This is deliberately NOT a comprehensive behavioral test. The real-LLM loop is
non-deterministic and slow (1-3 min per call), so this test checks only the one
stable invariant that matters: fail-closed. Deep behavioral assertions live in
the hermetic unit tests (``test_loop_matrix.py``) and the manual evidence
workflow (``debug_loop.py``).

Running:
    # Start compose with a cloud LLM provider:
    PC_OPENAI_API_KEY=sk-... docker compose up -d

    # Run this smoke test:
    PC_INTEGRATION=1 python3 -m pytest tests/docker/test_loop_real_llm.py -v -s --no-cov

    # For full LLM response inspection (not pytest):
    python3 tests/docker/debug_loop.py adversarial
    python3 tests/docker/debug_loop.py normal

Evidence:
    The full response is saved to docs/test/docker/ as timestamped JSON.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import httpx
import pytest

BASE = "http://localhost:8080"
DX = Path(__file__).parent / "fixtures"
LOG_DIR = Path(__file__).resolve().parents[2] / "docs" / "test" / "docker"

# Per-request timeout: 5 minutes. The LLM loop may revise up to 3 times.
REQUEST_TIMEOUT = 300.0


def _load(name: str) -> dict[str, Any]:
    """Load a JSON fixture from tests/docker/fixtures/."""
    return cast("dict[str, Any]", json.loads((DX / name).read_text()))


def _save_evidence(label: str, goal: dict[str, Any], body: dict[str, Any]) -> None:
    """Save request + response as timestamped JSON evidence."""
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    record = {
        "timestamp": ts,
        "label": label,
        "request": {"goal": goal},
        "response": body,
    }
    out = LOG_DIR / f"{ts}_{label}.json"
    out.write_text(json.dumps(record, indent=2, sort_keys=True))


def _post_plan(goal: dict[str, Any], label: str) -> dict[str, Any]:
    """Send a goal to POST /plan, save evidence, return the response body.

    Prints progress to stderr so the test doesn't appear to hang silently.
    Fails immediately on HTTP errors rather than waiting for a timeout.

    Args:
        goal: The goal dict to send.
        label: Label for evidence filename and progress output.

    Returns:
        The parsed response body.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    print(
        f"\n  [{label}] POST /plan to {BASE} (timeout={REQUEST_TIMEOUT}s)...",
        file=sys.stderr,
        flush=True,
    )
    try:
        r = httpx.post(f"{BASE}/plan", json=goal, timeout=REQUEST_TIMEOUT)
    except httpx.TimeoutException:
        pytest.fail(
            f"LLM request timed out after {REQUEST_TIMEOUT}s. "
            f"Check: docker compose logs engine-http --tail=50"
        )
    except httpx.HTTPError as err:
        pytest.fail(f"HTTP error: {err}")

    print(f"  [{label}] HTTP {r.status_code}", file=sys.stderr, flush=True)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:500]}"

    body = r.json()
    _save_evidence(label, goal, body)

    if body.get("status") != 200:
        pytest.fail(f"engine returned error: {json.dumps(body, indent=2)}")

    data = body["data"]
    print(
        f"  [{label}] done — status={data.get('status')} "
        f"reason={data.get('reason_code')} "
        f"findings={len(data.get('findings', []))}",
        file=sys.stderr,
        flush=True,
    )
    return cast("dict[str, Any]", data)


# ---------------------------------------------------------------------------
# Smoke test — fail-closed invariant on the adversarial goal
# ---------------------------------------------------------------------------


def test_adversarial_goal_never_approved() -> None:
    """A critical-risk goal under strict tolerance is NEVER approved.

    This is the fail-closed invariant (F-73). The LLM planner may produce a
    valid plan, the deterministic gates may pass, but the loop must escalate
    (never approve) when blockers remain under strict tolerance.

    This test sends ONE request and asserts ONE invariant. Deep behavioral
    coverage lives in hermetic tests and the debug script.
    """
    goal = _load("adversarial_goal.json")
    data = _post_plan(goal, "adversarial")

    # The one invariant that matters: never approved.
    assert data["status"] == "escalated", (
        f"FAIL-CLOSED BROKEN: adversarial goal was approved!\n"
        f"  reason_code: {data.get('reason_code')}\n"
        f"  findings: {len(data.get('findings', []))} finding(s)\n"
        f"  evidence in: {LOG_DIR}\n"
        f"  debug: python3 tests/docker/debug_loop.py adversarial"
    )
    assert data["reason_code"] != "approved"

    # Sanity: an escalated result should have at least one finding.
    assert len(data.get("findings", [])) > 0, "escalated with zero findings — unexpected"


# ---------------------------------------------------------------------------
# Health check — compose topology is responsive
# ---------------------------------------------------------------------------


def test_engine_healthz() -> None:
    """Engine health endpoint responds — compose topology is healthy."""
    r = httpx.get(f"{BASE}/healthz", timeout=10.0)
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
