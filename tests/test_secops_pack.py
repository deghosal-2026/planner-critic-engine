"""SecOps domain pack tests (#140).

Three deterministic gates + precondition catalog + domain critic prompt:
- Blast-radius check: isolation without prior traffic drain
- Forensic order of operations: terminate/stop before snapshot
- Least-privilege verification: broad privilege without HITL
"""

from __future__ import annotations

import pytest

from conftest import hard_dep, make_plan, make_task
from planner_critic.domains.base import DomainPack, pack_from_dict
from planner_critic.domains.secops import SecOpsDomainPack
from planner_critic.schema.plan import PlanVersion, Task
from planner_critic.types import Severity


def _task(tid: str, **kw: object) -> Task:
    return Task.model_validate(
        {"id": tid, "description": f"task {tid}", "action": "do", "target": tid, **kw}
    )


def _clean_plan() -> PlanVersion:
    return make_plan(tasks=[make_task("isolate"), make_task("snapshot")])


class TestSecOpsPackIsDomainPack:
    """Protocol compliance."""

    def test_pack_is_valid_domain_pack(self) -> None:
        pack = SecOpsDomainPack()
        assert isinstance(pack, DomainPack)
        assert pack.name == "secops"

    def test_three_gates(self) -> None:
        pack = SecOpsDomainPack()
        assert len(pack.gate_evaluators) == 3

    def test_precondition_catalog(self) -> None:
        pack = SecOpsDomainPack()
        assert "traffic_drained" in pack.precondition_catalog
        assert "snapshot_created" in pack.precondition_catalog

    def test_critic_prompt_present(self) -> None:
        pack = SecOpsDomainPack()
        assert pack.critic_prompt_template is not None
        assert "security" in pack.critic_prompt_template.lower()


class TestBlastRadiusGate:
    """Isolation without prior traffic drain → blocker."""

    GATE = SecOpsDomainPack().gate_evaluators[0]

    def test_clean_plan_passes(self) -> None:
        assert self.GATE.run(_clean_plan()) == []

    def test_isolation_with_drain_passes(self) -> None:
        plan = make_plan(
            tasks=[_task("drain", action="drain"), _task("isolate", action="isolate")],
            dependencies=[hard_dep("drain", "isolate")],
        )
        assert self.GATE.run(plan) == []

    def test_isolation_without_drain_blocked(self) -> None:
        findings = self.GATE.run(make_plan(tasks=[_task("isolate", action="isolate")]))
        assert len(findings) == 1
        assert findings[0].severity is Severity.BLOCKER


class TestForensicOrderGate:
    """Terminate/stop before snapshot → blocker."""

    GATE = SecOpsDomainPack().gate_evaluators[1]

    def test_clean_plan_passes(self) -> None:
        assert self.GATE.run(_clean_plan()) == []

    def test_terminate_before_snapshot_blocked(self) -> None:
        findings = self.GATE.run(
            make_plan(
                tasks=[_task("term", action="terminate"), _task("snap", action="snapshot")],
            )
        )
        assert len(findings) == 1
        assert findings[0].severity is Severity.BLOCKER

    def test_snapshot_then_terminate_passes(self) -> None:
        assert (
            self.GATE.run(
                make_plan(
                    tasks=[_task("snap", action="snapshot"), _task("term", action="terminate")],
                )
            )
            == []
        )


class TestLeastPrivilegeGate:
    """Broad privilege without HITL → blocker."""

    GATE = SecOpsDomainPack().gate_evaluators[2]

    def test_clean_plan_passes(self) -> None:
        assert self.GATE.run(_clean_plan()) == []

    def test_broad_privilege_without_hitl_blocked(self) -> None:
        findings = self.GATE.run(
            make_plan(
                tasks=[_task("assume", action="sts:AssumeRole", target="*")],
            )
        )
        assert len(findings) >= 1

    def test_broad_privilege_with_hitl_passes(self) -> None:
        assert (
            self.GATE.run(
                make_plan(
                    tasks=[
                        _task("approval", action="human_approval"),
                        _task("assume", action="sts:AssumeRole", target="*"),
                    ],
                    dependencies=[hard_dep("approval", "assume")],
                )
            )
            == []
        )


class TestManifestLoading:
    """Packs can be loaded from manifest YAML too."""

    SECOPS_MANIFEST = {
        "name": "secops",
        "gates": [
            {"module": "planner_critic.domains.secops.gates", "class": "BlastRadiusGate"},
            {"module": "planner_critic.domains.secops.gates", "class": "ForensicOrderGate"},
            {"module": "planner_critic.domains.secops.gates", "class": "LeastPrivilegeGate"},
        ],
        "preconditions": {
            "traffic_drained": "Traffic has been drained",
            "snapshot_created": "A recent snapshot exists",
        },
        "critic_prompt": "Audit this plan from a security perspective.\n",
    }

    def test_load_from_manifest(self) -> None:
        pack = pack_from_dict(self.SECOPS_MANIFEST)
        assert isinstance(pack, DomainPack)
        assert pack.name == "secops"
        assert len(pack.gate_evaluators) == 3

    def test_manifest_gates_fire(self) -> None:
        pack = pack_from_dict(self.SECOPS_MANIFEST)
        findings = pack.gate_evaluators[2].run(
            make_plan(
                tasks=[_task("assume", action="sts:AssumeRole", target="*")],
            )
        )
        assert len(findings) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
