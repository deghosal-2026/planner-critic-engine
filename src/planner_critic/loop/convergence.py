"""Convergence detection (PRD §2.6: "revisions circling the same blockers").

Escalates early when the loop is making no progress:

* **Circling blockers** — the revision did not change the blocker set
  between consecutive revisions.
* **Near-zero diff** — the newest revision is structurally identical to the
  previous one (same task ids, same dependency set, same branch shapes), so
  further revisions will never diverge.
"""

from __future__ import annotations

from ..schema.plan import PlanVersion
from ..types import Finding, Severity


def _plan_fingerprint(plan: PlanVersion) -> str:
    """Stable structural fingerprint of a plan revision.

    Two fingerprints equal ⟺ the plans have identical task ids, dependency
    edges, and branch shapes (ignoring noise like ``created_at``).

    Args:
        plan: The plan to fingerprint.

    Returns:
        A canonical string identifying the plan's structure.
    """
    tasks = ",".join(sorted(task.id for task in plan.tasks))
    deps = ",".join(
        sorted(f"{d.from_task}>{d.to_task}" for d in plan.dependencies)
    )
    branches = ",".join(
        sorted(
            f"{b.id}:{sorted(b.tasks)}:{b.join}"
            for b in plan.branches
        )
    )
    return f"{tasks}|{deps}|{branches}"


def circling_blockers(prior: list[Finding], current: list[Finding]) -> bool:
    """True when the blocker set did not change between revisions.

    Args:
        prior: Findings from the previous revision.
        current: Findings from the current revision.

    Returns:
        True when both revisions flag the same blocker reason-codes on the
        same tasks — the planner is circling.
    """
    def blocker_keys(findings: list[Finding]) -> frozenset[tuple[str, str | None]]:
        return frozenset(
            (f.reason_code, f.task_id)
            for f in findings
            if f.severity is Severity.BLOCKER
        )

    if not prior or not current:
        return False
    return blocker_keys(prior) == blocker_keys(current) and bool(blocker_keys(current))


def near_zero_diff(prior: PlanVersion | None, current: PlanVersion) -> bool:
    """True when the current revision is structurally identical to the prior.

    Args:
        prior: The prior revision, or None on the first pass.
        current: The current revision.

    Returns:
        True when there is no prior plan, or when fingerprints match.
    """
    if prior is None:
        return False
    return _plan_fingerprint(prior) == _plan_fingerprint(current)


def stalled(
    prior: PlanVersion | None,
    prior_findings: list[Finding],
    current: PlanVersion,
    current_findings: list[Finding],
) -> bool:
    """Combine the two convergence signals into one decision.

    Args:
        prior: The prior plan revision (None on first pass).
        prior_findings: Findings from the prior revision.
        current: The current plan revision.
        current_findings: Findings from the current revision.

    Returns:
        True when the loop should escalate for stalled progress.
    """
    return circling_blockers(prior_findings, current_findings) or near_zero_diff(
        prior, current
    )
