"""The regression guard (PRD §2.6(d)) — a revision introduced a new blocker.

The planner is thrashing when a revision *adds* a blocker that did not exist
in the prior revision. Escalating here stops an unproductive loop and keeps
the audit trail honest.
"""

from __future__ import annotations

from ..types import Finding, Severity


def regression_detected(prior: list[Finding], current: list[Finding]) -> bool:
    """True when the current revision regressed vs the prior one.

    "Introduces a new blocker" ⟺ a blocker reason-code/task pair appears in
    ``current`` that was absent from ``prior``.

    Args:
        prior: Findings from the previous revision.
        current: Findings from the current revision.

    Returns:
        True when ``current`` has a blocker key that ``prior`` did not.
    """
    if not prior:
        return False

    def blocker_keys(findings: list[Finding]) -> set[tuple[str, str | None]]:
        return {
            (f.reason_code, f.task_id)
            for f in findings
            if f.severity is Severity.BLOCKER
        }

    prior_keys = blocker_keys(prior)
    current_keys = blocker_keys(current)
    return bool(current_keys.difference(prior_keys))
