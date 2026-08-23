"""FinOps domain pack tests (#142).

Two deterministic gates + precondition catalog + domain critic prompt:
- Grace-period enforcement: instant delete without snapshot+notify+wait
- Budget-boundary gates: expansion breaches localized cap without override
"""

from __future__ import annotations

import pytest

from conftest import make_plan, make_task
from planner_critic.domains.base import DomainPack, pack_from_dict
from planner_critic.domains.finops import FinOpsDomainPack
from planner_critic.schema.plan import PlanVersion, Task
from planner_critic.types import Severity


def _task(tid: str, **kw: object) -> Task:
    return Task.model_validate(
        {"id": tid, "description": f"task {tid}", "action": "do", "target": tid, **kw}
    )


def _clean_plan() -> PlanVersion:
    return make_plan(tasks=[make_task("check"), make_task("resize")])


class TestPackShape:
    """Protocol compliance and metadata."""

    def test_is_valid_domain_pack(self) -> None:
        pack = FinOpsDomainPack()
        assert isinstance(pack, DomainPack)
        assert pack.name == "finops"

    def test_two_gates(self) -> None:
        assert len(FinOpsDomainPack().gate_evaluators) == 2

    def test_precondition_catalog(self) -> None:
        cat = FinOpsDomainPack().precondition_catalog
        for key in (
            "snapshot_created",
            "owner_notified",
            "grace_period_elapsed",
            "budget_within_cap",
            "spend_forecast_checked",
        ):
            assert key in cat

    def test_critic_prompt_present(self) -> None:
        prompt = FinOpsDomainPack().critic_prompt_template
        assert prompt is not None
        assert "cost" in prompt.lower() or "budget" in prompt.lower()

    def test_constructor_config(self) -> None:
        """The pack accepts a budget_cap constructor arg."""
        pack = FinOpsDomainPack(budget_cap=1000)
        assert isinstance(pack, FinOpsDomainPack)
        assert pack.pack_config.get("budget_cap") == 1000


class TestGracePeriodGate:
    """Instant delete without snapshot+notify+wait → blocker."""

    GATE = FinOpsDomainPack().gate_evaluators[0]

    def test_clean_passes(self) -> None:
        assert self.GATE.run(_clean_plan()) == []

    def test_delete_with_full_grace_period_passes(self) -> None:
        plan = make_plan(
            tasks=[
                _task("snap", action="snapshot", target="db"),
                _task("notify", action="notify_owner", target="db"),
                _task("wait", action="wait_grace_period", target="7d"),
                _task("delete", action="delete", target="db"),
            ]
        )
        assert self.GATE.run(plan) == []

    def test_instant_delete_blocked(self) -> None:
        findings = self.GATE.run(
            make_plan(
                tasks=[
                    _task("delete", action="delete", target="db"),
                ]
            )
        )
        assert any(f.severity is Severity.BLOCKER for f in findings)

    def test_delete_with_snapshot_but_no_wait_blocked(self) -> None:
        findings = self.GATE.run(
            make_plan(
                tasks=[
                    _task("snap", action="snapshot", target="db"),
                    _task("notify", action="notify_owner", target="db"),
                    _task("delete", action="delete", target="db"),
                ]
            )
        )
        assert any(f.reason_code == "finops_delete_without_grace_period" for f in findings)


class TestBudgetBoundaryGate:
    """Expansion breaches localized cap without override → blocker."""

    def test_clean_passes(self) -> None:
        assert FinOpsDomainPack().gate_evaluators[1].run(_clean_plan()) == []

    def test_scale_within_cap_passes(self) -> None:
        plan = make_plan(
            tasks=[
                _task("check", action="check_budget", target="1000"),
                _task("scale", action="scale_up", target="500"),
            ]
        )
        assert FinOpsDomainPack(budget_cap=2000).gate_evaluators[1].run(plan) == []

    def test_scale_beyond_cap_blocked(self) -> None:
        plan = make_plan(
            tasks=[
                _task("check", action="check_budget", target="1000"),
                _task("scale", action="scale_up", target="1500"),
            ]
        )
        findings = FinOpsDomainPack(budget_cap=1000).gate_evaluators[1].run(plan)
        assert any(f.reason_code == "finops_budget_boundary_breached" for f in findings)

    def test_scale_beyond_cap_with_override_passes(self) -> None:
        plan = make_plan(
            tasks=[
                _task("check", action="check_budget", target="1000"),
                _task("override", action="executive_override", target="budget"),
                _task("scale", action="scale_up", target="1500"),
            ]
        )
        assert FinOpsDomainPack(budget_cap=1000).gate_evaluators[1].run(plan) == []

    def test_default_cap_used_when_no_arg(self) -> None:
        """Without a budget_cap arg, the pack uses its default cap (100k)."""
        pack = FinOpsDomainPack()
        plan = make_plan(
            tasks=[
                _task("check", action="check_budget", target="100000"),
                _task("scale", action="scale_up", target="50000"),
            ]
        )
        assert pack.gate_evaluators[1].run(plan) == []


class TestManifestLoading:
    """Packs load from manifest YAML."""

    MANIFEST = {
        "name": "finops",
        "gates": [
            {"module": "planner_critic.domains.finops.gates", "class": "GracePeriodGate"},
            {"module": "planner_critic.domains.finops.gates", "class": "BudgetBoundaryGate"},
        ],
        "preconditions": {"snapshot_created": "Snapshot exists"},
        "critic_prompt": "Audit from a cost perspective.\n",
    }

    def test_load_from_manifest(self) -> None:
        pack = pack_from_dict(self.MANIFEST)
        assert isinstance(pack, DomainPack)
        assert pack.name == "finops"
        assert len(pack.gate_evaluators) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
