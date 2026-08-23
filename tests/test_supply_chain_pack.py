"""Supply-chain domain pack tests (#141).

Three deterministic gates + precondition catalog + domain critic prompt:
- Transitive locking: manifest edit without lockfile regeneration
- Breaking-change pre-checks: major semver bump without migration/linter
- Artifact integrity: deploy of unsigned/unattested artifact
"""

from __future__ import annotations

import pytest

from conftest import make_plan, make_task
from planner_critic.domains.base import DomainPack, pack_from_dict
from planner_critic.domains.supply_chain import SupplyChainDomainPack
from planner_critic.schema.plan import PlanVersion, Task
from planner_critic.types import Severity


def _task(tid: str, **kw: object) -> Task:
    return Task.model_validate(
        {"id": tid, "description": f"task {tid}", "action": "do", "target": tid, **kw}
    )


def _clean_plan() -> PlanVersion:
    return make_plan(tasks=[make_task("build"), make_task("deploy")])


class TestPackShape:
    """Protocol compliance and metadata."""

    def test_is_valid_domain_pack(self) -> None:
        pack = SupplyChainDomainPack()
        assert isinstance(pack, DomainPack)
        assert pack.name == "supply_chain"

    def test_three_gates(self) -> None:
        assert len(SupplyChainDomainPack().gate_evaluators) == 3

    def test_precondition_catalog(self) -> None:
        cat = SupplyChainDomainPack().precondition_catalog
        for key in (
            "lockfile_regenerated",
            "migration_script_passed",
            "artifact_signed",
            "sbom_generated",
            "linter_clean",
        ):
            assert key in cat

    def test_critic_prompt_present(self) -> None:
        prompt = SupplyChainDomainPack().critic_prompt_template
        assert prompt is not None
        assert "supply" in prompt.lower() or "dependency" in prompt.lower()


class TestTransitiveLockingGate:
    """Manifest edit without lockfile regeneration → blocker."""

    GATE = SupplyChainDomainPack().gate_evaluators[0]

    def test_clean_passes(self) -> None:
        assert self.GATE.run(_clean_plan()) == []

    def test_manifest_edit_with_lockfile_regeneration_passes(self) -> None:
        plan = make_plan(
            tasks=[
                _task("edit", action="edit_manifest", target="package.json"),
                _task("regen", action="regenerate_lockfile", target="package-lock.json"),
            ]
        )
        assert self.GATE.run(plan) == []

    def test_manifest_edit_without_lockfile_blocked(self) -> None:
        findings = self.GATE.run(
            make_plan(
                tasks=[
                    _task("edit", action="edit_manifest", target="package.json"),
                ]
            )
        )
        assert len(findings) == 1
        assert findings[0].severity is Severity.BLOCKER


class TestBreakingChangeGate:
    """Major semver bump without migration/linter → blocker."""

    GATE = SupplyChainDomainPack().gate_evaluators[1]

    def test_clean_passes(self) -> None:
        assert self.GATE.run(_clean_plan()) == []

    def test_major_bump_with_migration_passes(self) -> None:
        plan = make_plan(
            tasks=[
                _task("bump", action="bump_major", target="2.0.0"),
                _task("migrate", action="run_migration", target="migration.py"),
                _task("lint", action="run_linter", target="all"),
            ]
        )
        assert self.GATE.run(plan) == []

    def test_major_bump_without_checks_blocked(self) -> None:
        findings = self.GATE.run(
            make_plan(
                tasks=[
                    _task("bump", action="bump_major", target="2.0.0"),
                ]
            )
        )
        assert len(findings) >= 1

    def test_minor_bump_passes(self) -> None:
        findings = self.GATE.run(
            make_plan(
                tasks=[
                    _task("bump", action="bump_minor", target="1.5.0"),
                ]
            )
        )
        assert findings == []


class TestArtifactIntegrityGate:
    """Deploy of unsigned/unattested artifact → blocker."""

    GATE = SupplyChainDomainPack().gate_evaluators[2]

    def test_clean_passes(self) -> None:
        assert self.GATE.run(_clean_plan()) == []

    def test_signed_artifact_passes(self) -> None:
        plan = make_plan(
            tasks=[
                _task("sign", action="sign_artifact", target="app.tar.gz"),
                _task("deploy", action="deploy", target="app.tar.gz"),
            ]
        )
        findings = self.GATE.run(plan)
        # SBOM check still fires without generate_sbom
        assert not any(f.reason_code == "supply_chain_unsigned_artifact" for f in findings)

    def test_unsigned_deploy_blocked(self) -> None:
        findings = self.GATE.run(
            make_plan(
                tasks=[
                    _task("deploy", action="deploy", target="app.tar.gz"),
                ]
            )
        )
        assert any(f.reason_code == "supply_chain_unsigned_artifact" for f in findings)

    def test_sbom_generated_clears_sbom_check(self) -> None:
        plan = make_plan(
            tasks=[
                _task("sbom", action="generate_sbom", target="app"),
                _task("deploy", action="deploy", target="app.tar.gz"),
            ]
        )
        findings = self.GATE.run(plan)
        assert not any(f.reason_code == "supply_chain_missing_sbom" for f in findings)

    def test_fully_integrity_clean_passes(self) -> None:
        plan = make_plan(
            tasks=[
                _task("sign", action="sign_artifact", target="app.tar.gz"),
                _task("sbom", action="generate_sbom", target="app"),
                _task("deploy", action="deploy", target="app.tar.gz"),
            ]
        )
        assert self.GATE.run(plan) == []


class TestManifestLoading:
    """Packs load from manifest YAML."""

    MANIFEST = {
        "name": "supply_chain",
        "gates": [
            {
                "module": "planner_critic.domains.supply_chain.gates",
                "class": "TransitiveLockingGate",
            },
            {"module": "planner_critic.domains.supply_chain.gates", "class": "BreakingChangeGate"},
            {
                "module": "planner_critic.domains.supply_chain.gates",
                "class": "ArtifactIntegrityGate",
            },
        ],
        "preconditions": {"lockfile_regenerated": "Lockfile regenerated"},
        "critic_prompt": "Audit this plan from a supply-chain perspective.\n",
    }

    def test_load_from_manifest(self) -> None:
        pack = pack_from_dict(self.MANIFEST)
        assert isinstance(pack, DomainPack)
        assert pack.name == "supply_chain"
        assert len(pack.gate_evaluators) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
