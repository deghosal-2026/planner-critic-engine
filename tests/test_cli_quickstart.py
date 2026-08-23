"""``plancritic quickstart`` CLI tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from planner_critic import _cli
from planner_critic.cli.quickstart import build_quickstart_parser, run_quickstart


def test_quickstart_parser_exposes_provider_surface() -> None:
    """The parser accepts provider config and workspace controls."""
    parser = build_quickstart_parser()
    args = parser.parse_args(
        [
            "--base-url",
            "http://127.0.0.1:8000/v1",
            "--model",
            "Qwen3.5-9B-MLX-4bit",
            "--api-key",
            "sk-test",
            "--dir",
            "/tmp/pc-quickstart",
            "--goal",
            "/tmp/goal.json",
        ]
    )
    assert args.base_url == "http://127.0.0.1:8000/v1"
    assert args.model == "Qwen3.5-9B-MLX-4bit"
    assert args.api_key == "sk-test"
    assert args.dir == "/tmp/pc-quickstart"
    assert args.goal == "/tmp/goal.json"


def test_quickstart_defaults_to_packaged_goal_and_temp_dir() -> None:
    """Without overrides, quickstart uses the packaged goal and temp workspace."""
    args = build_quickstart_parser().parse_args(
        ["--base-url", "http://127.0.0.1:8000/v1", "--model", "mlx-model"]
    )
    assert Path(args.goal).is_file()
    assert args.dir == ""


def test_run_quickstart_requires_live_provider_args(capsys: pytest.CaptureFixture[str]) -> None:
    """Provider/model args are mandatory for the shipped quickstart."""
    with pytest.raises(SystemExit):
        run_quickstart([])
    assert "--base-url" in capsys.readouterr().err


def test_run_quickstart_writes_temp_project_and_fails_closed_on_provider(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Quickstart scaffolds a workspace before surfacing provider failures."""
    rc = run_quickstart(
        [
            "--base-url",
            "http://127.0.0.1:9/v1",
            "--model",
            "broken-model",
            "--dir",
            str(tmp_path),
        ]
    )
    assert rc == 1
    assert (tmp_path / "plancritic.toml").is_file()
    assert (tmp_path / ".plancritic" / "goal.json").is_file()
    out = capsys.readouterr().out
    assert "planning failed" in out


def test_quickstart_subcommand_is_registered(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``plancritic quickstart`` is wired into the root CLI."""
    assert "quickstart" in _cli._SUBCOMMANDS
    rc = _cli.main(
        [
            "quickstart",
            "--base-url",
            "http://127.0.0.1:9/v1",
            "--model",
            "broken-model",
            "--dir",
            str(tmp_path),
        ]
    )
    assert rc == 1
    assert "planning failed" in capsys.readouterr().out
