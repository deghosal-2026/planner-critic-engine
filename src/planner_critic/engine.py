"""The Engine facade — a single convenience entry point into the loop.

Wraps :func:`planner_critic.loop.run_loop` with a fixed role pair and
configuration so a consumer can ``Engine(...).plan(goal)`` without touching
the procedural API. The engine is deliberately thin: all real logic lives
in :mod:`planner_critic.loop`.
"""

from __future__ import annotations

from .loop import LoopConfig, LoopResult, run_loop
from .roles import CriticRole, PlannerRole
from .schema.goal import Goal


class Engine:
    """Configuration-bound wrapper around the planning loop.

    Args:
        planner: The planner role the engine will use for every goal.
        critic: The critic role the engine will use for every goal.
        config: Loop tuning (mode + revision cap); defaults to
            deterministic-first with cap 3.
    """

    def __init__(
        self,
        planner: PlannerRole,
        critic: CriticRole,
        config: LoopConfig | None = None,
    ) -> None:
        """Bind a ready-to-run engine to its roles and config."""
        self.planner = planner
        self.critic = critic
        self.config = config or LoopConfig()

    def plan(self, goal: Goal) -> LoopResult:
        """Plan a goal end-to-end.

        Args:
            goal: The typed planning request.

        Returns:
            The loop outcome (approved plan or escalated question).
        """
        return run_loop(
            goal=goal,
            planner=self.planner,
            critic=self.critic,
            config=self.config,
        )
