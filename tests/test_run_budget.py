from __future__ import annotations

import time

from planner_critic.run_budget import FailureClass, ReplanClassifier, RunBudget
from planner_critic.types import ExecutionTrace


class TestRunBudget:
    def test_no_ceilings_no_block(self) -> None:
        budget = RunBudget()
        assert budget.check() is None

    def test_spend_exceeds_ceiling(self) -> None:
        budget = RunBudget(run_max_budget_usd=1.0)
        budget.record_spend(0.5)
        assert budget.check() is None
        budget.record_spend(0.6)
        assert budget.check() == "run_budget_exceeded"

    def test_depth_exceeds_ceiling(self) -> None:
        budget = RunBudget(run_max_depth=2)
        budget.record_replan()
        budget.record_replan()
        assert budget.check() is None
        budget.record_replan()
        assert budget.check() == "run_depth_exceeded"

    def test_timeout(self) -> None:
        budget = RunBudget(run_max_time=0.01)
        time.sleep(0.02)
        assert budget.check() == "run_timeout"

    def test_no_timeout_within_limit(self) -> None:
        budget = RunBudget(run_max_time=60.0)
        assert budget.check() is None

    def test_exceeded_latches_first_failure(self) -> None:
        budget = RunBudget(run_max_budget_usd=1.0)
        budget.record_spend(2.0)
        assert budget.check() == "run_budget_exceeded"

    def test_exceeded_property(self) -> None:
        budget = RunBudget(run_max_budget_usd=0.5)
        assert budget.exceeded is None
        budget.record_spend(1.0)
        assert budget.exceeded == "run_budget_exceeded"


class TestReplanClassifier:
    def test_transient_error_returns_transient(self) -> None:
        classifier = ReplanClassifier()
        trace = ExecutionTrace(
            id="trace-1",
            plan_id="plan-1",
            task_id="task-1",
            outcome="timeout",
        )
        assert classifier.classify(trace) is FailureClass.TRANSIENT

    def test_deterministic_error_returns_deterministic(self) -> None:
        classifier = ReplanClassifier()
        trace = ExecutionTrace(
            id="trace-1",
            plan_id="plan-1",
            task_id="task-1",
            outcome="precondition_drift",
        )
        assert classifier.classify(trace) is FailureClass.DETERMINISTIC

    def test_ambiguous_error_returns_ambiguous(self) -> None:
        classifier = ReplanClassifier()
        trace = ExecutionTrace(
            id="trace-1",
            plan_id="plan-1",
            task_id="task-1",
            outcome="unknown_error_42",
        )
        assert classifier.classify(trace) is FailureClass.AMBIGUOUS

    def test_step_retry_budget_exceeded(self) -> None:
        classifier = ReplanClassifier(step_max_retries=2)
        for _ in range(3):
            trace = ExecutionTrace(
                id="trace-x",
                plan_id="plan-1",
                task_id="task-1",
                outcome="timeout",
            )
            classifier.classify(trace)
        assert classifier.check_step_retry_exceeded("task-1")

    def test_step_retry_within_budget(self) -> None:
        classifier = ReplanClassifier(step_max_retries=3)
        for _ in range(2):
            trace = ExecutionTrace(
                id="trace-x",
                plan_id="plan-1",
                task_id="task-1",
                outcome="timeout",
            )
            classifier.classify(trace)
        assert not classifier.check_step_retry_exceeded("task-1")

    def test_transient_becomes_ambiguous_after_budget(self) -> None:
        classifier = ReplanClassifier(step_max_retries=1)
        results: list[FailureClass] = []
        for _ in range(2):
            trace = ExecutionTrace(
                id="trace-x",
                plan_id="plan-1",
                task_id="task-1",
                outcome="rate_limit",
            )
            results.append(classifier.classify(trace))
        assert results[-1] is FailureClass.AMBIGUOUS

    def test_transient_codes(self) -> None:
        for code in [
            "timeout",
            "rate_limit",
            "network_error",
            "connection_reset",
            "service_unavailable",
            "429",
            "503",
        ]:
            classifier = ReplanClassifier()
            trace = ExecutionTrace(
                id="trace-x",
                plan_id="plan-1",
                task_id="task-1",
                outcome=code,
            )
            assert classifier.classify(trace) is FailureClass.TRANSIENT, (
                f"{code} should be transient"
            )

    def test_deterministic_codes(self) -> None:
        for code in [
            "precondition_drift",
            "schema_mismatch",
            "missing_dependency",
            "invalid_config",
            "auth_failure",
            "permission_denied",
            "not_found",
        ]:
            classifier = ReplanClassifier()
            trace = ExecutionTrace(
                id="trace-x",
                plan_id="plan-1",
                task_id="task-1",
                outcome=code,
            )
            assert classifier.classify(trace) is FailureClass.DETERMINISTIC, (
                f"{code} should be deterministic"
            )
