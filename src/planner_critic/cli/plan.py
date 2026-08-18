from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..critique.critic import LLMCritic
from ..engine import Engine
from ..llm.base import LLMProvider, Message
from ..llm.registry import ProviderRegistry
from ..llm.structured import StructuredEnforcer
from ..loop import LoopConfig
from ..roles import CriticRole, PlannerRole
from ..schema.goal import Goal
from ..schema.plan import PlanVersion
from ..types import Finding

DEFAULT_CONFIG_PATH = "plancritic.toml"
DEFAULT_STORE_PATH = ".plancritic/plans.db"


class _CLIPlanner(PlannerRole):
    def __init__(self, provider: LLMProvider) -> None:
        self._enforcer = StructuredEnforcer(provider)

    def decompose(self, goal: Goal) -> PlanVersion:
        messages = [
            Message(
                role="system",
                content=(
                    "You are a planner. Decompose the goal into a typed plan "
                    "with tasks, dependencies, branches, and rollback steps."
                ),
            ),
            Message(
                role="user",
                content=(
                    f"GOAL:\n{goal.model_dump(mode='json')}\n\n"
                    "Produce a PlanVersion JSON."
                ),
            ),
        ]
        return self._enforcer.complete(messages, PlanVersion)

    def revise(self, plan: PlanVersion, findings: list[Finding]) -> PlanVersion:
        messages = [
            Message(
                role="system",
                content="You are a planner. Revise the plan to address the critique findings.",
            ),
            Message(
                role="user",
                content=(
                    f"PLAN:\n{plan.model_dump(mode='json')}\n\n"
                    + f"FINDINGS:\n{json.dumps([f.model_dump(mode='json') for f in findings])}\n\n"
                    + "Produce a revised PlanVersion JSON."
                ),
            ),
        ]
        return self._enforcer.complete(messages, PlanVersion)


def _build_roles(registry: ProviderRegistry, goal: Goal) -> tuple[PlannerRole, CriticRole]:
    planner_provider = registry.get_provider("planner")
    critic_provider = registry.get_provider("critic")
    planner = _CLIPlanner(planner_provider)
    critic: CriticRole = LLMCritic(goal, critic_provider)
    return planner, critic


def build_plan_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="plancritic plan",
        description="Plan a goal (F-61)",
        add_help=False,
    )
    parser.add_argument("goal_file", help="Path to a Goal JSON file")
    parser.add_argument("--store", default=DEFAULT_STORE_PATH, help="Store path")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Config file path")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan but don't store")
    return parser


def _store_plan(args: argparse.Namespace, plan: PlanVersion, findings: list[Finding]) -> None:
    from ..store.sqlite import SQLiteStore

    try:
        store = SQLiteStore(args.store)
        store.put_plan_version(plan)
        store.put_findings(plan.id, plan.version, findings)
        store.close()
    except Exception as err:
        print(f"warning: could not store plan: {err}")


def run_plan(argv: list[str]) -> int:
    args = build_plan_parser().parse_args(argv)
    try:
        goal_data = json.loads(Path(args.goal_file).read_text())
    except FileNotFoundError:
        print(f"goal file not found: {args.goal_file}")
        return 1
    except json.JSONDecodeError as err:
        print(f"invalid goal JSON: {err}")
        return 1

    try:
        goal = Goal.model_validate(goal_data)
    except Exception as err:
        print(f"goal validation failed: {err}")
        return 1

    try:
        registry = ProviderRegistry.load(args.config)
    except Exception as err:
        print(f"failed to load config: {err}")
        return 1

    if not registry.roles.get("planner") or not registry.roles.get("critic"):
        print(
            "no providers configured for planner and critic roles; "
            "run 'plancritic providers add' first"
        )
        return 1

    try:
        planner, critic = _build_roles(registry, goal)
    except Exception as err:
        print(f"failed to build provider roles: {err}")
        return 1

    engine = Engine(planner=planner, critic=critic, config=LoopConfig())

    try:
        result = engine.plan(goal)
    except Exception as err:
        print(f"planning failed: {err}")
        return 1

    if result.is_approved:
        ap = result.approved_plan
        if ap is None:
            return 1
        print(f"plan approved: {ap.plan.id} v{ap.plan.version}")
        print(json.dumps(ap.plan.to_dict(), indent=2))
        if not args.dry_run:
            _store_plan(args, ap.plan, result.findings)
    else:
        print(f"plan escalated: {result.reason_code}")
        if result.escalation:
            print(f"  question: {result.escalation.question}")
        if result.plan is not None:
            plan = result.plan
            print(json.dumps(plan.to_dict(), indent=2))
            if not args.dry_run:
                _store_plan(args, plan, result.findings)

    return 0


__all__ = ["build_plan_parser", "run_plan"]
