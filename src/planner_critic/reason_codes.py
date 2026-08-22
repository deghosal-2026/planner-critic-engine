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

# --- Deterministic auto-fix codes (PRD §2.6, M2) ------------------------------
AUTO_REPAIRED_ORDERING: Literal["auto_repaired_ordering"] = "auto_repaired_ordering"
AUTO_CLOSED_PRECONDITION: Literal["auto_closed_precondition"] = "auto_closed_precondition"
PLAN_OSCILLATION_DETECTED: Literal["plan_oscillation_detected"] = "plan_oscillation_detected"
AUTO_CONVERGE_PARTIAL_APPROVAL: Literal["auto_converge_partial_approval"] = (
    "auto_converge_partial_approval"
)
POLICY_EVALUATION_ERROR: Literal["policy_evaluation_error"] = "policy_evaluation_error"
POLICY_VIOLATION: Literal["policy_violation"] = "policy_violation"

# --- Domain pack reason codes (M4) --------------------------------------------
SECOPS_ISOLATION_WITHOUT_TRAFFIC_DRAIN: Literal["secops_isolation_without_traffic_drain"] = (
    "secops_isolation_without_traffic_drain"
)
SECOPS_FORENSIC_ORDER_VIOLATION: Literal["secops_forensic_order_violation"] = (
    "secops_forensic_order_violation"
)
SECOPS_BROAD_PRIVILEGE_WITHOUT_HITL: Literal["secops_broad_privilege_without_hitl"] = (
    "secops_broad_privilege_without_hitl"
)
SUPPLY_CHAIN_LOCKFILE_NOT_REGENERATED: Literal["supply_chain_lockfile_not_regenerated"] = (
    "supply_chain_lockfile_not_regenerated"
)
SUPPLY_CHAIN_BREAKING_CHANGE_WITHOUT_MIGRATION: Literal[
    "supply_chain_breaking_change_without_migration"
] = "supply_chain_breaking_change_without_migration"
SUPPLY_CHAIN_UNSIGNED_ARTIFACT: Literal["supply_chain_unsigned_artifact"] = (
    "supply_chain_unsigned_artifact"
)
SUPPLY_CHAIN_MISSING_SBOM: Literal["supply_chain_missing_sbom"] = (
    "supply_chain_missing_sbom"
)
FINOPS_DELETE_WITHOUT_GRACE_PERIOD: Literal["finops_delete_without_grace_period"] = (
    "finops_delete_without_grace_period"
)
FINOPS_BUDGET_BOUNDARY_BREACHED: Literal["finops_budget_boundary_breached"] = (
    "finops_budget_boundary_breached"
)
DATA_ENG_DESTRUCTIVE_WITHOUT_BACKUP: Literal["data_eng_destructive_without_backup"] = (
    "data_eng_destructive_without_backup"
)
DATA_ENG_MIGRATION_OUTSIDE_MAINTENANCE_WINDOW: Literal[
    "data_eng_migration_outside_maintenance_window"
] = "data_eng_migration_outside_maintenance_window"
DATA_ENG_MIGRATION_WITHOUT_DUAL_WRITE: Literal["data_eng_migration_without_dual_write"] = (
    "data_eng_migration_without_dual_write"
)
DATA_ENG_MIGRATION_WITHOUT_FALLBACK: Literal["data_eng_migration_without_fallback"] = (
    "data_eng_migration_without_fallback"
)
ROLLBACK_DAG_GENERATED: Literal["rollback_dag_generated"] = "rollback_dag_generated"
ROLLBACK_EXECUTION_TRIGGERED: Literal["rollback_execution_triggered"] = (
    "rollback_execution_triggered"
)
ROLLBACK_NON_REVERSIBLE_STEP_SKIPPED: Literal["rollback_non_reversible_step_skipped"] = (
    "rollback_non_reversible_step_skipped"
)
ROLLBACK_MISSING_ACTION_MAPPING: Literal["rollback_missing_action_mapping"] = (
    "rollback_missing_action_mapping"
)

# --- Loop decision codes (PRD §2.6) ------------------------------------------
REVISION_CAP_REACHED: Literal["revision_cap_reached"] = "revision_cap_reached"
CONVERGED_STALLED: Literal["converged_stalled"] = "converged_stalled"
REGRESSION_THRASHING: Literal["regression_thrashing"] = "regression_thrashing"
BUDGET_EXCEEDED: Literal["budget_exceeded"] = "budget_exceeded"
REPLAN_ABORTED: Literal["replan_aborted"] = "replan_aborted"
APPROVED: Literal["approved"] = "approved"
PLANNING_UNAVAILABLE: Literal["planning_unavailable"] = "planning_unavailable"

# --- Approval / fail-closed codes -------------------------------------------
APPROVAL_THRESHOLD_NOT_MET: Literal["approval_threshold_not_met"] = "approval_threshold_not_met"

# --- LLM critic heuristic codes (PRD §2.5.1, F-80) ---------------------------
LLM_FEASIBILITY: Literal["llm_feasibility"] = "llm_feasibility"
LLM_RISK: Literal["llm_risk"] = "llm_risk"
LLM_MISSING_STEPS: Literal["llm_missing_steps"] = "llm_missing_steps"
LLM_UNSAFE_SEQUENCING: Literal["llm_unsafe_sequencing"] = "llm_unsafe_sequencing"
LLM_UNVERIFIED_DEPENDENCIES: Literal["llm_unverified_dependencies"] = "llm_unverified_dependencies"
LLM_WEAK_ROLLBACK: Literal["llm_weak_rollback"] = "llm_weak_rollback"

