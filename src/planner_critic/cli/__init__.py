"""CLI subcommand package.

M1 shipped the bare ``plancritic --version`` entry point. M2 adds the first
functional subcommands — ``migrate`` (store schema) and ``providers``
(registry) — while the full CLI surface (plan/critique/plans/escalate/...) is
an M6 concern. Each module exposes a ``run(args) -> int`` function registered
in :mod:`planner_critic._cli`; the argument parser stays in the subcommand
module so a command is self-describing and testable in isolation.
"""

from __future__ import annotations

from .escalate import build_escalate_parser, run_escalate
from .migrate import build_migrate_parser, run_migrate
from .providers import build_providers_parser, run_providers
from .replay import build_replay_parser, run_replay

__all__ = [
    "build_escalate_parser",
    "build_migrate_parser",
    "build_providers_parser",
    "build_replay_parser",
    "run_escalate",
    "run_migrate",
    "run_providers",
    "run_replay",
]
