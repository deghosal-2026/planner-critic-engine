"""CLI entry point — ``plancritic``.

M1 shipped only ``--version``. M2 adds the first functional subcommands
(``migrate``, and ``providers`` from the M2 registry work); the full CLI
(plan/critique/plans/escalate/...) is an M6 concern. Subcommands live in
:mod:`planner_critic.cli` and each exposes ``build_*_parser`` + ``run_*`` so
they are self-describing and testable in isolation.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence

from . import __version__
from .cli import (
    build_critique_parser,
    build_demo_parser,
    build_escalate_parser,
    build_init_parser,
    build_migrate_parser,
    build_plan_parser,
    build_plans_parser,
    build_providers_parser,
    build_quickstart_parser,
    build_replay_parser,
    run_critique,
    run_demo,
    run_escalate,
    run_init,
    run_migrate,
    run_plan,
    run_plans,
    run_providers,
    run_quickstart,
    run_replay,
)

SubcommandRunner = Callable[[list[str]], int]

_SUBCOMMANDS: dict[str, tuple[argparse.ArgumentParser, SubcommandRunner]] = {
    "critique": (build_critique_parser(), run_critique),
    "demo": (build_demo_parser(), run_demo),
    "escalate": (build_escalate_parser(), run_escalate),
    "init": (build_init_parser(), run_init),
    "migrate": (build_migrate_parser(), run_migrate),
    "plan": (build_plan_parser(), run_plan),
    "plans": (build_plans_parser(), run_plans),
    "providers": (build_providers_parser(), run_providers),
    "quickstart": (build_quickstart_parser(), run_quickstart),
    "replay": (build_replay_parser(), run_replay),
}


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser with its subcommands.

    Returns:
        The root parser; subcommand parsers are attached as children.
    """
    parser = argparse.ArgumentParser(
        prog="plancritic", description="PlannerCritic Engine CLI"
    )
    parser.add_argument("--version", action="version", version=f"plancritic {__version__}")
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    for name, (sub_parser, _) in _SUBCOMMANDS.items():
        subparsers.add_parser(name, parents=[sub_parser], help=sub_parser.description)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point (console script target).

    Args:
        argv: Argument list; None means ``sys.argv[1:]``.

    Returns:
        The process exit code.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    raw = list(argv) if argv is not None else sys.argv[1:]
    rest = raw[raw.index(args.command) + 1 :]
    return _SUBCOMMANDS[args.command][1](rest)


if __name__ == "__main__":  # pragma: no cover - console-script path
    raise SystemExit(main())
