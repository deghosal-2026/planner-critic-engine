from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from planner_critic.schema.plan import PlanVersion, RiskClass, Task


def _simple_plan() -> PlanVersion:
    t = Task(id="t1", description="deploy", action="deploy", target="api", risk_class=RiskClass.LOW)
    return PlanVersion(id="plan-1", goal_id="goal-1", version=1, tasks=[t], dependencies=[])


def test_check_cli_accepts_valid_plan() -> None:
    from planner_critic.cli.check import run_check
    with tempfile.TemporaryDirectory() as tmp:
        plan_path = Path(tmp) / "plan.json"
        plan_path.write_text(_simple_plan().model_dump_json())
        code = run_check([str(plan_path)])
        assert code in (0, 1)


def test_check_cli_rejects_missing_plan() -> None:
    from planner_critic.cli.check import run_check
    code = run_check(["/nonexistent/plan.json"])
    assert code == 4


def test_check_cli_json_output() -> None:
    from planner_critic.cli.check import run_check
    with tempfile.TemporaryDirectory() as tmp:
        plan_path = Path(tmp) / "plan.json"
        plan_path.write_text(_simple_plan().model_dump_json())
        code = run_check([str(plan_path), "--output", "json"])
        assert code in (0, 1)


def test_domains_cli_list() -> None:
    from planner_critic.cli.domains import run_domains
    code = run_domains(["list"])
    assert code == 0


def test_templates_cli_list() -> None:
    from planner_critic.cli.templates import run_templates
    code = run_templates(["list"])
    assert code == 0


def test_policy_cli_list() -> None:
    from planner_critic.cli.policy import run_policy
    code = run_policy(["list"])
    assert code == 0


def test_diagnose_cli_with_trace_file() -> None:
    from planner_critic.cli.diagnose import run_diagnose
    from planner_critic.types import ExecutionTrace
    trace = ExecutionTrace(id="t1", plan_id="p1", task_id="step1", outcome="missing_rollback", failure_class="planning")
    with tempfile.TemporaryDirectory() as tmp:
        trace_path = Path(tmp) / "trace.json"
        trace_path.write_text(trace.model_dump_json())
        code = run_diagnose([str(trace_path)])
        assert code == 0


def test_diagnose_cli_json_format() -> None:
    from planner_critic.cli.diagnose import run_diagnose
    from planner_critic.types import ExecutionTrace
    trace = ExecutionTrace(id="t1", plan_id="p1", task_id="step1", outcome="timeout", failure_class="execution")
    with tempfile.TemporaryDirectory() as tmp:
        trace_path = Path(tmp) / "trace.json"
        trace_path.write_text(trace.model_dump_json())
        code = run_diagnose([str(trace_path), "--format", "json"])
        assert code == 0


def test_diagnose_markdown_format() -> None:
    from planner_critic.cli.diagnose import run_diagnose
    from planner_critic.types import ExecutionTrace
    trace = ExecutionTrace(id="t1", plan_id="p1", task_id="step1", outcome="permission_denied", failure_class="execution")
    with tempfile.TemporaryDirectory() as tmp:
        trace_path = Path(tmp) / "trace.json"
        trace_path.write_text(trace.model_dump_json())
        code = run_diagnose([str(trace_path), "--format", "markdown"])
        assert code == 0