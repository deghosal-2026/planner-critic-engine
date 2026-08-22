from __future__ import annotations

import pytest

from planner_critic.quota import BlastRadiusQuotaConfig, BlastRadiusQuotaGate
from planner_critic.schema.goal import RiskTolerance
from planner_critic.schema.plan import PlanVersion, RiskClass, Task
from planner_critic.types import Severity


def _task(tid: str, action: str = "do", target: str = "server") -> Task:
    return Task(
        id=tid,
        description=f"task {tid}",
        action=action,
        target=target,
        risk_class=RiskClass.LOW,
    )


def _plan(tasks: list[Task]) -> PlanVersion:
    return PlanVersion(
        id="plan-1",
        goal_id="goal-1",
        version=1,
        tasks=tasks,
        dependencies=[],
    )


class TestBlastRadiusQuotaGate:
    def test_no_quotas_no_findings(self) -> None:
        config = BlastRadiusQuotaConfig()
        gate = BlastRadiusQuotaGate(config)
        plan = _plan([_task("t1"), _task("t2")])
        findings = gate.run(plan)
        assert len(findings) == 0

    def test_resource_changes_breach(self) -> None:
        config = BlastRadiusQuotaConfig(max_resource_changes=1)
        gate = BlastRadiusQuotaGate(config)
        plan = _plan([_task("t1"), _task("t2")])
        findings = gate.run(plan)
        blockers = [f for f in findings if f.severity is Severity.BLOCKER]
        assert len(blockers) == 1
        assert blockers[0].reason_code == "blast_radius_quota_breach"
        assert "max_resource_changes" in (blockers[0].message or "")

    def test_resource_changes_within_limit(self) -> None:
        config = BlastRadiusQuotaConfig(max_resource_changes=5)
        gate = BlastRadiusQuotaGate(config)
        plan = _plan([_task("t1"), _task("t2")])
        findings = gate.run(plan)
        blockers = [f for f in findings if f.severity is Severity.BLOCKER]
        assert len(blockers) == 0

    def test_destructive_actions_breach(self) -> None:
        config = BlastRadiusQuotaConfig(max_destructive_actions=1)
        gate = BlastRadiusQuotaGate(config)
        plan = _plan([_task("t1", action="delete"), _task("t2", action="destroy")])
        findings = gate.run(plan)
        blockers = [f for f in findings if f.severity is Severity.BLOCKER]
        assert len(blockers) == 1
        assert blockers[0].reason_code == "blast_radius_quota_breach"

    def test_restricted_cluster(self) -> None:
        config = BlastRadiusQuotaConfig(restricted_clusters=["payment-us-east-1"])
        gate = BlastRadiusQuotaGate(config, posture=RiskTolerance.STRICT)
        plan = _plan([_task("t1", target="payment-us-east-1")])
        findings = gate.run(plan)
        blockers = [f for f in findings if f.severity is Severity.BLOCKER]
        assert len(blockers) == 1
        assert blockers[0].reason_code == "blast_radius_restricted_cluster"

    def test_restricted_action(self) -> None:
        config = BlastRadiusQuotaConfig(restricted_actions=["db.schema.drop"])
        gate = BlastRadiusQuotaGate(config, posture=RiskTolerance.STRICT)
        plan = _plan([_task("t1", action="db.schema.drop")])
        findings = gate.run(plan)
        blockers = [f for f in findings if f.severity is Severity.BLOCKER]
        assert len(blockers) == 1
        assert blockers[0].reason_code == "blast_radius_restricted_action"

    def test_restricted_permits_warning(self) -> None:
        config = BlastRadiusQuotaConfig(restricted_clusters=["prod"])
        gate = BlastRadiusQuotaGate(config, posture=RiskTolerance.PERMISSIVE)
        plan = _plan([_task("t1", target="prod-db")])
        findings = gate.run(plan)
        assert len(findings) == 1
        assert findings[0].severity is Severity.WARNING

    def test_db_alterations_breach(self) -> None:
        config = BlastRadiusQuotaConfig(max_database_alterations=1)
        gate = BlastRadiusQuotaGate(config)
        plan = _plan([_task("t1", target="db-schema"), _task("t2", target="database-users")])
        findings = gate.run(plan)
        blockers = [f for f in findings if f.severity is Severity.BLOCKER]
        assert len(blockers) == 1
        assert blockers[0].reason_code == "blast_radius_quota_breach"

    def test_multiple_breaches(self) -> None:
        config = BlastRadiusQuotaConfig(
            max_resource_changes=1,
            restricted_actions=["delete"],
        )
        gate = BlastRadiusQuotaGate(config, posture=RiskTolerance.STRICT)
        plan = _plan([_task("t1", action="delete"), _task("t2", action="delete")])
        findings = gate.run(plan)
        assert len(findings) == 3

    def test_config_from_dict(self) -> None:
        data = {
            "max_resource_changes": 5,
            "restricted_clusters": ["prod"],
        }
        config = BlastRadiusQuotaConfig.from_dict(data)
        assert config.max_resource_changes == 5
        assert config.restricted_clusters == ["prod"]
        assert config.max_destructive_actions is None