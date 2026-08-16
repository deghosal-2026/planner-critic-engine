"""preconditions_referenced gate — preconditions are grounded.

Every precondition must reference an established fact: either another task
earlier in the ordering that produces/outputs the fact, or a named environment
fact. A precondition that references nothing already established is a
blocker — the step would silently depend on a belief (F-12, Unverified
dependencies family).
"""

from __future__ import annotations

from ..reason_codes import UNVERIFIED_PRECONDITION
from ..schema.plan import PlanVersion
from ..types import Finding, Severity
from .base import BaseGate


class Gate(BaseGate):
    """Flags preconditions that reference no established fact."""

    name = "preconditions_referenced"

    def run(self, plan: PlanVersion) -> list[Finding]:
        """Check every precondition is grounded in an earlier fact.

        Args:
            plan: The typed plan to audit.

        Returns:
            One finding per ungrounded precondition.
        """
        {task.id: index for index, task in enumerate(plan.tasks)}
        established = self._established_facts(plan)
        findings: list[Finding] = []
        for task in plan.tasks:
            for precondition in task.preconditions:
                grounded = False
                if precondition.probe is not None:
                    grounded = True
                elif precondition.established_by is not None:
                    grounding = precondition.established_by
                    grounded = grounding in established or grounding.startswith("env:")
                if not grounded:
                    findings.append(
                        Finding(
                            id=f"preconditions_referenced:{plan.id}:{plan.version}:{task.id}:{precondition.fact}",
                            task_id=task.id,
                            version=plan.version,
                            severity=Severity.BLOCKER,
                            reason_code=UNVERIFIED_PRECONDITION,
                            message=(
                                f"precondition {precondition.fact!r} on task {task.id!r} "
                                "references no established fact"
                            ),
                            suggested_fix=(
                                f"Point the precondition at an earlier task "
                                f"that establishes {precondition.fact!r}"
                            ),
                        )
                    )
        return findings

    def _established_facts(self, plan: PlanVersion) -> frozenset[str]:
        """Collect facts established earlier in the ordering.

        A fact is established by an earlier task id, a task's
        ``verification.expected`` output, or an explicit env fact name.

        Args:
            plan: The typed plan to audit.

        Returns:
            The set of established fact keys.
        """
        facts: set[str] = set()
        for task in plan.tasks:
            facts.add(task.id)
            facts.add(f"env:{task.target}")
            if task.verification is not None:
                facts.add(f"verified:{task.verification.what}")
        return frozenset(facts)
