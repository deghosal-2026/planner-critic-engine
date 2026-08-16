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
store-less (persistence lands with M2). Escalation surfaces a precise
question so the escalation manager (M4) can present it to a human.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from ..approval import ApprovalGate, meets_threshold, resolve_threshold
from ..gates import run_deterministic_gates
from ..reason_codes import ReasonCode
from ..roles import CriticRole, PlannerRole
from ..schema.goal import Goal
from ..schema.plan import PlanVersion
from ..types import ApprovedPlan, Escalation, Finding, PlanningError, Severity
from .budget import SpendState, budget_exceeded
from .convergence import stalled
from .regression import regression_detected

CriticMode = Literal["deterministic-first", "llm-every-revision"]


@dataclass(frozen=True)
class LoopConfig:
    """Deterministic tuning of the revise-until-approved loop."""

    mode: CriticMode = "deterministic-first"
    revision_cap: int = 3


@dataclass
class LoopResult:
    """The consolidated outcome of one ``run_loop`` invocation."""

    status: Literal["approved", "escalated"]
    plan: PlanVersion | None = None
    findings: list[Finding] = field(default_factory=list)
    reason_code: ReasonCode | None = None
    approved_plan: ApprovedPlan | None = None
    escalation: Escalation | None = None

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
    try:
        plan = planner.decompose(goal)
    except Exception as exc:
        raise PlanningError(f"planner role failed to decompose: {exc}") from exc
    if not isinstance(plan, PlanVersion):
        raise PlanningError(f"planner returned non-PlanVersion: {type(plan).__name__}")

    approval: ApprovalGate = ApprovalGate(goal.risk_tolerance, goal.approval_ttl)
    prior_plan: PlanVersion | None = None
    prior_findings: list[Finding] = []

    for revision in range(1, config.revision_cap + 1):
        state.record_revision()

        gate_findings = run_deterministic_gates(plan)

        if config.mode == "deterministic-first" and _has_blocker(gate_findings):
            if budget_exceeded(goal.constraints.budget, state):
                return _escalate(goal, plan, gate_findings, "budget_exceeded", revision)
            if revision < config.revision_cap:
                plan = _revise_or_raise(
                    planner, plan, gate_findings,
                    next_id=f"plan-{goal.id}-r{revision + 1}",
                )
                continue
            return _escalate(goal, plan, gate_findings, "revision_cap_reached", revision)

        findings = list(gate_findings) + _safe_audit(critic, plan, gate_findings)

        threshold_ok, thresholds = resolve_threshold(findings, goal.risk_tolerance)
        if threshold_ok:
            approved = approval.approve(plan, thresholds)
            return LoopResult(
                status="approved",
                plan=plan,
                findings=findings,
                reason_code="approved",
                approved_plan=approved,
            )

        if budget_exceeded(goal.constraints.budget, state):
            return _escalate(goal, plan, findings, "budget_exceeded", revision)

        if regression_detected(prior_findings, findings):
            return _escalate(goal, plan, findings, "regression_thrashing", revision)

        if stalled(prior_plan, prior_findings, plan, findings):
            return _escalate(goal, plan, findings, "converged_stalled", revision)

        prior_plan, prior_findings = plan, findings
        if revision < config.revision_cap:
            next_id = f"plan-{goal.id}-r{revision + 1}"
            plan = _revise_or_raise(planner, plan, findings, next_id=next_id)

    return _escalate(goal, plan, prior_findings or [], "revision_cap_reached", config.revision_cap)


def _has_blocker(findings: list[Finding]) -> bool:
    """True when any finding is a blocker (fail-closed threshold)."""
    return any(f.severity is Severity.BLOCKER for f in findings)


def _safe_audit(critic: CriticRole, plan: PlanVersion, findings: list[Finding]) -> list[Finding]:
    """Audit via critic, but never let a single bad finding kill the loop.

    Args:
        critic: The critic role.
        plan: The plan being audited.
        findings: Gate findings flow through to the critic's view.

    Returns:
        The critic's findings. The deterministic gates have already
        collected gate findings separately, so a critic error maps to an
        empty list here rather than breaking the loop (the gates remain the
        free/immune layer; real critic integration is M3).
    """
    try:
        return critic.audit(plan, findings)
    except Exception as exc:
        raise PlanningError(f"critic role failed: {exc}") from exc


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
