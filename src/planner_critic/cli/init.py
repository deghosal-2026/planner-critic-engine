from __future__ import annotations

import argparse
from importlib.resources import files
from pathlib import Path

DEFAULT_CONFIG = """# PlannerCritic provider registry
# Edit this file to configure LLM providers for the planner and critic roles.

[roles]
planner = "local"
critic = "local"

[providers.local]
transport = "openai-compatible"
base_url = "http://localhost:11434/v1"
model = "llama3.2"
"""

#: The packaged demo goal (D11 §7) so ``init`` → ``plan`` works immediately.
_PACKAGED_GOAL_NAME = "migration.json"


def _packaged_goal_text() -> str:
    """Read the packaged demo goal bundled inside the wheel."""
    resource = files("planner_critic.demo").joinpath("data", _PACKAGED_GOAL_NAME)
    return resource.read_text(encoding="utf-8")


def build_init_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="plancritic init",
        description="Scaffold a new PlannerCritic project (F-85)",
        add_help=False,
    )
    parser.add_argument(
        "--dir",
        default=".",
        help="Target directory (default: current directory)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files",
    )
    return parser


def run_init(argv: list[str]) -> int:
    args = build_init_parser().parse_args(argv)
    target = Path(args.dir).resolve()

    plancritic_dir = target / ".plancritic"
    config_path = target / "plancritic.toml"
    db_path = plancritic_dir / "plans.db"
    goal_path = plancritic_dir / "goal.json"

    if config_path.exists() and not args.force:
        print(f"plancritic.toml already exists at {config_path}; use --force to overwrite")
        return 1

    plancritic_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text(DEFAULT_CONFIG)
    db_path.write_text("")
    goal_path.write_text(_packaged_goal_text())

    print(f"Initialized PlannerCritic project in {target}")
    print(f"  Config: {config_path}")
    print(f"  Store:  {db_path}")
    print(f"  Example goal: {goal_path}")
    print(f"Run: plancritic plan {goal_path}")
    return 0


__all__ = ["build_init_parser", "run_init"]
