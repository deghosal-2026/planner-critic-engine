from __future__ import annotations

import tempfile
from pathlib import Path

from planner_critic.schema.plan import PlanVersion, RiskClass, Task


def _plan() -> PlanVersion:
    t = Task(id="t1", description="deploy", action="deploy", target="api", risk_class=RiskClass.LOW)
    return PlanVersion(id="plan-1", goal_id="goal-1", version=1, tasks=[t], dependencies=[])


def test_cli_imports() -> None:
    from planner_critic._cli import _SUBCOMMANDS
    assert "check" in _SUBCOMMANDS
    assert "domains" in _SUBCOMMANDS
    assert "policy" in _SUBCOMMANDS
    assert "templates" in _SUBCOMMANDS
    assert "diagnose" in _SUBCOMMANDS
    assert "plan" in _SUBCOMMANDS
    assert "quota" in _SUBCOMMANDS


def test_cli_help() -> None:
    from planner_critic._cli import main
    code = main([])
    assert code == 0


def test_check_with_policies_dir() -> None:
    from planner_critic.cli.check import run_check
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        plan_path = tmpdir / "plan.json"
        plan_path.write_text(_plan().model_dump_json())
        pol_dir = tmpdir / "policies"
        pol_dir.mkdir()
        pol_file = pol_dir / "test_policy.yaml"
        pol_file.write_text("""
kind: Policy
name: test_policy
cel: "len(tasks) > 0"
severity: blocker
""")
        code = run_check([str(plan_path), "--policies-dir", str(pol_dir)])
        assert code in (0, 1)


def test_check_with_domain_pack_manifest() -> None:
    from planner_critic.cli.check import run_check
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        plan_path = tmpdir / "plan.json"
        plan_path.write_text(_plan().model_dump_json())
        manifest = tmpdir / "domain-pack.yaml"
        manifest.write_text("""
name: test
gates: []
preconditions: {}
""")
        code = run_check([str(plan_path), "--domain", str(manifest)])
        assert code in (0, 1)


def test_check_with_invalid_domain() -> None:
    from planner_critic.cli.check import run_check
    with tempfile.TemporaryDirectory() as tmp:
        plan_path = Path(tmp) / "plan.json"
        plan_path.write_text(_plan().model_dump_json())
        code = run_check([str(plan_path), "--domain", "nonexistent"])
        assert code == 4


def test_domains_show_nonexistent() -> None:
    from planner_critic.cli.domains import run_domains
    code = run_domains(["show", "nonexistent"])
    assert code == 1


def test_domains_add_nonexistent() -> None:
    from planner_critic.cli.domains import run_domains
    code = run_domains(["add", "/nonexistent.yaml"])
    assert code == 1


def test_policy_add_nonexistent() -> None:
    from planner_critic.cli.policy import run_policy
    code = run_policy(["add", "/nonexistent"])
    assert code == 1


def test_templates_test_nonexistent() -> None:
    from planner_critic.cli.templates import run_templates
    with tempfile.TemporaryDirectory() as tmp:
        plan_path = Path(tmp) / "plan.json"
        plan_path.write_text(_plan().model_dump_json())
        code = run_templates(["test", "nonexistent", str(plan_path)])
        assert code == 1


def test_templates_add() -> None:
    from planner_critic.cli.templates import run_templates
    code = run_templates(["add", "my-template", "--pattern", "backup", "--description", "Back up data"])
    assert code == 0


def test_diagnose_nonexistent_file() -> None:
    from planner_critic.cli.diagnose import run_diagnose
    code = run_diagnose(["/nonexistent/trace.json"])
    assert code == 1


def test_diagnose_empty_trace_list() -> None:
    from planner_critic.cli.diagnose import run_diagnose
    with tempfile.TemporaryDirectory() as tmp:
        trace_path = Path(tmp) / "trace.json"
        trace_path.write_text("[]")
        code = run_diagnose([str(trace_path)])
        assert code == 1


def test_policy_test_nonexistent() -> None:
    from planner_critic.cli.policy import run_policy
    with tempfile.TemporaryDirectory() as tmp:
        plan_path = Path(tmp) / "plan.json"
        plan_path.write_text(_plan().model_dump_json())
        code = run_policy(["test", "nonexistent", str(plan_path)])
        assert code == 1


def test_guardrail_module_imports() -> None:
    from planner_critic.guardrail import (
        escalate,
        guardrail,
        re_gate,
    )
    assert callable(guardrail)
    assert callable(re_gate)
    assert callable(escalate)
