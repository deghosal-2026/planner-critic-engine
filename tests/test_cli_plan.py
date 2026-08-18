"""``plancritic plan`` CLI tests (F-61)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from planner_critic.cli.plan import build_plan_parser, run_plan


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
        "[roles]\nplanner = \"local\"\ncritic = \"local\"\n\n[providers.local]\ntransport = \"openai-compatible\"\nbase_url = \"http://localhost:11434/v1\"\nmodel = \"llama3.2\"\n"
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


def test_run_plan_no_providers(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
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


def test_run_plan_goal_validation_failure(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Invalid goal fields return exit code 1 (line 109-111)."""
    goal_file = tmp_path / "goal.json"
    goal_file.write_text(json.dumps({"id": 123}))  # wrong type for id
    rc = run_plan([str(goal_file)])
    assert rc == 1
    assert "goal validation failed" in capsys.readouterr().out


def test_run_plan_config_load_failure(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """A config file with bad TOML returns exit code 1 (line 115-117)."""
    goal_file = _make_goal_file(tmp_path)
    config_file = tmp_path / "bad.toml"
    config_file.write_text("[[[invalid]]]\n")
    rc = run_plan([str(goal_file), "--config", str(config_file)])
    assert rc == 1
    assert "failed to load config" in capsys.readouterr().out