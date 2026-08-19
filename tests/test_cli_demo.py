"""``plancritic demo`` CLI tests (F-86): subcommand wiring + exit codes.

The CLI is a thin wrapper over :func:`planner_critic.demo.runner.run_demo`;
these tests cover the parser surface, the store fallback (side-channel
contract §7.2), and the ``_cli`` registration.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from planner_critic import _cli
from planner_critic.cli.demo import build_demo_parser, run_demo
from planner_critic.store.base import StoreUnavailable

MIGRATION = Path(__file__).parents[1] / "examples" / "goals" / "migration.json"


def test_demo_parser_exposes_surface() -> None:
    """The demo parser accepts --goal, --store, and --no-graph."""
    parser = build_demo_parser()
    args = parser.parse_args(
        ["--goal", str(MIGRATION), "--store", ".plancritic/plans.db", "--no-graph"]
    )
    assert args.goal == str(MIGRATION)
    assert args.store == ".plancritic/plans.db"
    assert args.no_graph is True


def test_demo_defaults_to_packaged_goal() -> None:
    """Without --goal the demo uses the packaged migration scenario (D11 §6)."""
    args = build_demo_parser().parse_args([])
    assert args.goal != ""
    assert Path(args.goal).is_file()


def test_run_demo_returns_one_on_invalid_goal(tmp_path: Path, capsys) -> None:
    """A missing goal file fails closed with exit code 1."""
    rc = run_demo(["--goal", str(tmp_path / "nope.json")])
    assert rc == 1
    assert "is not a valid Goal" in capsys.readouterr().out


def test_run_demo_returns_zero_and_prints_story(tmp_path: Path, capsys) -> None:
    """A valid corpus goal runs the full hermetic story to exit code 0."""
    store = tmp_path / "plans.db"
    rc = run_demo(["--goal", str(MIGRATION), "--store", str(store)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[1/5 draft]" in out
    assert "[5/5 complete]" in out
    assert "graph TD" in out


def test_run_demo_store_unavailable_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """A down store warns and continues in memory (side-channel §7.2)."""

    class DownStore:
        """A stand-in that always claims the store is unavailable."""

        def __init__(self, path: object) -> None:
            raise StoreUnavailable("store is down")

    monkeypatch.setattr("planner_critic.cli.demo.SQLiteStore", DownStore)
    rc = run_demo(["--goal", str(MIGRATION), "--store", str(tmp_path / "plans.db")])
    assert rc == 0
    assert "continuing in memory" in capsys.readouterr().out


def test_demo_subcommand_is_registered(tmp_path: Path, capsys) -> None:
    """``plancritic demo`` is wired into the root CLI."""
    assert "demo" in _cli._SUBCOMMANDS
    rc = _cli.main(["demo", "--goal", str(MIGRATION), "--store", str(tmp_path / "p.db")])
    assert rc == 0
    assert "[5/5 complete]" in capsys.readouterr().out
