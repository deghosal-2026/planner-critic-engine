from __future__ import annotations

import pytest

from planner_critic.guardrail import (
    EscalationRequired,
    PreconditionDrift,
    escalate,
    re_gate,
)
from planner_critic.types import Finding, Severity


def test_escalation_required_exception() -> None:
    exc = EscalationRequired("blocked", reason_code="budget_exceeded")
    assert "blocked" in str(exc)
    assert exc.reason_code == "budget_exceeded"
    assert exc.findings == []


def test_escalation_required_with_findings() -> None:
    finding = Finding(
        id="f1", version=1, severity=Severity.BLOCKER,
        reason_code="missing_rollback", message="missing rollback",
    )
    exc = EscalationRequired("blocked", reason_code="gate_failure", findings=[finding])
    assert len(exc.findings) == 1
    assert exc.findings[0].reason_code == "missing_rollback"


def test_precondition_drift_exception() -> None:
    exc = PreconditionDrift("drift detected", precondition_key="db_healthy")
    assert "drift" in str(exc)
    assert exc.precondition_key == "db_healthy"


def test_precondition_drift_default_key() -> None:
    exc = PreconditionDrift("drift detected")
    assert exc.precondition_key == ""


def test_re_gate_raises_precondition_drift() -> None:
    @re_gate(precondition_key="db_healthy")
    def my_step() -> str:
        return "done"

    with pytest.raises(PreconditionDrift) as exc:
        my_step()
    assert "db_healthy" in str(exc.value)


def test_re_gate_function_name_as_key() -> None:
    @re_gate()
    def my_step() -> str:
        return "done"

    with pytest.raises(PreconditionDrift) as exc:
        my_step()
    assert "my_step" in str(exc.value)


def test_re_gate_on_drift_callback() -> None:
    callback_key: list[str] = []

    def on_drift(key: str) -> str:
        callback_key.append(key)
        return "handled"

    @re_gate(precondition_key="auth", on_drift=on_drift)
    def my_step() -> str:
        return "done"

    result = my_step()
    assert result == "handled"
    assert "auth" in callback_key


def test_escalate_decorator_passes_through() -> None:
    def my_handler(reason: str) -> str:
        return f"handled: {reason}"

    decorated = escalate(my_handler)
    assert decorated is my_handler
    result = decorated("test")
    assert result == "handled: test"


def test_escalate_requires_handler() -> None:
    with pytest.raises(TypeError):
        escalate()  # type: ignore[call-arg]


def test_guardrail_dry_run_via_kwargs() -> None:
    @re_gate(precondition_key="test")
    def my_func() -> str:
        return "ok"

    assert my_func.__name__ == "my_func"