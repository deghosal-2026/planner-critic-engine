"""The Engine facade — a single convenience entry point into the loop.

Wraps :func:`planner_critic.loop.run_loop` with a fixed role pair and
configuration so a consumer can ``Engine(...).plan(goal)`` without touching
the procedural API. The engine is deliberately thin: all real logic lives
in :mod:`planner_critic.loop`.
"""

from __future__ import annotations

from .domains.base import DomainPack
from .gates import run_deterministic_gates
from .ledger import PreconditionLedger
from .loop import LoopConfig, LoopResult, run_loop
from .posture import PostureResolver
from .quota import BlastRadiusQuotaConfig, BlastRadiusQuotaGate
from .redaction import SecretsRedactor
from .roles import CriticRole, PlannerRole
from .run_budget import RunBudget
from .schema.goal import Goal
from .schema.plan import PlanVersion
from .types import Finding


class Engine:
    """Configuration-bound wrapper around the planning loop.

    Args:
        planner: The planner role the engine will use for every goal.
        critic: The critic role the engine will use for every goal.
        config: Loop tuning (mode + revision cap); defaults to
            deterministic-first with cap 3.
        domain_pack: Optional domain pack whose gates run *in addition*
            to the built-in six, and whose prompt template is prepended
            to the critic system prompt.
        posture_resolver: Optional context-aware posture resolver.
        run_budget: Optional run-level budget ceilings.
        precondition_ledger: Optional deterministic precondition store.
        redactor: Optional secrets redactor for output surfaces.
        quota_config: Optional blast-radius quota configuration.
    """

    def __init__(
        self,
        planner: PlannerRole,
        critic: CriticRole,
        config: LoopConfig | None = None,
        domain_pack: DomainPack | None = None,
        posture_resolver: PostureResolver | None = None,
        run_budget: RunBudget | None = None,
        precondition_ledger: PreconditionLedger | None = None,
        redactor: SecretsRedactor | None = None,
        quota_config: BlastRadiusQuotaConfig | None = None,
    ) -> None:
        """Bind a ready-to-run engine to its roles, config, and optional packs."""
        self.planner = planner
        self.critic = critic
        self.config = config or LoopConfig()
        self.domain_gates = list(domain_pack.gate_evaluators) if domain_pack else []
        self.domain_critic_prompt = domain_pack.critic_prompt_template if domain_pack else None
        self.posture_resolver = posture_resolver
        self.run_budget = run_budget
        self.precondition_ledger = precondition_ledger
        self.redactor = redactor
        self.quota_config = quota_config

        if self.quota_config is not None:
            self.domain_gates.append(BlastRadiusQuotaGate(self.quota_config))

    def run_domain_gates(self, plan: PlanVersion) -> list[Finding]:
        """Run both built-in six gates and domain/quotas gates (if any).

        Args:
            plan: The typed plan to audit.

        Returns:
            Findings from built-in gates followed by extra-gate findings.
        """
        return run_deterministic_gates(plan, extra_gates=self.domain_gates)

    def plan(self, goal: Goal) -> LoopResult:
        """Plan a goal end-to-end.

        Resolves posture, applies redaction, and passes M6 safety
        subsystems into the loop.

        Args:
            goal: The typed planning request.

        Returns:
            The loop outcome (approved plan or escalated question).
        """
        if self.posture_resolver is not None:
            resolved = self.posture_resolver.resolve(goal.risk_tolerance)
            goal = goal.model_copy(update={"risk_tolerance": resolved.posture})

        return run_loop(
            goal=goal,
            planner=self.planner,
            critic=self.critic,
            config=self.config,
            extra_gates=self.domain_gates,
            run_budget=self.run_budget,
            precondition_ledger=self.precondition_ledger,
            redactor=self.redactor,
        )
