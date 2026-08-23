from __future__ import annotations

from typing import Literal

from planner_critic.cli.diagnose import DIAGNOSTIC_RULES, _diagnose_trace
from planner_critic.types import ExecutionTrace


def _trace(
    task_id: str = "t1",
    failure_class: Literal["planning", "execution"] | None = "planning",
    outcome: str = "missing_rollback",
) -> ExecutionTrace:
    return ExecutionTrace(
        id="trace-1",
        plan_id="plan-1",
        task_id=task_id,
        outcome=outcome,
        failure_class=failure_class,
    )


class TestDiagnose:
    def test_missing_rollback_diagnosis(self) -> None:
        trace = _trace(outcome="missing_rollback")
        diag = _diagnose_trace(trace)
        assert diag["category"] == "precondition.missing_rollback"
        assert diag["severity"] == 4
        assert "rollback" in diag["root_cause"].lower()
        assert diag["suggested_fix"] is not None

    def test_missing_verification_diagnosis(self) -> None:
        trace = _trace(outcome="missing_verification")
        diag = _diagnose_trace(trace)
        assert diag["category"] == "precondition.missing_verification"
        assert diag["severity"] == 3

    def test_transient_network_diagnosis(self) -> None:
        trace = _trace(failure_class="execution", outcome="transient_retry_triggered")
        diag = _diagnose_trace(trace)
        assert diag["category"] == "execution.transient_network"
        assert diag["severity"] == 2

    def test_state_stale_diagnosis(self) -> None:
        trace = _trace(failure_class="execution", outcome="state_view_stale")
        diag = _diagnose_trace(trace)
        assert diag["category"] == "state.snapshot_stale"

    def test_resource_locked_diagnosis(self) -> None:
        trace = _trace(failure_class="execution", outcome="resource_locked_by_concurrent_execution")
        diag = _diagnose_trace(trace)
        assert diag["category"] == "state.resource_locked"
        assert diag["severity"] == 4

    def test_timeout_diagnosis(self) -> None:
        trace = _trace(failure_class="execution", outcome="timeout")
        diag = _diagnose_trace(trace)
        assert diag["category"] == "execution.timeout"

    def test_auth_failure_diagnosis(self) -> None:
        trace = _trace(failure_class="execution", outcome="auth_failure: invalid token")
        diag = _diagnose_trace(trace)
        assert diag["category"] == "execution.authentication"

    def test_permission_denied_diagnosis(self) -> None:
        trace = _trace(failure_class="execution", outcome="permission_denied on resource")
        diag = _diagnose_trace(trace)
        assert diag["category"] == "execution.authorization"

    def test_blast_radius_quota_diagnosis(self) -> None:
        trace = _trace(failure_class="planning", outcome="blast_radius_quota_breach")
        diag = _diagnose_trace(trace)
        assert diag["category"] == "quota.blast_radius"

    def test_unclassified_failure(self) -> None:
        trace = _trace(failure_class="execution", outcome="some_unknown_error")
        diag = _diagnose_trace(trace)
        assert diag["category"] == "unclassified_failure"
        assert diag["severity"] == 1
        assert diag["suggested_fix"] is None

    def test_diagnostic_rules_have_required_fields(self) -> None:
        for rule in DIAGNOSTIC_RULES:
            assert "match" in rule
            assert "category" in rule
            assert "severity" in rule
            assert "root_cause_template" in rule
            assert "suggested_fix_template" in rule

    def test_severity_in_range(self) -> None:
        for rule in DIAGNOSTIC_RULES:
            assert 1 <= rule["severity"] <= 5

    def test_format_human_output(self) -> None:
        from planner_critic.cli.diagnose import _format_human
        trace = _trace(outcome="missing_rollback")
        diag = _diagnose_trace(trace)
        output = _format_human(diag)
        assert "Failing step" in output
        assert "Root cause" in output
        assert "Suggested fix" in output

    def test_format_markdown_output(self) -> None:
        from planner_critic.cli.diagnose import _format_markdown
        trace = _trace(outcome="missing_rollback")
        diag = _diagnose_trace(trace)
        output = _format_markdown(diag)
        assert "## Execution Trace Diagnosis" in output
        assert "| Failing step" in output
        assert "**Root cause:**" in output
