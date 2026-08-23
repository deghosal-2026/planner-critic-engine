"""Top-level CLI wiring tests: subcommand dispatch and version."""

from __future__ import annotations

from pathlib import Path

import pytest

from planner_critic._cli import main


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    """``plancritic --version`` prints the package version and exits 0."""
    from planner_critic import __version__

    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_cli_no_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    """No subcommand prints the help and exits 0."""
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "usage:" in out
    assert "escalate" in out
    assert "migrate" in out
    assert "providers" in out


def test_cli_migrate_dispatches(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The migrate subcommand dispatches through the top-level entry point."""
    db = tmp_path / "plans.db"
    assert main(["migrate", "--path", str(db)]) == 0
    assert "schema at v" in capsys.readouterr().out


def test_cli_providers_add_dispatches(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The providers subcommand dispatches through the top-level entry point."""
    config = tmp_path / "plancritic.toml"
    assert (
        main(
            [
                "providers",
                "--config",
                str(config),
                "add",
                "local",
                "--base-url",
                "http://localhost:11434/v1",
                "--model",
                "llama3.2",
            ]
        )
        == 0
    )
    assert "added provider 'local'" in capsys.readouterr().out
