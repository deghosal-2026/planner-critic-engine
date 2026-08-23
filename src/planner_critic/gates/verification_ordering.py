"""verification_ordering gate — a verified mutation's verification must not be vacuous (#219).

A high-blast-radius task that carries a :class:`VerificationStep` is asserting
"after my action runs, this check proves the result". That assertion is only
meaningful if no consumer of the mutated state acts before the verification
point. This gate pins the **inline-after-task** semantics: a task's
verification executes immediately after its own action, before the next
linear task begins.

Under those semantics two deterministic cases make the verification vacuous:

* **Reversed order** — a hard-dependency consumer ``U`` of high-risk task
  ``T`` appears *before* ``T`` in linear order. ``U`` acted on the
  pre-mutation state and ``T``'s verification can never bless what ``U``
  consumed. (``ordering_sane`` also fires on this shape; both findings are
  kept because they report different defects — the ordering violation and
  the verification-staleness consequence.)
* **Parallel race** — a sibling ``U`` shares ``T``'s ``parallel_group`` and
  mutates the same ``target``. Group members run concurrently, so ``U`` may
  overwrite the target before ``T``'s verification executes.

Both fire as a gate-layer BLOCKER with reason code
:data:`~planner_critic.reason_codes.VERIFICATION_AFTER_CONSUMER` — the LLM
critic never votes on it, closing the under-claim direction at this seam.
"""

from __future__ import annotations

from ..reason_codes import VERIFICATION_AFTER_CONSUMER
from ..schema.plan import PlanVersion, Task
from ..types import Finding, Severity
from .base import BaseGate


def _is_high_blast(task: Task) -> bool:
    """True when the task is high-risk by risk_class or blast_radius."""
    return task.risk_class.is_high_risk or task.blast_radius in ("high", "critical")


class Gate(BaseGate):
    """Flags consumers that run ahead of a verified high-risk mutation."""

    name = "verification_ordering"

    def run(self, plan: PlanVersion) -> list[Finding]:
        """Check every verified high-risk task for vacuous-verification orderings.

        Args:
            plan: The typed plan to audit.

        Returns:
            One finding per offending consumer task. Empty when every
            consumer of a verified high-risk mutation runs after its
            verification point.
        """
        id_to_index = {task.id: index for index, task in enumerate(plan.tasks)}
        findings: list[Finding] = []

        for producer in plan.tasks:
            if not _is_high_blast(producer) or producer.verification is None:
                continue

            # Hard-dependency consumers positioned before their verified
            # producer consumed pre-mutation state.
            for dep in plan.dependencies:
                if dep.from_task != producer.id or dep.kind.value != "hard":
                    continue
                consumer_id = dep.to_task
                if consumer_id not in id_to_index:
                    continue
                if id_to_index[consumer_id] < id_to_index[producer.id]:
                    findings.append(self._finding(plan, consumer_id, producer.id))

            # Same-group siblings racing the same target may complete before
            # the producer's verification executes.
            if producer.parallel_group is None:
                continue
            for sibling in plan.tasks:
                if (
                    sibling.id != producer.id
                    and sibling.parallel_group == producer.parallel_group
                    and sibling.target == producer.target
                    and sibling.id in id_to_index
                ):
                    findings.append(
                        self._finding(
                            plan,
                            sibling.id,
                            producer.id,
                            detail=f"parallel group {producer.parallel_group!r}",
                        )
                    )
        return findings

    def _finding(
        self,
        plan: PlanVersion,
        consumer_id: str,
        producer_id: str,
        *,
        detail: str = "",
    ) -> Finding:
        """Build one VERIFICATION_AFTER_CONSUMER blocker."""
        where = f" ({detail})" if detail else ""
        return Finding(
            id=f"verification_ordering:{plan.id}:{plan.version}:{consumer_id}",
            task_id=consumer_id,
            version=plan.version,
            severity=Severity.BLOCKER,
            reason_code=VERIFICATION_AFTER_CONSUMER,
            message=(
                f"task {consumer_id!r}{where} consumes the state produced by "
                f"high-risk task {producer_id!r} without waiting for its "
                f"verification point"
            ),
            suggested_fix=(
                f"Order task {consumer_id!r} after {producer_id!r}'s verification "
                f"(or move it out of parallel group {producer_id!r} shares)"
            ),
        )


__all__ = ["Gate"]
