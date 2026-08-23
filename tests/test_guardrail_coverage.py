"""Coverage tests for guardrail.py — decorators and helpers."""

from __future__ import annotations

import pytest

from planner_critic.guardrail import EscalationRequired, PreconditionDrift, _make_goal, escalate


def test_escalation_required() -> None:
    e = EscalationRequired("blocked", reason_code="no_approval")
    assert str(e) == "blocked"
    assert e.reason_code == "no_approval"
    assert e.findings == []


def test_escalation_required_with_findings() -> None:
    from planner_critic.types import Finding, Severity

    f = Finding(
        id="f1",
        version=1,
        severity=Severity.BLOCKER,
        reason_code="missing_rollback",
        message="no rollback",
    )
    e = EscalationRequired("blocked", reason_code="gate_violation", findings=[f])
    assert len(e.findings) == 1
    assert e.findings[0].reason_code == "missing_rollback"


def test_precondition_drift() -> None:
    d = PreconditionDrift("precondition lost", precondition_key="db_healthy")
    assert str(d) == "precondition lost"
    assert d.precondition_key == "db_healthy"


def test_make_goal_balanced() -> None:
    from planner_critic.schema.goal import RiskTolerance

    goal = _make_goal("test goal", "balanced", None)
    assert goal.description == "test goal"
    assert goal.risk_tolerance is RiskTolerance.BALANCED


def test_make_goal_strict() -> None:
    from planner_critic.schema.goal import RiskTolerance

    goal = _make_goal("strict goal", "strict", None)
    assert goal.risk_tolerance is RiskTolerance.STRICT


def test_make_goal_with_constraints() -> None:
    goal = _make_goal("budgeted goal", "balanced", {"max_calls": 5, "env": "prod"})
    assert goal.description == "budgeted goal"


def test_escalate_decorator() -> None:
    def handler() -> str:
        return "handled"

    wrapped = escalate(handler)
    assert wrapped is handler
    assert wrapped() == "handled"


def test_escalate_decorator_no_args_raises() -> None:
    with pytest.raises(TypeError):
        escalate(None)


def test_get_docstring() -> None:
    from planner_critic.guardrail import _get_docstring

    def foo() -> None:
        """Some docstring."""

    assert _get_docstring(foo) == "Some docstring."


def test_get_docstring_none() -> None:
    from planner_critic.guardrail import _get_docstring

    def bar() -> None:
        pass

    assert _get_docstring(bar) is None


def test_re_gate_no_ledger_raises() -> None:
    from planner_critic.guardrail import re_gate

    @re_gate()
    def my_func() -> str:
        return "executed"

    with pytest.raises(PreconditionDrift):
        my_func()


def test_re_gate_no_ledger_callback() -> None:
    from planner_critic.guardrail import re_gate

    @re_gate(on_drift=lambda pk: f"drift:{pk}")
    def my_func() -> str:
        return "executed"

    assert my_func() == "drift:my_func"


def test_re_gate_with_ledger_satisfied() -> None:
    from planner_critic.guardrail import re_gate

    class FakeLedger:
        def read(self, pk: str) -> dict[str, object] | None:
            return {"satisfied": True}

    @re_gate(ledger=FakeLedger())
    def my_func() -> str:
        return "executed"

    assert my_func() == "executed"


def test_re_gate_with_ledger_unsatisfied() -> None:
    from planner_critic.guardrail import re_gate

    class FakeLedger:
        def read(self, pk: str) -> dict[str, object] | None:
            return {"satisfied": False}

    @re_gate(ledger=FakeLedger())
    def my_func() -> str:
        return "executed"

    with pytest.raises(PreconditionDrift):
        my_func()


def test_re_gate_with_ledger_missing_key() -> None:
    from planner_critic.guardrail import re_gate

    class FakeLedger:
        def read(self, pk: str) -> dict[str, object] | None:
            return None

    @re_gate(precondition_key="custom_key", ledger=FakeLedger())
    def my_func() -> str:
        return "executed"

    with pytest.raises(PreconditionDrift):
        my_func()


def test_re_gate_with_ledger_satisfied_callback() -> None:
    from planner_critic.guardrail import re_gate

    class FakeLedger:
        def read(self, pk: str) -> dict[str, object] | None:
            return {"satisfied": True}

    @re_gate(ledger=FakeLedger(), on_drift=lambda pk: f"drift:{pk}")
    def my_func() -> str:
        return "executed"

    assert my_func() == "executed"
