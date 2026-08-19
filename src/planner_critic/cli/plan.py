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

_PLAN_EXAMPLE = (
    '{"id":"plan-x","goal_id":"g","version":1,'
    '"tasks":[{"id":"backup","description":"Back up the database",'
    '"action":"backup","target":"db","risk_class":"medium"},'
    '{"id":"migrate","description":"Apply schema migration",'
    '"action":"migrate","target":"schema","risk_class":"high",'
    '"rollback":{"trigger":"migration fails","action":"restore from backup",'
    '"safety_guard":"verify backup integrity"},'
    '"verification":{"what":"schema version","how":"run checks",'
    '"expected":"v2"}}],'
    '"dependencies":[{"from_task":"backup","to_task":"migrate","kind":"hard"}]}'
)

_PLANNER_SYSTEM_PROMPT = (
    "/no_think You are a planner. Reply with ONLY a JSON object "
    "(no markdown, no prose, no thinking). Use EXACTLY these field names: "
    "id, goal_id, version, tasks, dependencies, branches. "
    "Each task uses: id, description, action, target, risk_class, optional "
    "rollback{trigger,action,safety_guard}, optional verification{what,how,expected}, "
    "optional preconditions, optional parallel_group, optional blast_radius. "
    "Each dependency uses: from_task, to_task, kind, optional reason. "
    "Each branch uses: id, kind, tasks, join. High/critical risk tasks MUST have rollback. "
    f"Example shape: {_PLAN_EXAMPLE}"
)


class _CLIPlanner(PlannerRole):
    def __init__(self, provider: LLMProvider) -> None:
        self._enforcer = StructuredEnforcer(provider)

    def decompose(self, goal: Goal) -> PlanVersion:
        messages = [
            Message(
                role="system",
                content=_PLANNER_SYSTEM_PROMPT,
            ),
            Message(
                role="user",
                content=(
                    f"GOAL:\n{goal.model_dump(mode='json')}\n\n"
                    "Produce the PlanVersion JSON now. version=1."
                ),
            ),
        ]
        return self._enforcer.complete(messages, PlanVersion)

    def revise(self, plan: PlanVersion, findings: list[Finding]) -> PlanVersion:
        messages = [
            Message(
                role="system",
                content=(
                    _PLANNER_SYSTEM_PROMPT
                    + " Revise the plan to address the critique findings. "
                    "Keep version unchanged; the loop stamps it."
                ),
            ),
            Message(
                role="user",
                content=(
                    f"PLAN:\n{plan.model_dump(mode='json')}\n\n"
                    + f"FINDINGS:\n{json.dumps([f.model_dump(mode='json') for f in findings])}\n\n"
                    + "Produce the revised PlanVersion JSON now."
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