ReasonCode: TypeAlias = Literal[
    "plan_schema_invalid",
    "dependency_cycle",
    "unsafe_ordering",
    "missing_verification",
    "missing_rollback",
    "unverified_precondition",
    "unsafe_parallelization",
    "auto_repaired_ordering",
    "auto_closed_precondition",
    "plan_oscillation_detected",
    "auto_converge_partial_approval",
    "policy_evaluation_error",
    "policy_violation",
    "secops_isolation_without_traffic_drain",
    "secops_forensic_order_violation",
    "secops_broad_privilege_without_hitl",
    "supply_chain_lockfile_not_regenerated",
    "supply_chain_breaking_change_without_migration",
    "supply_chain_unsigned_artifact",
    "supply_chain_missing_sbom",
    "finops_delete_without_grace_period",
    "finops_budget_boundary_breached",
    "data_eng_destructive_without_backup",
    "data_eng_migration_outside_maintenance_window",
    "data_eng_migration_without_dual_write",
    "data_eng_migration_without_fallback",
    "rollback_dag_generated",
    "rollback_execution_triggered",
    "rollback_non_reversible_step_skipped",
    "rollback_missing_action_mapping",
    "revision_cap_reached",
    "converged_stalled",
    "regression_thrashing",
    "budget_exceeded",
    "replan_aborted",
    "approved",
    "planning_unavailable",
    "approval_threshold_not_met",
    "llm_feasibility",
    "llm_risk",
    "llm_missing_steps",
    "llm_unsafe_sequencing",
    "llm_unverified_dependencies",
    "llm_weak_rollback",
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
    AUTO_REPAIRED_ORDERING: "Auto-repaired task ordering to satisfy hard-dependency precedences",
    AUTO_CLOSED_PRECONDITION: "Auto-closed a precondition gap from a template match",
    PLAN_OSCILLATION_DETECTED: "Plan oscillates between two structural signatures — no convergence",
    AUTO_CONVERGE_PARTIAL_APPROVAL: (
        "Auto-converged non-oscillating tasks; oscillating subset escalated"
    ),
    POLICY_EVALUATION_ERROR: "An external policy evaluation failed or the runtime was unavailable",
    POLICY_VIOLATION: "A policy-as-code rule produced a violation",
    SECOPS_ISOLATION_WITHOUT_TRAFFIC_DRAIN: "Isolation step without prior traffic drain",
    SECOPS_FORENSIC_ORDER_VIOLATION: "Destructive action before forensic preservation",
    SECOPS_BROAD_PRIVILEGE_WITHOUT_HITL: "Broad privilege escalation without human approval",
    SUPPLY_CHAIN_LOCKFILE_NOT_REGENERATED: "Manifest edited without lockfile regeneration",
    SUPPLY_CHAIN_BREAKING_CHANGE_WITHOUT_MIGRATION: "Major semver bump without migration/linter",
    SUPPLY_CHAIN_UNSIGNED_ARTIFACT: "Deploy of unsigned artifact",
    SUPPLY_CHAIN_MISSING_SBOM: "Deploy without generated SBOM",
    FINOPS_DELETE_WITHOUT_GRACE_PERIOD: "Instant delete without snapshot/notify/wait",
    FINOPS_BUDGET_BOUNDARY_BREACHED: "Expansion breaches localized budget cap",
    DATA_ENG_DESTRUCTIVE_WITHOUT_BACKUP: "Destructive query without verified backup",
    DATA_ENG_MIGRATION_OUTSIDE_MAINTENANCE_WINDOW: "Migration outside maintenance window",
    DATA_ENG_MIGRATION_WITHOUT_DUAL_WRITE: "Live migration without dual-write",
    DATA_ENG_MIGRATION_WITHOUT_FALLBACK: "Live migration without fallback path",
    ROLLBACK_DAG_GENERATED: "Rollback DAG generated at approval time",
    ROLLBACK_EXECUTION_TRIGGERED: "Rollback execution triggered on failure",
    ROLLBACK_NON_REVERSIBLE_STEP_SKIPPED: "Non-reversible step skipped during rollback",
    ROLLBACK_MISSING_ACTION_MAPPING: "Forward action has no rollback mapping",
    REVISION_CAP_REACHED: "Loop terminated because the revision cap was hit",
    CONVERGED_STALLED: "Revisions are circling the same blockers or diff converges to zero",
    REGRESSION_THRASHING: "A revision introduced a new blocker",
    BUDGET_EXCEEDED: "The per-goal spend budget was exceeded",
    REPLAN_ABORTED: "replan_policy=abort: the loop escalated without revising",
    APPROVED: "Loop terminated by meeting the approval threshold",
    PLANNING_UNAVAILABLE: "A provider failed; planning is unavailable and must fail closed",
    APPROVAL_THRESHOLD_NOT_MET: "Findings do not meet the goal's risk-tolerance threshold",
    LLM_FEASIBILITY: "LLM critic: task is not achievable with the stated environment/tools",
    LLM_RISK: "LLM critic: risk/blast-radius exceeds the goal's tolerance",
    LLM_MISSING_STEPS: "LLM critic: an obvious prerequisite or step is missing",
    LLM_UNSAFE_SEQUENCING: "LLM critic: ordering or parallelization breaks safety",
    LLM_UNVERIFIED_DEPENDENCIES: "LLM critic: a step depends on a fact never established earlier",
    LLM_WEAK_ROLLBACK: "LLM critic: a high-blast-radius step lacks sound rollback coverage",
}

# All valid codes; a test asserts every produced reason code is in this set.
ALL_REASON_CODES: frozenset[ReasonCode] = frozenset(REASON_CODE_DESCRIPTIONS)
