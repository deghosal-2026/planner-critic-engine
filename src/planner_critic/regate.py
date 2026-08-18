"""Re-gate module (F-19): precondition re-verification at execution time.

The re-gate checks whether preconditions that were true at planning time
still hold when a task is about to execute. It runs probes against live
state and reports which preconditions are stale. The caller (adapter layer)
decides whether to replan based on the goal's ``replan_policy``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, cast

from .probe.base import ProbeKind, ProbeRequest, run_probe
from .schema.plan import Task
from .store.base import PlanStore
from .types import ApprovedPlan


@dataclass
class ReGateConfig:
    """Configuration for the re-gate.

    Attributes:
        mode: ``"off"`` to skip all precondition checks; ``"before-each-step"``
            to re-verify preconditions before every task execution.
    """

    mode: Literal["before-each-step", "off"] = "off"


@dataclass
class ReGateResult:
    """The outcome of a re-gate check.

    Attributes:
        status: ``"pass"`` if every precondition with a probe held;
            ``"stale"`` if at least one precondition failed.
        stale_preconditions: Descriptions of preconditions whose probe did
            not match live state.
        replan_triggered: Always ``False`` in this module — the caller
            decides whether to replan.
    """

    status: Literal["pass", "stale"]
    stale_preconditions: list[str] = field(default_factory=list)
    replan_triggered: bool = False


def check_preconditions(
    approved: ApprovedPlan,
    task_id: str,
    store: PlanStore,
    config: ReGateConfig | None = None,
) -> ReGateResult:
    """Re-verify preconditions for a task against live state.

    Args:
        approved: The approved plan the task belongs to.
        task_id: Which task to check.
        store: Unused in this implementation; kept for API compatibility
            with future store-based preconditions.
        config: Re-gate configuration; defaults to ``off``.

    Returns:
        A :class:`ReGateResult` summarising which preconditions (if any)
        are stale.

    Raises:
        ValueError: If ``task_id`` is not found in the approved plan.
    """
    cfg = config or ReGateConfig()

    if cfg.mode == "off":
        return ReGateResult(status="pass")

    task = _find_task(approved, task_id)

    stale: list[str] = []
    for precondition in task.preconditions:
        probe = precondition.probe
        if probe is None:
            continue
        request = ProbeRequest(
            kind=cast(ProbeKind, probe.kind),
            query=probe.query,
            expected=probe.expected,
        )
        result = run_probe(request)
        if not result.matched:
            stale.append(precondition.description)

    if stale:
        return ReGateResult(status="stale", stale_preconditions=stale)

    return ReGateResult(status="pass")


def _find_task(approved: ApprovedPlan, task_id: str) -> Task:
    """Look up a task by id; raises ValueError if not found."""
    for task in approved.plan.tasks:
        if task.id == task_id:
            return task
    raise ValueError(f"task '{task_id}' not found in plan '{approved.plan.id}'")
