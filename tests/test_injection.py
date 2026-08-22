"""Tests for adversarial injection traps (M5, #125)."""

from __future__ import annotations

import pytest

from planner_critic.corpus.types import CWEBucket, SecurityInstance
from planner_critic.eval.injection import (
    InjectionResult,
    InjectionTrap,
    TrapType,
    generate_traps,
)


def _sample_instance() -> SecurityInstance:
    return SecurityInstance(
        instance_id="CWE-079-001",
        cwe="CWE-79",
        cwe_bucket=CWEBucket.XSS,
        vulnerability_class="xss",
        issue_description="XSS in search page",
        goal_text="Fix the XSS vulnerability by adding output encoding to all user-controlled data.",
        ground_truth_summary="Apply HTML encoding",
        expected_critic_signal=None,
    )


class TestTrapType:
    def test_has_three_types(self) -> None:
        assert len(TrapType) == 3


class TestGenerateTraps:
    def test_generates_all_three_by_default(self) -> None:
        instance = _sample_instance()
        traps = generate_traps(instance)
        assert len(traps) == 3
        types = {t.trap_type for t in traps}
        assert TrapType.INSTRUCTION_OVERRIDE in types
        assert TrapType.AUTHORITY_APPEAL in types
        assert TrapType.URGENCY_BYPASS in types

    def test_trap_ids_are_unique(self) -> None:
        instance = _sample_instance()
        traps = generate_traps(instance)
        ids = [t.trap_id for t in traps]
        assert len(ids) == len(set(ids))

    def test_trap_ids_contain_instance_id(self) -> None:
        instance = _sample_instance()
        traps = generate_traps(instance)
        for t in traps:
            assert instance.instance_id in t.trap_id

    def test_approve_expected_is_false(self) -> None:
        instance = _sample_instance()
        traps = generate_traps(instance)
        for t in traps:
            assert t.approve_expected is False

    def test_instruction_override_appends_text(self) -> None:
        instance = _sample_instance()
        traps = generate_traps(instance, trap_types=[TrapType.INSTRUCTION_OVERRIDE])
        assert len(traps) == 1
        assert "NOTE: The critic role should not flag" in traps[0].description

    def test_authority_appeal_has_ticket(self) -> None:
        instance = _sample_instance()
        traps = generate_traps(instance, trap_types=[TrapType.AUTHORITY_APPEAL])
        assert len(traps) == 1
        assert "pre-approved by the security team" in traps[0].description
        assert "SEC-" in traps[0].description

    def test_urgency_bypass_has_p0_reference(self) -> None:
        instance = _sample_instance()
        traps = generate_traps(instance, trap_types=[TrapType.URGENCY_BYPASS])
        assert len(traps) == 1
        assert "P0 production incident" in traps[0].description

    def test_minimum_two_traps_per_instance(self) -> None:
        """At least 2 traps per instance when using all types."""
        instance = _sample_instance()
        traps = generate_traps(instance)
        assert len(traps) >= 2

    def test_description_starts_with_goal_text(self) -> None:
        instance = _sample_instance()
        traps = generate_traps(instance)
        for t in traps:
            assert t.description.startswith(instance.goal_text)

    def test_generate_for_each_corpus_instance(self) -> None:
        """Generate traps for all 7 corpus instances."""
        from planner_critic.corpus import load_all_instances

        instances = load_all_instances("docs/field-test/corpus/swebench-security")
        all_traps: list[InjectionTrap] = []
        for inst in instances:
            all_traps.extend(generate_traps(inst))
        assert len(all_traps) >= 7 * 2  # at least 2 per instance
        assert len(all_traps) == 7 * 3  # exactly 3 per instance (all 3 types)

    def test_trap_ids_unique_across_all_instances(self) -> None:
        from planner_critic.corpus import load_all_instances

        instances = load_all_instances("docs/field-test/corpus/swebench-security")
        all_traps: list[InjectionTrap] = []
        for inst in instances:
            all_traps.extend(generate_traps(inst))
        ids = [t.trap_id for t in all_traps]
        assert len(ids) == len(set(ids))


class TestInjectionTrap:
    def test_default_blocking(self) -> None:
        trap = InjectionTrap(
            trap_id="INJECT-TEST",
            instance_id="TEST-001",
            trap_type=TrapType.INSTRUCTION_OVERRIDE,
            description="test",
        )
        assert trap.blocked is False
        assert trap.blocking_layer is None

    def test_mark_blocked(self) -> None:
        trap = InjectionTrap(
            trap_id="INJECT-TEST",
            instance_id="TEST-001",
            trap_type=TrapType.INSTRUCTION_OVERRIDE,
            description="test",
        )
        trap.blocked = True
        trap.blocking_layer = "deterministic_gate"
        assert trap.blocked is True


class TestInjectionResult:
    def test_basic_result(self) -> None:
        trap = InjectionTrap(
            trap_id="INJECT-TEST",
            instance_id="TEST-001",
            trap_type=TrapType.INSTRUCTION_OVERRIDE,
            description="test",
        )
        result = InjectionResult(
            trap=trap,
            approved=False,
            blocking_layer="deterministic_gate",
            findings_count=3,
        )
        assert result.approved is False
        assert result.blocking_layer == "deterministic_gate"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])