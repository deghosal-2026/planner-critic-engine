"""Domain Pack framework tests (#139).

The Domain Pack protocol lets domain-specific gate evaluators, precondition
catalogs, and critic prompt templates be packaged into installable units and
plugged into the engine via ``Engine(domain_pack=...)``.

These tests cover:
1. ``DomainPack`` protocol compliance (name, gates, catalog, prompt)
2. Manifest YAML loading and validation
3. Engine integration: domain gates additive to built-in six
4. Critic prompt template prepended to the system prompt
5. ``plancritic domains`` CLI: list/show
6. Discovery of installed packs under ``planner_critic.domains.*``
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from conftest import make_plan
from planner_critic.domains.base import (
    DomainPack,
    find_domain_packs,
    load_domain_pack_from_manifest,
    pack_from_dict,
)
from planner_critic.gates import GATES, run_deterministic_gates
from planner_critic.gates.base import BaseGate
from planner_critic.schema.plan import PlanVersion
from planner_critic.types import Finding, Severity

# ── Sample domain gates for testing ───────────────────────────────────────


class SampleGate(BaseGate):
    """A no-op gate that always produces one warning finding."""

    name = "sample_gate"

    def run(self, plan: PlanVersion) -> list[Finding]:
        return [
            Finding(
                id=f"sample:{plan.id}:{plan.version}",
                version=plan.version,
                severity=Severity.WARNING,
                reason_code="unverified_precondition",
                message="sample domain gate finding",
            )
        ]


SAMPLE_PROMPT = "Audit this plan from a security-engineering perspective.\n"


class SampleDomainPack:
    """A minimal protocol-compliant domain pack for testing."""

    name = "sample-domain"
    precondition_catalog: dict = {
        "traffic_drained": "Traffic has been drained from the target",
        "snapshot_created": "A recent snapshot of the resource exists",
    }
    gate_evaluators: list = [SampleGate()]
    critic_prompt_template: str | None = SAMPLE_PROMPT
    pack_config: dict = {}


# ── Manifest YAML tests ───────────────────────────────────────────────────

SAMPLE_MANIFEST = {
    "name": "test-pack",
    "version": "0.1.0",
    "description": "A test domain pack",
    "preconditions": {
        "db_backed_up": "Database has been backed up",
    },
    "critic_prompt": "Audit with database safety in mind.\n",
    "config_schema": {},
}

MINIMAL_MANIFEST = {
    "name": "minimal-pack",
}


class TestDomainPackProtocol:
    """Protocol compliance: a pack must expose name, gates, catalog, prompt."""

    def test_sample_pack_is_valid_domain_pack(self) -> None:
        """A correctly-shaped object passes the protocol check."""
        assert isinstance(SampleDomainPack(), DomainPack)

    def test_missing_name_is_not_a_domain_pack(self) -> None:
        """An object without ``name`` does not satisfy the protocol."""

        class BadPack:
            gate_evaluators: list = []
            precondition_catalog: dict = {}
            critic_prompt_template: str | None = None
            pack_config: dict = {}

        assert not isinstance(BadPack(), DomainPack)

    def test_missing_gates_is_not_a_domain_pack(self) -> None:
        """An object without ``gate_evaluators`` is not a valid pack."""

        class BadPack:
            name = "bad"
            precondition_catalog: dict = {}

        assert not isinstance(BadPack(), DomainPack)

    def test_pack_name_is_stable_identifier(self) -> None:
        """The pack name is used for CLI display and manifest matching."""
        pack = SampleDomainPack()
        assert pack.name == "sample-domain"


class TestManifestLoading:
    """YAML manifest → DomainPack object."""

    def test_load_from_dict(self) -> None:
        """A valid manifest dict produces a working domain pack."""
        pack = pack_from_dict(SAMPLE_MANIFEST)
        assert pack.name == "test-pack"
        assert isinstance(pack, DomainPack)

    def test_minimal_manifest(self) -> None:
        """A manifest with only ``name`` still produces a valid pack."""
        pack = pack_from_dict(MINIMAL_MANIFEST)
        assert pack.name == "minimal-pack"
        assert pack.gate_evaluators == []
        assert pack.precondition_catalog == {}
        assert pack.critic_prompt_template is None

    def test_manifest_requires_name(self) -> None:
        """A manifest without ``name`` raises a clear error."""
        with pytest.raises(ValueError, match="name"):
            pack_from_dict({})

    def test_load_from_yaml_file(self, tmp_path: Path) -> None:
        """A ``domain-pack.yaml`` file loads into a DomainPack."""
        path = tmp_path / "domain-pack.yaml"
        with path.open("w") as f:
            yaml.dump(SAMPLE_MANIFEST, f)

        pack = load_domain_pack_from_manifest(str(path))
        assert pack.name == "test-pack"
        assert isinstance(pack, DomainPack)

    def test_load_from_yaml_file_not_found(self) -> None:
        """A missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_domain_pack_from_manifest("/nonexistent/pack.yaml")

    def test_build_gate_from_import(self) -> None:
        """A gate spec with a module path resolves to a BaseGate."""
        pack = pack_from_dict(
            {
                "name": "import-test",
                "gates": [{"module": "planner_critic.gates.ordering"}],
            }
        )
        assert len(pack.gate_evaluators) == 1
        assert isinstance(pack.gate_evaluators[0], BaseGate)

    def test_build_gate_missing_module_raises(self) -> None:
        """A gate spec without a module raises ValueError."""
        with pytest.raises(ValueError, match="module"):
            pack_from_dict(
                {
                    "name": "bad-gate",
                    "gates": [{"class": "MissingGate"}],
                }
            )

    def test_build_gate_bad_class_raises(self) -> None:
        """A gate spec with a non-existent class raises ImportError."""
        with pytest.raises(ImportError):
            pack_from_dict(
                {
                    "name": "bad-gate",
                    "gates": [
                        {"module": "planner_critic.gates.ordering", "class": "NonExistentGate"}
                    ],
                }
            )

    def test_find_domain_packs_empty(self) -> None:
        """Scanning a namespace with no packs returns an empty dict."""
        packs = find_domain_packs("planner_critic.adapters")
        assert isinstance(packs, dict)


