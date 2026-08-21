"""CLI subcommand package.

M1 shipped the bare ``plancritic --version`` entry point. M2 adds the first
functional subcommands — ``migrate`` (store schema) and ``providers``
(registry) — while the full CLI surface (plan/critique/plans/escalate/...) is
an M6 concern. Each module exposes a ``run(args) -> int`` function registered
in :mod:`planner_critic._cli`; the argument parser stays in the subcommand
module so a command is self-describing and testable in isolation.
"""

from __future__ import annotations

from .critique import build_critique_parser, run_critique
from .demo import build_demo_parser, run_demo
from .escalate import build_escalate_parser, run_escalate
from .field_test import build_field_test_parser, run_field_test  # noqa: F401
from .init import build_init_parser, run_init
from .migrate import build_migrate_parser, run_migrate
from .plan import build_plan_parser, run_plan
from .plans import build_plans_parser, run_plans
from .providers import build_providers_parser, run_providers
from .quickstart import build_quickstart_parser, run_quickstart
from .replay import build_replay_parser, run_replay

__all__ = [
    "build_critique_parser",
    "build_demo_parser",
    "build_escalate_parser",
    "build_init_parser",
    "build_migrate_parser",
    "build_plan_parser",
    "build_plans_parser",
    "build_providers_parser",
    "build_quickstart_parser",
    "build_replay_parser",
    "run_critique",
    "run_demo",
    "run_escalate",
    "run_init",
    "run_migrate",
    "run_plan",
    "run_plans",
    "run_providers",
    "run_quickstart",
    "run_replay",
]
