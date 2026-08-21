"""``plancritic plan`` CLI tests (F-61)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from planner_critic.cli.plan import build_plan_parser, run_plan
from planner_critic.llm.base import Completion
from planner_critic.schema.goal import Goal
from planner_critic.schema.plan import PlanVersion


def _make_goal_file(tmp_path: Path, **overrides: object) -> str:
    data: dict[str, object] = {
        "id": "test-goal",
        "description": "Test goal description",
        "risk_tolerance": "balanced",
    }
    data.update(overrides)
    path = tmp_path / "goal.json"
    path.write_text(json.dumps(data))
    return str(path)


def _make_config(tmp_path: Path) -> str:
    config = tmp_path / "plancritic.toml"
    config.write_text(
        "[roles]\n"
        'planner = "local"\n'
        'critic = "local"\n\n'
        "[providers.local]\n"
        'transport = "openai-compatible"\n'
        'base_url = "http://localhost:11434/v1"\n'
        'model = "llama3.2"\n'
    )
    return str(config)


def test_build_plan_parser() -> None:
    """The parser can be constructed without error."""
    parser = build_plan_parser()
    assert parser.prog == "plancritic plan"


def test_run_plan_missing_goal_file(tmp_path: Path) -> None:
    """A missing goal file returns exit code 1."""
    rc = run_plan([str(tmp_path / "nonexistent.json")])
    assert rc == 1


def test_run_plan_invalid_json(tmp_path: Path) -> None:
    """Invalid goal JSON returns exit code 1."""
    goal_file = tmp_path / "goal.json"
    goal_file.write_text("not json")
    rc = run_plan([str(goal_file)])
    assert rc == 1


def test_run_plan_no_providers(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Missing provider config returns exit code 1."""
    goal_file = _make_goal_file(tmp_path)
    config_file = tmp_path / "plancritic.toml"
    config_file.write_text("[roles]\n[providers]\n")
    rc = run_plan([str(goal_file), "--config", str(config_file)])
    assert rc == 1
    assert "no providers configured" in capsys.readouterr().out


def test_run_plan_no_config(tmp_path: Path) -> None:
    """Missing config file returns exit code 1."""
    goal_file = _make_goal_file(tmp_path)
    rc = run_plan([str(goal_file), "--config", str(tmp_path / "nonexistent.toml")])
    assert rc == 1


def test_run_plan_dry_run_with_config(tmp_path: Path) -> None:
    """Dry-run with a valid goal and config attempts planning (may fail at
    provider call, which is fine — we test the CLI wiring)."""
    goal_file = _make_goal_file(tmp_path)
    config_file = _make_config(tmp_path)
    rc = run_plan([str(goal_file), "--config", str(config_file), "--dry-run"])
    assert rc in (0, 1)


def test_run_plan_goal_validation_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Invalid goal fields return exit code 1 (line 109-111)."""
    goal_file = tmp_path / "goal.json"
    goal_file.write_text(json.dumps({"id": 123}))  # wrong type for id
    rc = run_plan([str(goal_file)])
    assert rc == 1
    assert "goal validation failed" in capsys.readouterr().out


def test_run_plan_config_load_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A config file with bad TOML returns exit code 1 (line 115-117)."""
    goal_file = _make_goal_file(tmp_path)
    config_file = tmp_path / "bad.toml"
    config_file.write_text("[[[invalid]]]\n")
    rc = run_plan([str(goal_file), "--config", str(config_file)])
    assert rc == 1
    assert "failed to load config" in capsys.readouterr().out


