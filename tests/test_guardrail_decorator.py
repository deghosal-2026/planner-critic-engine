"""Coverage tests for guardrail.py — @guardrail decorator paths."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from planner_critic.guardrail import EscalationRequired, guardrail
from planner_critic.types import Finding, Severity


def test_guardrail_approved_executes_func() -> None:
    """When the engine approves, the decorated function runs."""
    fake_result = MagicMock()
    fake_result.is_approved = True
    fake_result.reason_code = ""
    fake_result.findings = []

    with patch("planner_critic.guardrail._make_engine") as mock_engine:
        mock_engine.return_value.plan.return_value = fake_result
        @guardrail(goal="test goal")
        def my_func() -> str:
            return "executed"
        assert my_func() == "executed"


def test_guardrail_escalated_raises() -> None:
    """When the engine escalates, EscalationRequired is raised."""
    fake_result = MagicMock()
    fake_result.is_approved = False
    fake_result.reason_code = "budget_exceeded"
    fake_result.findings = []

    with patch("planner_critic.guardrail._make_engine") as mock_engine:
        mock_engine.return_value.plan.return_value = fake_result
        @guardrail(goal="test goal")
        def my_func() -> str:
            return "should not run"
        with pytest.raises(EscalationRequired) as exc:
            my_func()
        assert "budget_exceeded" in str(exc.value)
        assert exc.value.reason_code == "budget_exceeded"


def test_guardrail_dry_run_executes_despite_escalation() -> None:
    """In dry_run mode, the function runs even when escalated."""
    fake_result = MagicMock()
    fake_result.is_approved = False
    fake_result.reason_code = "converged_stalled"
    fake_result.findings = []

    with patch("planner_critic.guardrail._make_engine") as mock_engine:
        mock_engine.return_value.plan.return_value = fake_result
        @guardrail(goal="test goal", dry_run=True)
        def my_func() -> str:
            return "ran anyway"
        assert my_func() == "ran anyway"


def test_guardrail_on_escalate_callback() -> None:
    """When on_escalate is provided, it is called instead of raising."""
    fake_result = MagicMock()
    fake_result.is_approved = False
    fake_result.reason_code = "revision_cap_reached"
    fake_result.findings = [
        Finding(id="f1", version=1, severity=Severity.BLOCKER,
                reason_code=cast("Any", "missing_rollback"),
                message="no rollback"),
    ]

    callback_results: list[tuple[str, list[Finding]]] = []

    def handler(reason: str, findings: list[Finding]) -> str:
        callback_results.append((reason, findings))
        return "handled"

    with patch("planner_critic.guardrail._make_engine") as mock_engine:
        mock_engine.return_value.plan.return_value = fake_result
        @guardrail(goal="test", on_escalate=handler)
        def my_func() -> str:
            return "should not run"
        result = my_func()
        assert result == "handled"
        assert len(callback_results) == 1
        assert callback_results[0][0] == "revision_cap_reached"
        assert len(callback_results[0][1]) == 1


def test_guardrail_uses_docstring_as_goal() -> None:
    """When goal is None, the function's docstring is used."""
    fake_result = MagicMock()
    fake_result.is_approved = True
    fake_result.reason_code = ""
    fake_result.findings = []

    with patch("planner_critic.guardrail._make_engine") as mock_engine:
        mock_engine.return_value.plan.return_value = fake_result

        @guardrail()
        def my_func() -> str:
            """My docstring goal."""
            return "ok"

        assert my_func() == "ok"


def test_guardrail_preserves_function_name() -> None:
    """The decorator preserves the wrapped function's name."""
    fake_result = MagicMock()
    fake_result.is_approved = True
    fake_result.reason_code = ""
    fake_result.findings = []

    with patch("planner_critic.guardrail._make_engine") as mock_engine:
        mock_engine.return_value.plan.return_value = fake_result

        @guardrail(goal="test")
        def my_named_func() -> str:
            return "ok"

        assert my_named_func.__name__ == "my_named_func"
