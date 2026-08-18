"""``plancritic init`` CLI tests (F-85)."""

from __future__ import annotations

import os

import pytest

from planner_critic.cli.init import run_init


def test_init_creates_project_structure(tmp_path: Path) -> None:
    """init creates .plancritic dir, config, and store."""
    rc = run_init(["--dir", str(tmp_path)])
    assert rc == 0

    assert (tmp_path / ".plancritic").is_dir()
    assert (tmp_path / "plancritic.toml").is_file()
    assert (tmp_path / ".plancritic" / "plans.db").is_file()

    config_text = (tmp_path / "plancritic.toml").read_text()
    assert "local" in config_text
    assert "localhost:11434" in config_text


def test_init_refuses_overwrite_without_force(tmp_path: Path) -> None:
    """init without --force refuses to overwrite existing config."""
    (tmp_path / ".plancritic").mkdir(parents=True)
    (tmp_path / "plancritic.toml").write_text("existing")
    rc = run_init(["--dir", str(tmp_path)])
    assert rc == 1
    assert (tmp_path / "plancritic.toml").read_text() == "existing"


def test_init_force_overwrites(tmp_path: Path) -> None:
    """init --force overwrites existing config and store."""
    (tmp_path / ".plancritic").mkdir(parents=True)
    (tmp_path / "plancritic.toml").write_text("old config")
    old_db = tmp_path / ".plancritic" / "plans.db"
    old_db.write_text("old db")

    rc = run_init(["--dir", str(tmp_path), "--force"])
    assert rc == 0

    config_text = (tmp_path / "plancritic.toml").read_text()
    assert "localhost:11434" in config_text
    assert old_db.read_text() == ""


def test_init_defaults_to_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """init without --dir uses the current working directory."""
    monkeypatch.chdir(tmp_path)
    rc = run_init([])
    assert rc == 0
    assert os.path.isdir(".plancritic")
    assert os.path.isfile("plancritic.toml")


from pathlib import Path  # noqa: E402 - needed for tmp_path type annotation