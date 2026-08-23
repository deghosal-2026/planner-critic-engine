"""``plancritic lessons`` CLI tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from planner_critic.cli.lessons import run_lessons


def test_lessons_propose(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = run_lessons(["propose"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Proposed" in out or "standing" in out.lower()


def test_lessons_list(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = run_lessons(["list"])
    assert rc == 0


def test_lessons_list_filtered(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = run_lessons(["list", "--status", "proposed"])
    assert rc == 0


def test_lessons_promote_not_found(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = run_lessons(["promote", "nonexistent-rule"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "not found" in err.lower()
