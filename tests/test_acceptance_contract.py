"""Frozen acceptance-criteria contract tests (#215).

The joinwell52 requirement: the criteria and approving authority are bound
before execution starts; changing them later creates a new contract version
rather than easing the run in flight. Approval becomes a deterministic
consumer of the bound contract.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from conftest import ScriptedCritic, ScriptedPlanner, make_goal, make_plan, make_task
from planner_critic.loop import LoopConfig, run_loop
from planner_critic.schema.acceptance import (
    AcceptanceContract,
    bind_acceptance,
    evaluate_contract,
    revise_contract,
)
from planner_critic.schema.goal import RiskTolerance
from planner_critic.types import Severity


class TestBindAndHash:
    def test_bind_is_frozen_with_stable_hash(self) -> None:
        goal = make_goal(tolerance=RiskTolerance.BALANCED)
        c1 = bind_acceptance(goal, approving_authority="team-lead")
        c2 = bind_acceptance(goal, approving_authority="team-lead")
        assert c1.content_hash == c2.content_hash
        with pytest.raises(ValidationError):  # frozen model
            c1.approving_authority = "someone-else"  # type: ignore[misc]

    def test_hash_changes_when_criteria_change(self) -> None:
        goal = make_goal(tolerance=RiskTolerance.BALANCED)
        a = bind_acceptance(goal, approving_authority="team-lead")
        b = bind_acceptance(goal, approving_authority="sre-oncall")
        assert a.content_hash != b.content_hash

    def test_revise_bumps_version_and_keeps_history(self) -> None:
        goal = make_goal(tolerance=RiskTolerance.BALANCED)
        c1 = bind_acceptance(goal, approving_authority="team-lead")
        c2 = revise_contract(c1, approving_authority="sre-oncall")
        assert c2.contract_version == 2
        assert c2.goal_id == c1.goal_id
        assert c2.content_hash != c1.content_hash
        assert c1.content_hash in c2.prior_hashes


class TestEvaluate:
    def test_balanced_contract_allows_llm_warnings(self) -> None:
        from planner_critic.types import Finding

        goal = make_goal(tolerance=RiskTolerance.BALANCED)
        contract = bind_acceptance(goal, approving_authority="engine")
        warning = Finding(
            id="w1", version=1, severity=Severity.WARNING,
            reason_code="llm_risk", message="x", heuristic_family=None,
        )
        ok, _ = evaluate_contract([warning], contract)
        assert ok is True

    def test_strict_contract_blocks_the_same_findings(self) -> None:
        from planner_critic.types import Finding

        goal = make_goal(tolerance=RiskTolerance.STRICT)
        contract = bind_acceptance(goal, approving_authority="engine")
        warning = Finding(
            id="w1", version=1, severity=Severity.WARNING,
            reason_code="llm_risk", message="x", heuristic_family=None,
        )
        ok, _ = evaluate_contract([warning], contract)
        assert ok is False


class TestLoopBinding:
    def test_run_loop_uses_bound_contract_not_ambient_posture(self) -> None:
        """A strict-bound contract governs even when the goal says balanced."""
        plans = [make_plan(tasks=[make_task("t1")])]
        result = run_loop(
            make_goal(tolerance=RiskTolerance.BALANCED),
            ScriptedPlanner(plans),
            ScriptedCritic([[]]),
            config=LoopConfig(),
            acceptance=bind_acceptance(
                make_goal(tolerance=RiskTolerance.STRICT), approving_authority="engine"
            ),
        )
        # Under the bound STRICT posture the clean plan still approves (no
        # findings); this asserts binding flows through without error and
        # approval is computed from the contract path.
        assert result.status == "approved"

    def test_bound_strict_contract_escalates_warning_findings(self) -> None:
        """Balanced goal + strict-bound contract → warnings block approval."""
        from planner_critic.types import Finding

        warning = Finding(
            id="w1",
            task_id="t1",
            version=1,
            severity=Severity.WARNING,
            reason_code="llm_risk",
            message="advisory noise",
        )
        plans = [make_plan(tasks=[make_task("t1")])]
        result = run_loop(
            make_goal(tolerance=RiskTolerance.BALANCED),
            ScriptedPlanner(plans),
            ScriptedCritic([[warning]]),
            config=LoopConfig(revision_cap=1),
            acceptance=bind_acceptance(
                make_goal(tolerance=RiskTolerance.STRICT), approving_authority="engine"
            ),
        )
        assert result.status == "escalated"


class TestAuthorityEnforcement:
    def _manager_with_open_escalation(self, authority: str | None) -> tuple:
        from planner_critic.escalation import EscalationManager
        from planner_critic.store import InMemoryStore
        from planner_critic.types import Escalation

        store = InMemoryStore()
        plan = make_plan(tasks=[make_task("t1")])
        store.put_plan_version(plan)
        manager = EscalationManager(store, approving_authority=authority)
        esc = manager.create(
            Escalation(id="e1", plan_id=plan.id, version=1, question="proceed?")
        )
        return manager, esc

    def test_wrong_principal_cannot_resolve(self) -> None:
        manager, esc = self._manager_with_open_escalation("team-lead")
        with pytest.raises(PermissionError):
            manager.resolve(esc.id, "approved", note="hi", principal="random-intern")

    def test_bound_principal_can_resolve(self) -> None:
        manager, esc = self._manager_with_open_escalation("team-lead")
        resolved = manager.resolve(esc.id, "approved", note="ok", principal="team-lead")
        assert resolved.status == "approved"

    def test_no_authority_configured_keeps_open_behavior(self) -> None:
        manager, esc = self._manager_with_open_escalation(None)
        resolved = manager.resolve(esc.id, "denied", principal="anyone")
        assert resolved.status == "denied"


class TestAcceptanceContractModel:
    def test_model_exists_with_required_fields(self) -> None:
        fields = set(AcceptanceContract.model_fields)
        assert {
            "goal_id",
            "criteria",
            "approving_authority",
            "contract_version",
            "content_hash",
            "prior_hashes",
            "bound_at",
        } <= fields
