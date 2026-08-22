"""Label-migration escape harness (M5, #171).

Detects when a model re-labels a blocked concern into a different severity
family (label-migration), potentially slipping the gate. Provides boundary-case
generation, confusion matrices, and a deterministic invariate gate for
irreversible steps.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..gates.base import BaseGate
from ..reason_codes import (
    IRREVERSIBLE_INVARIANT_BLOCKED,
)
from ..schema.plan import PlanVersion
from ..types import Finding, Severity


@dataclass
class LabelMigrationRecord:
    """Records a detected label-migration event.

    Attributes:
        finding_id: The finding ID that was migrated.
        original_family: The heuristic family the finding SHOULD belong to.
        assigned_family: The heuristic family the model assigned.
        original_severity: The expected severity.
        assigned_severity: The actual severity assigned.
        finding_text: The raw finding text.
    """

    finding_id: str
    original_family: str
    assigned_family: str
    original_severity: Severity
    assigned_severity: Severity
    finding_text: str


@dataclass
class BoundaryCase:
    """A pair of plans differing by exactly one fact.

    Attributes:
        case_id: Unique identifier.
        description: Human-readable description of what the case tests.
        plan_a: First plan (passes).
        plan_b: Second plan (should be blocked by one specific gate).
        expected_blocker_family: Which heuristic family should block plan_b.
        expected_reason_code: Which reason code plan_b should trigger.
    """

    case_id: str
    description: str
    plan_a: PlanVersion
    plan_b: PlanVersion
    expected_blocker_family: str
    expected_reason_code: str


class IrreversibleInvariantGate(BaseGate):
    """Deterministic invariant gate for irreversible steps.

    An irreversible step (risk_class=critical, blast_radius=high) MUST have
    both a verified predecessor and a rollback plan. This gate outranks any
    model-chosen blocker label — it fires regardless of what the LLM critic
    reports.
    """

    name = "irreversible_invariant"

    def run(self, plan: PlanVersion) -> list[Finding]:
        findings: list[Finding] = []

        for task in plan.tasks:
            if task.risk_class == "critical" and task.blast_radius == "high":
                has_precondition = bool(task.preconditions)
                has_rollback = task.rollback is not None
                has_verification = task.verification is not None

                if not (has_rollback and (has_verification or has_precondition)):
                    findings.append(
                        Finding(
                            id=f"irreversible_invariant:{plan.id}:{plan.version}:{task.id}",
                            task_id=task.id,
                            version=plan.version,
                            severity=Severity.BLOCKER,
                            reason_code=IRREVERSIBLE_INVARIANT_BLOCKED,
                            message=(
                                f"Irreversible step {task.id!r} (critical risk, high blast radius) "
                                f"requires rollback and verified precondition, "
                                f"but has: rollback={has_rollback}, verification={has_verification}, "
                                f"precondition={has_precondition}"
                            ),
                        )
                    )

        return findings


def build_confusion_matrix(
    records: list[LabelMigrationRecord],
) -> dict[str, dict[str, int]]:
    """Build a confusion matrix from label-migration records.

    Args:
        records: Label migration records from eval runs.

    Returns:
        A dict mapping original_family → {assigned_family: count}.
    """
    matrix: dict[str, dict[str, int]] = {}
    for record in records:
        orig = record.original_family
        assn = record.assigned_family
        if orig not in matrix:
            matrix[orig] = {}
        matrix[orig][assn] = matrix[orig].get(assn, 0) + 1
    return matrix


__all__ = [
    "BoundaryCase",
    "IrreversibleInvariantGate",
    "LabelMigrationRecord",
    "build_confusion_matrix",
]