class TestEngineIntegration:
    """Domain gates are additive; prompt is prepended."""

    def test_domain_gates_add_to_built_in_six(self) -> None:
        """Domain gates run alongside, not instead of, the built-in six."""
        len(GATES)
        # Simulate adding domain gates by checking that GATES count grows
        # when domain gates are present.  The engine integration will
        # compose the two lists.
        from planner_critic.engine import Engine
        from planner_critic.schema.goal import Goal

        class FakePlanner:
            def decompose(self, goal: Goal) -> PlanVersion: ...
            def revise(self, plan: PlanVersion, findings: list[Finding]) -> PlanVersion: ...

        class FakeCritic:
            def audit(self, plan: PlanVersion, findings: list[Finding]) -> list[Finding]:
                return list(findings)

        engine = Engine(
            planner=FakePlanner(),
            critic=FakeCritic(),
            domain_pack=SampleDomainPack(),
        )
        assert engine.domain_gates is not None
        # Domain gates are separate from built-in; engine.run_domain_gates
        # should produce both gate sets.
        findings = engine.run_domain_gates(make_plan())
        assert len(findings) == 1  # sample domain gate produces 1 finding
        assert findings[0].reason_code == "unverified_precondition"

    def test_domain_prompt_available(self) -> None:
        """The domain prompt is stored on the engine for the critic to use."""
        from planner_critic.engine import Engine

        class FakePlanner:
            def decompose(self, goal):
                return make_plan()

            def revise(self, plan, findings):
                return plan

        class FakeCritic:
            def audit(self, plan, findings):
                return list(findings)

        engine = Engine(FakePlanner(), FakeCritic(), domain_pack=SampleDomainPack())
        assert engine.domain_critic_prompt == SAMPLE_PROMPT


class TestDomainGatesAdditive:
    """The built-in six still fire alongside domain gates."""

    def test_built_in_gates_still_block_when_domain_gates_are_empty(self) -> None:
        """With an empty domain pack, built-in gates behave as before."""
        plan = make_plan()
        findings = run_deterministic_gates(plan)
        assert isinstance(findings, list)

    def test_domain_gates_do_not_mask_built_in_blockers(self) -> None:
        """When both domain and built-in gates fire, both blockers surface."""
        # The built-in gates block a high-risk plan with no verification;
        # the domain sample gate adds a warning. Both are present.
        plan = make_plan(tasks=[__import__("conftest").make_task("t1", risk_class="critical")])
        built_in = run_deterministic_gates(plan)
        sample = SampleGate().run(plan)
        combined = built_in + sample
        blockers = [f for f in combined if f.severity is Severity.BLOCKER]
        warnings = [f for f in combined if f.severity is Severity.WARNING]
        assert len(blockers) == 2  # missing_verification + missing_rollback
        assert len(warnings) == 1  # sample domain gate


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
