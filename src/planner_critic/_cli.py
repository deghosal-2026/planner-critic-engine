"""Minimal M1 CLI entry point — ``plancritic --version``.

The full CLI (plan/critique/providers/plans/escalate/...) is an M6 concern.
M1 ships only the entry point that reports version, but wiring this module
into ``pyproject.toml``'s ``[project.scripts]`` makes ``plancritic --version``
valid from day one. Kept dependency-free (stdlib ``argparse``) so the core
package stays installable without the M6 tooling.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from . import __version__


def _build_parser() -> argparse.ArgumentParser:
    """Build the placeholder CLI parser.

    Returns:
        A parser that only knows ``--version`` today; extended in M6.
    """
    parser = argparse.ArgumentParser(prog="plancritic", description="PlannerCritic Engine CLI")
    parser.add_argument("--version", action="version", version=f"plancritic {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entry point (console script target).

    Args:
        argv: Argument list; None means ``sys.argv[1:]``.
    """
    parser = _build_parser()
    parser.parse_args(argv)


if __name__ == "__main__":  # pragma: no cover - console-script path
    main()
