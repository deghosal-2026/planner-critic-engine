"""The loop controller (F-05..F-08, F-13) — verbatim §2.6.1 pseudocode.

The controller orchestrates planner, deterministic gates, critic, and the
termination logic. It is **deterministic on identical inputs** (F-74): given
the same planner/critic outputs, the same loop decisions (approve/revise/
escalate) result. CI asserts this via the acceptance matrix
(``tests/fixtures/loop_matrix.yaml``).

```text
function run_loop(goal, planner, critic, config):
    plan_v = planner.decompose(goal)
    for revision in 1..config.revision_cap:
        gates = deterministic_gates(plan_v)             # free, always run
        if critic.mode == "deterministic-first":
            if gates.has_blocker():
                plan_v = planner.revise(plan_v, gates.as_findings()); continue
            findings = gates.as_findings() + critic.audit(plan_v)  # LLM
        else:                                            # llm-every-revision
            findings = gates.as_findings() + critic.audit(plan_v)
        if meets_threshold(findings, goal.risk_tolerance): return Approved(plan_v)
        if budget_exceeded(goal.budget): return Escalate(budget)
        if regression_detected(findings, prior_findings): return Escalate(thrashing)
        if converged(plan_v, prior_plan): return Escalate(stalled)
        prior_plan, prior_findings = plan_v, findings
        plan_v = planner.revise(plan_v, findings)
    return Escalate(revision_cap)
```

M1 keeps the loop model-agnostic (fake roles in tests, real ones later) and
store-less. Escalation surfaces a precise question so the escalation manager
can present it to a human.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal, cast

from ..approval import ApprovalGate, meets_threshold, resolve_threshold
from ..critique.diff import scope_between
from ..critique.mode import CriticMode, should_invoke_llm
from ..gates import run_deterministic_gates
from ..reason_codes import ReasonCode
from ..roles import CriticRole, PlannerRole
from ..schema.goal import Goal, ReplanPolicy
from ..schema.plan import PlanVersion
from ..types import ApprovedPlan, Escalation, Finding, PlanningError, Severity
from .budget import SpendState, budget_exceeded
from .convergence import stalled
from .regression import regression_detected

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoopConfig:
    """Deterministic tuning of the revise-until-approved loop."""

    mode: CriticMode = "deterministic-first"
    revision_cap: int = 3

    @staticmethod
    def from_env() -> LoopConfig:
        """Build a LoopConfig from PC_* environment variables.

        Env vars:
            PC_CRITIQUE_MODE: one of heuristic-only|deterministic-first|llm-every-revision
            PC_REVISION_CAP: positive integer (default 3)

        Returns:
            A LoopConfig, falling back to defaults on missing/invalid env.
        """
        import os

        from ..critique.mode import validate_mode

        mode_str = os.environ.get("PC_CRITIQUE_MODE", "deterministic-first")
        try:
            mode = validate_mode(mode_str)
        except ValueError:
            logger.warning("invalid PC_CRITIQUE_MODE=%r, using default", mode_str)
            mode = "deterministic-first"

        cap_str = os.environ.get("PC_REVISION_CAP", "3")
        try:
            cap = max(1, int(cap_str))
        except ValueError:
            logger.warning("invalid PC_REVISION_CAP=%r, using default", cap_str)
            cap = 3

        return LoopConfig(mode=mode, revision_cap=cap)


@dataclass
class LoopResult:
    """The consolidated outcome of one ``run_loop`` invocation."""

    status: Literal["approved", "escalated"]
    plan: PlanVersion | None = None
    findings: list[Finding] = field(default_factory=list)
    reason_code: ReasonCode | None = None
    approved_plan: ApprovedPlan | None = None
    escalation: Escalation | None = None
    spend: SpendState | None = None
    mode: Literal["live", "shadow"] = "live"

    @property
    def is_approved(self) -> bool:
        """True when the loop produced an ApprovedPlan."""
        return self.status == "approved"


def run_loop(
    goal: Goal,
    planner: PlannerRole,
    critic: CriticRole,
    config: LoopConfig | None = None,
    spend: SpendState | None = None,
) -> LoopResult:
    """Run the draft → critique → revise → (approve|escalate) loop.

    Args:
        goal: The typed planning request.
        planner: Role that decomposes/revises plans.
        critic: Role that audits plans (returns findings).
        config: Loop tuning (mode + revision cap). Defaults to
            deterministic-first with cap 3.
        spend: Optional spend counter; a fresh one is created when omitted.

    Returns:
        A :class:`LoopResult` — ``approved`` (with an ``ApprovedPlan``) or
        ``escalated`` (with a precise question and reason code).

    Raises:
        PlanningError: When the planner fails to produce a valid plan with a
            failure reason (fail-closed; never continues on garbage).
    """
    cfg = config or LoopConfig()
    state = spend or SpendState()

    result = _run(
        goal=goal,
        planner=planner,
        critic=critic,
        config=cfg,
        state=state,
    )
    result.spend = state
    return result


def _escalate(
    goal: Goal,
    plan: PlanVersion,
    findings: list[Finding],
    reason: ReasonCode,
    index: int,
) -> LoopResult:
    """Build an escalation result with a precise question (M1 form)."""
    blockers = [f for f in findings if f.severity is Severity.BLOCKER]
    question = _compose_question(goal, blockers, reason)
    escalation = Escalation(
        id=f"escalation:{goal.id}:{plan.version}:{index}",
        plan_id=plan.id,
        version=plan.version,
        blocker_finding_id=blockers[0].id if blockers else None,
        question=question,
    )
    return LoopResult(
        status="escalated",
        plan=plan,
        findings=findings,
        reason_code=reason,
        escalation=escalation,
    )


def _compose_question(goal: Goal, blockers: list[Finding], reason: ReasonCode) -> str:
    """Human-readable, precise question for the escalation record."""
    if blockers:
        detail = "; ".join(sorted({f.reason_code for f in blockers}))
        return (
            f"Plan for goal {goal.id!r} cannot be approved: blockers remain "
            f"({detail}). Decide whether to patch, override, or abandon."
        )
    return f"Plan for goal {goal.id!r} did not converge ({reason}). Decide next step."


def _plan_revision(plan: PlanVersion, next_id: str, parent: PlanVersion | None) -> PlanVersion:
    """Wrap a replan result as the next immutable revision.

    Args:
        plan: The planner's replan output (usually derived from the parent).
        next_id: Id to stamp on the new revision.
        parent: The parent revision, or None to stamp from scratch.

    Returns:
        The new revision: fresh id/version/parent link and a fresh
        ``created_at`` so each revision carries its own timestamp.
    """

    data = plan.model_dump()
    data["id"] = next_id
    data["version"] = (parent.version + 1) if parent else 1
    data["parent_version"] = parent.id if parent else None
    data["created_at"] = datetime.now(UTC)
    return PlanVersion.model_validate(data)


def _run(
    goal: Goal,
    planner: PlannerRole,
    critic: CriticRole,
    config: LoopConfig,
    state: SpendState,
) -> LoopResult:
    """Internal deterministic loop body."""
    logger.info(
        "loop start — goal=%s mode=%s revision_cap=%d risk=%s",
        goal.id,
        config.mode,
        config.revision_cap,
        goal.risk_tolerance,
    )
    try:
        logger.info("loop: planner.decompose(goal=%s)", goal.id)
        plan = planner.decompose(goal)
    except Exception as exc:
        logger.error("loop: planner.decompose failed: %s", exc)
        raise PlanningError(f"planner role failed to decompose: {exc}") from exc
    if not isinstance(plan, PlanVersion):
        raise PlanningError(f"planner returned non-PlanVersion: {type(plan).__name__}")

    logger.info(
        "loop: planner produced plan=%s v%d (%d tasks)",
        plan.id,
        plan.version,
        len(plan.tasks),
    )

    approval: ApprovalGate = ApprovalGate(goal.risk_tolerance, goal.approval_ttl)
    prior_plan: PlanVersion | None = None
    prior_findings: list[Finding] = []

    for revision in range(1, config.revision_cap + 1):
        state.record_revision()
        logger.info(
            "loop: revision %d/%d — plan=%s v%d",
            revision,
            config.revision_cap,
            plan.id,
            plan.version,
        )

        gate_findings = run_deterministic_gates(plan)
        gate_blockers = [f for f in gate_findings if f.severity is Severity.BLOCKER]
        logger.info(
            "loop: gates — %d findings (%d blockers)",
            len(gate_findings),
            len(gate_blockers),
        )

        if config.mode == "deterministic-first" and _has_blocker(gate_findings):
            logger.info("loop: gate blocker → revise (no LLM critic spend)")
            if budget_exceeded(goal.constraints.budget, state):
                logger.info("loop: budget exceeded → escalate")
                return _escalate(goal, plan, gate_findings, "budget_exceeded", revision)
            if revision < config.revision_cap:
                plan = _revise_or_raise(
                    planner,
                    plan,
                    gate_findings,
                    next_id=f"plan-{goal.id}-r{revision + 1}",
                )
                continue
            logger.info("loop: revision cap reached → escalate")
            return _escalate(goal, plan, gate_findings, "revision_cap_reached", revision)

        if should_invoke_llm(config.mode, gate_findings):
            if (
                goal.constraints.budget.max_calls is not None
                and state.calls_used >= goal.constraints.budget.max_calls
            ):
                logger.info("loop: LLM call budget exceeded → escalate")
                return _escalate(goal, plan, gate_findings, "budget_exceeded", revision)
            logger.info("loop: invoking LLM critic (call %d)", state.calls_used + 1)
            state.record_llm_call()
            if config.mode == "deterministic-first":
                findings = list(gate_findings) + _safe_audit_diff(
                    critic, plan, gate_findings, prior_plan
                )
            else:
                findings = list(gate_findings) + _safe_audit(critic, plan, gate_findings)
            crit_blockers = [f for f in findings if f.severity is Severity.BLOCKER]
            logger.info(
                "loop: critic — %d total findings (%d blockers)",
                len(findings),
                len(crit_blockers),
            )
        else:
            findings = list(gate_findings)

        threshold_ok, thresholds = resolve_threshold(findings, goal.risk_tolerance)
        if threshold_ok:
            approved = approval.approve(plan, thresholds)
            logger.info("loop: threshold met → APPROVED plan=%s v%d", plan.id, plan.version)
            return LoopResult(
                status="approved",
                plan=plan,
                findings=findings,
                reason_code="approved",
                approved_plan=approved,
            )

        if budget_exceeded(goal.constraints.budget, state):
            logger.info("loop: budget exceeded → escalate")
            return _escalate(goal, plan, findings, "budget_exceeded", revision)

        if goal.replan_policy is ReplanPolicy.ABORT:
            logger.info("loop: replan_policy=abort → escalate (no revise)")
            return _escalate(goal, plan, findings, "replan_aborted", revision)

        if regression_detected(prior_findings, findings):
            logger.info("loop: regression detected → escalate (thrashing)")
            return _escalate(goal, plan, findings, "regression_thrashing", revision)

        if stalled(prior_plan, prior_findings, plan, findings):
            logger.info("loop: convergence detected → escalate (stalled)")
            return _escalate(goal, plan, findings, "converged_stalled", revision)

        prior_plan, prior_findings = plan, findings
        if revision < config.revision_cap:
            logger.info("loop: revising plan (revision %d → %d)", revision, revision + 1)
            next_id = f"plan-{goal.id}-r{revision + 1}"
            plan = _revise_or_raise(planner, plan, findings, next_id=next_id)

    logger.info("loop: revision cap reached → escalate")
    return _escalate(goal, plan, prior_findings or [], "revision_cap_reached", config.revision_cap)


def _has_blocker(findings: list[Finding]) -> bool:
    """True when any finding is a blocker (fail-closed threshold)."""
    return any(f.severity is Severity.BLOCKER for f in findings)


def _safe_audit(critic: CriticRole, plan: PlanVersion, findings: list[Finding]) -> list[Finding]:
    """Audit via critic, but never let a critic failure kill the loop.

    Args:
        critic: The critic role.
        plan: The plan being audited.
        findings: Gate findings flow through to the critic's view.

    Returns:
        The critic's findings. The deterministic gates have already
        collected gate findings separately, so a critic error maps to an
        empty list here rather than breaking the loop (the gates remain the
        free/immune layer). The error is logged so the failure is visible.
    """
    try:
        return critic.audit(plan, findings)
    except Exception as exc:
        logger.warning("critic role failed (full audit): %s — continuing with gates only", exc)
        return []


def _safe_audit_diff(
    critic: CriticRole,
    plan: PlanVersion,
    findings: list[Finding],
    prior_plan: PlanVersion | None,
) -> list[Finding]:
    """Diff-aware audit on revision N>1 when the critic supports it (F-78).

    Args:
        critic: The critic role.
        plan: The current plan revision.
        findings: Gate findings flowing through to the critic's view.
        prior_plan: The previous revision, or None on the root revision.

    Returns:
        The critic's findings. A full audit is used on the root revision or
        when the critic has no diff-aware entry point.
    """
    diff_method = getattr(critic, "audit_diff", None)
    if diff_method is None:
        return _safe_audit(critic, plan, findings)
    audit_diff = cast(
        "Callable[[PlanVersion, list[Finding], Sequence[str]], list[Finding]]",
        diff_method,
    )
    try:
        scope = scope_between(prior_plan, plan)
        return audit_diff(plan, findings, scope)
    except Exception as exc:
        logger.warning("critic role failed (diff audit): %s — continuing with gates only", exc)
        return []


def _revise_or_raise(
    planner: PlannerRole,
    plan: PlanVersion,
    findings: list[Finding],
    next_id: str,
) -> PlanVersion:
    """Revise the plan; raise fail-closed PlanningError on role failure.

    Args:
        planner: The planner role.
        plan: The current revision.
        findings: Findings the revision must address.
        next_id: Id to stamp on the new revision.

    Returns:
        The new revision as a typed PlanVersion.

    Raises:
        PlanningError: When the planner fails or emits something untyped.
    """
    try:
        revised = planner.revise(plan, findings)
    except Exception as exc:
        raise PlanningError(f"planner role failed to revise: {exc}") from exc
    if not isinstance(revised, PlanVersion):
        raise PlanningError(f"planner revised to non-PlanVersion: {type(revised).__name__}")
    return _plan_revision(revised, next_id, parent=plan)


__all__ = ["CriticMode", "LoopConfig", "LoopResult", "meets_threshold", "run_loop"]
