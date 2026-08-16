"""Stable machine-readable reason-code catalog (F-77).

Every deterministic gate and every loop decision maps to a stable code so
downstream tooling (escalation UI, forensics, field-test reports) can key on
``reason_code`` instead of brittle message parsing. Add codes here first,
then reference the constant — never inline a string literal in gate/loop code.

Each constant carries its precise ``Literal`` type so ``mypy --strict``
verifies every finding/decision uses a code that actually exists in the
catalog.
"""

from __future__ import annotations

from typing import Literal, TypeAlias

# --- Deterministic gate codes (per PRD §2.5.2) ------------------------------
PLAN_SCHEMA_INVALID: Literal["plan_schema_invalid"] = "plan_schema_invalid"
DEPENDENCY_CYCLE: Literal["dependency_cycle"] = "dependency_cycle"
UNSAFE_ORDERING: Literal["unsafe_ordering"] = "unsafe_ordering"
MISSING_VERIFICATION: Literal["missing_verification"] = "missing_verification"
MISSING_ROLLBACK: Literal["missing_rollback"] = "missing_rollback"
UNVERIFIED_PRECONDITION: Literal["unverified_precondition"] = "unverified_precondition"
UNSAFE_PARALLELIZATION: Literal["unsafe_parallelization"] = "unsafe_parallelization"

# --- Loop decision codes (PRD §2.6) ------------------------------------------
REVISION_CAP_REACHED: Literal["revision_cap_reached"] = "revision_cap_reached"
CONVERGED_STALLED: Literal["converged_stalled"] = "converged_stalled"
REGRESSION_THRASHING: Literal["regression_thrashing"] = "regression_thrashing"
BUDGET_EXCEEDED: Literal["budget_exceeded"] = "budget_exceeded"
APPROVED: Literal["approved"] = "approved"
PLANNING_UNAVAILABLE: Literal["planning_unavailable"] = "planning_unavailable"

# --- Approval / fail-closed codes -------------------------------------------
APPROVAL_THRESHOLD_NOT_MET: Literal["approval_threshold_not_met"] = "approval_threshold_not_met"

ReasonCode: TypeAlias = Literal[
    "plan_schema_invalid",
    "dependency_cycle",
    "unsafe_ordering",
    "missing_verification",
    "missing_rollback",
    "unverified_precondition",
    "unsafe_parallelization",
    "revision_cap_reached",
    "converged_stalled",
    "regression_thrashing",
    "budget_exceeded",
    "approved",
    "planning_unavailable",
    "approval_threshold_not_met",
]

# Descriptions are the source of truth for docs and any generated API reference.
REASON_CODE_DESCRIPTIONS: dict[ReasonCode, str] = {
    PLAN_SCHEMA_INVALID: "Plan does not parse against the typed schema",
    DEPENDENCY_CYCLE: "Dependency graph contains a cycle (not a DAG)",
    UNSAFE_ORDERING: "A task is ordered before a hard dependency",
    MISSING_VERIFICATION: "A high-blast-radius step lacks a verification step",
    MISSING_ROLLBACK: "A high-blast-radius step lacks a rollback step",
    UNVERIFIED_PRECONDITION: "A precondition does not reference an established earlier fact",
    UNSAFE_PARALLELIZATION: "Tasks in one parallel_group break concurrency safety",
    REVISION_CAP_REACHED: "Loop terminated because the revision cap was hit",
    CONVERGED_STALLED: "Revisions are circling the same blockers or diff converges to zero",
    REGRESSION_THRASHING: "A revision introduced a new blocker",
    BUDGET_EXCEEDED: "The per-goal spend budget was exceeded",
    APPROVED: "Loop terminated by meeting the approval threshold",
    PLANNING_UNAVAILABLE: "A provider failed; planning is unavailable and must fail closed",
    APPROVAL_THRESHOLD_NOT_MET: "Findings do not meet the goal's risk-tolerance threshold",
}

# All valid codes; a test asserts every produced reason code is in this set.
ALL_REASON_CODES: frozenset[ReasonCode] = frozenset(REASON_CODE_DESCRIPTIONS)