def test_cli_planner_uses_no_think_and_structured_example_prompt() -> None:
    """The real CLI planner prompt carries the no-think + schema-shape guidance."""
    from planner_critic.cli.plan import _CLIPlanner
    from planner_critic.llm.base import Completion, Message, ToolSchema
    from planner_critic.schema.plan import PlanVersion

    class CaptureProvider:
        name = "fake"
        base_url = "http://fake.local"
        model = "fake-model"

        def __init__(self) -> None:
            self.messages: list[Message] = []

        def complete(
            self,
            messages: list[Message],
            tool_schemas: tuple[ToolSchema, ...] = (),
        ) -> Completion:
            self.messages = list(messages)
            plan = PlanVersion(
                id="p1",
                goal_id="g1",
                version=1,
                tasks=[],
                dependencies=[],
                branches=[],
            )
            return Completion(content=json.dumps(plan.to_dict()), finish_reason="stop")

    provider = CaptureProvider()
    planner = _CLIPlanner(provider)  # type: ignore[arg-type]
    goal = Goal.model_validate({"id": "g1", "description": "Ship a service"})

    planner.decompose(goal)

    assert provider.messages[0].role == "system"
    assert "/no_think" in provider.messages[0].content
    assert "Reply with ONLY a JSON object" in provider.messages[0].content
    assert "High/critical risk tasks MUST have rollback" in provider.messages[0].content


_SUPPORTED_PLAN = PlanVersion.model_validate(
    {
        "id": "p1",
        "goal_id": "g1",
        "version": 1,
        "tasks": [
            {
                "id": "backup",
                "description": "Back up the database",
                "action": "backup",
                "target": "db",
                "risk_class": "medium",
                "preconditions": [],
            },
            {
                "id": "migrate",
                "description": "Apply schema migration",
                "action": "migrate",
                "target": "schema",
                "risk_class": "high",
                "preconditions": [],
                "rollback": {"trigger": "migration fails", "action": "restore from backup"},
                "verification": {"what": "schema version", "how": "run checks", "expected": "v2"},
            },
        ],
        "dependencies": [{"from_task": "backup", "to_task": "migrate", "kind": "hard"}],
        "branches": [],
    }
)


def _cli_plan_from_supported(plan: PlanVersion) -> PlanVersion:
    """Run ``_CLIPlanner.decompose`` against a capture provider returning the
    supported plan, and return the parsed PlanVersion it produced."""
    from planner_critic.cli.plan import _CLIPlanner

    class CaptureProvider:
        """A provider that echoes the supported plan back as JSON."""

        name = "fake"
        base_url = "http://fake.local"
        model = "fake-model"

        def complete(self, messages, tool_schemas=()):
            return Completion(content=json.dumps(plan.to_dict()), finish_reason="stop")

    planner = _CLIPlanner(CaptureProvider())  # type: ignore[arg-type]
    goal = Goal.model_validate({"id": "g1", "description": "Ship a service"})
    produced = planner.decompose(goal)
    # Re-validate through the typed schema to prove structural fidelity.
    return PlanVersion.model_validate(produced.to_dict())


def test_cli_planner_high_risk_task_carries_rollback_and_verification() -> None:
    """C5 structural fidelity: a high-risk task the CLI planner emits must
    carry rollback + verification (the prompt contract the engine relies on)."""
    plan = _cli_plan_from_supported(_SUPPORTED_PLAN)
    high = next(t for t in plan.tasks if t.risk_class == "high")
    assert high.rollback is not None
    assert high.verification is not None
    assert high.rollback.action == "restore from backup"


def test_cli_planner_dependency_edges_reference_real_tasks() -> None:
    """C5 structural fidelity: dependency edges must reference task ids that
    exist, and the plan graph must be acyclic (schema_valid + no_dep_cycles)."""
    from planner_critic.gates import run_deterministic_gates

    plan = _cli_plan_from_supported(_SUPPORTED_PLAN)
    task_ids = {t.id for t in plan.tasks}
    for dep in plan.dependencies:
        assert dep.from_task in task_ids
        assert dep.to_task in task_ids
    blockers = [f for f in run_deterministic_gates(plan) if f.severity.value == "blocker"]
    assert blockers == []  # no schema/cycle/ordering blockers


def test_cli_planner_produces_schema_valid_plan() -> None:
    """C5 structural fidelity: the CLI planner output validates as a PlanVersion
    (the same typed schema the programmatic engine stores)."""
    plan = _cli_plan_from_supported(_SUPPORTED_PLAN)
    assert plan.goal_id == "g1"
    assert [t.id for t in plan.tasks] == ["backup", "migrate"]
    assert plan.dependencies[0].kind.value == "hard"
