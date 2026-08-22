"""Data engineering domain pack tests (#143).

Three deterministic gates + precondition catalog + domain critic prompt:
- Schema pre-verification: destructive query without verified backup
- SLA-window constraints: migration outside maintenance window
- Dual-write rollback plans: live migration without dual-write/fallback
"""

from __future__ import annotations

import pytest

from conftest import make_plan, make_task
from planner_critic.domains.base import DomainPack, pack_from_dict
from planner_critic.domains.data_eng import DataEngineeringDomainPack
from planner_critic.schema.plan import PlanVersion, Task
from planner_critic.types import Severity


def _task(tid: str, **kw: object) -> Task:
    return Task.model_validate({"id": tid, "description": f"task {tid}",
                                "action": "do", "target": tid, **kw})


def _clean_plan() -> PlanVersion:
    return make_plan(tasks=[make_task("inspect"), make_task("report")])


class TestPackShape:
    """Protocol compliance and metadata."""

    def test_is_valid_domain_pack(self) -> None:
        pack = DataEngineeringDomainPack()
        assert isinstance(pack, DomainPack)
        assert pack.name == "data_eng"

    def test_three_gates(self) -> None:
        assert len(DataEngineeringDomainPack().gate_evaluators) == 3

    def test_precondition_catalog(self) -> None:
        cat = DataEngineeringDomainPack().precondition_catalog
        for key in ("backup_created", "backup_verified_restorable",
                    "maintenance_window_active", "dual_write_enabled",
                    "fallback_path_defined", "schema_compatibility_checked"):
            assert key in cat

    def test_critic_prompt_present(self) -> None:
        prompt = DataEngineeringDomainPack().critic_prompt_template
        assert prompt is not None
        assert "migration" in prompt.lower() or "schema" in prompt.lower()


class TestSchemaPreVerificationGate:
    """Destructive query without verified backup → blocker."""

    GATE = DataEngineeringDomainPack().gate_evaluators[0]

    def test_clean_passes(self) -> None:
        assert self.GATE.run(_clean_plan()) == []

    def test_destructive_with_verified_backup_passes(self) -> None:
        plan = make_plan(tasks=[
            _task("backup", action="create_backup", target="db"),
            _task("verify", action="verify_restorable", target="backup"),
            _task("drop", action="drop_table", target="users"),
        ])
        assert self.GATE.run(plan) == []

    def test_destructive_without_backup_blocked(self) -> None:
        findings = self.GATE.run(make_plan(tasks=[
            _task("drop", action="drop_table", target="users"),
        ]))
        assert any(f.severity is Severity.BLOCKER for f in findings)

    def test_destructive_with_unverified_backup_blocked(self) -> None:
        findings = self.GATE.run(make_plan(tasks=[
            _task("backup", action="create_backup", target="db"),
            _task("drop", action="drop_table", target="users"),
        ]))
        assert any(f.reason_code == "data_eng_destructive_without_backup"
                   for f in findings)


class TestSLAWindowGate:
    """Migration outside maintenance window → blocker."""

    GATE = DataEngineeringDomainPack().gate_evaluators[1]

    def test_clean_passes(self) -> None:
        assert self.GATE.run(_clean_plan()) == []

    def test_migration_in_window_passes(self) -> None:
        plan = make_plan(tasks=[
            _task("window", action="maintenance_window", target="active"),
            _task("migrate", action="migrate", target="schema"),
        ])
        assert self.GATE.run(plan) == []

    def test_migration_outside_window_blocked(self) -> None:
        findings = self.GATE.run(make_plan(tasks=[
            _task("migrate", action="migrate", target="schema"),
        ]))
        assert any(f.reason_code == "data_eng_migration_outside_maintenance_window"
                   for f in findings)


class TestDualWriteGate:
    """Live migration without dual-write/fallback → blocker."""

    GATE = DataEngineeringDomainPack().gate_evaluators[2]

    def test_clean_passes(self) -> None:
        assert self.GATE.run(_clean_plan()) == []

    def test_migration_with_dual_write_and_fallback_passes(self) -> None:
        plan = make_plan(tasks=[
            _task("dual", action="enable_dual_write", target="db"),
            _task("fallback", action="define_fallback", target="rollback"),
            _task("migrate", action="live_migrate", target="schema"),
        ])
        assert self.GATE.run(plan) == []

    def test_live_migration_without_dual_write_blocked(self) -> None:
        findings = self.GATE.run(make_plan(tasks=[
            _task("migrate", action="live_migrate", target="schema"),
        ]))
        assert any(f.reason_code == "data_eng_migration_without_dual_write"
                   for f in findings)

    def test_live_migration_without_fallback_blocked(self) -> None:
        findings = self.GATE.run(make_plan(tasks=[
            _task("dual", action="enable_dual_write", target="db"),
            _task("migrate", action="live_migrate", target="schema"),
        ]))
        assert any(f.reason_code == "data_eng_migration_without_fallback"
                   for f in findings)


class TestManifestLoading:
    """Packs load from manifest YAML."""

    MANIFEST = {
        "name": "data_eng",
        "gates": [
            {"module": "planner_critic.domains.data_eng.gates",
             "class": "SchemaPreVerificationGate"},
            {"module": "planner_critic.domains.data_eng.gates",
             "class": "SLAWindowGate"},
            {"module": "planner_critic.domains.data_eng.gates",
             "class": "DualWriteGate"},
        ],
        "preconditions": {"backup_created": "Backup exists"},
        "critic_prompt": "Audit from a data-engineering perspective.\n",
    }

    def test_load_from_manifest(self) -> None:
        pack = pack_from_dict(self.MANIFEST)
        assert isinstance(pack, DomainPack)
        assert pack.name == "data_eng"
        assert len(pack.gate_evaluators) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
