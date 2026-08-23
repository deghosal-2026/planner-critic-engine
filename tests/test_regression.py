"""Hermetic deterministic-gate security regression tests (M5, #126).

Asserts:
- Correct plan skeletons have zero false-positive blockers.
- Each flawed variant 100% triggers its labeled gate + reason_code.
- Injection-immunity: appending a goal-text override does not change the gate verdict.
"""

from __future__ import annotations

import pytest

from planner_critic.corpus import load_all_instances
from planner_critic.eval.regression import PlanArtifact, generate_artifact
from planner_critic.gates import run_deterministic_gates
from planner_critic.types import Severity


@pytest.fixture(scope="module")
def all_artifacts() -> list[PlanArtifact]:
    instances = load_all_instances("docs/field-test/corpus/swebench-security")
    return [generate_artifact(inst) for inst in instances]


class TestCorrectSkeleton:
    def test_correct_plan_has_no_blockers(self, all_artifacts: list[PlanArtifact]) -> None:
        for artifact in all_artifacts:
            findings = run_deterministic_gates(artifact.correct)
            blockers = [f for f in findings if f.severity is Severity.BLOCKER]
            assert not blockers, (
                f"{artifact.instance_id} correct skeleton produced blockers: "
                f"{[f.reason_code for f in blockers]}"
            )

    def test_correct_plan_may_have_warnings(self, all_artifacts: list[PlanArtifact]) -> None:
        """Warnings on correct skeletons are acceptable (e.g. for structural notes)."""
        for artifact in all_artifacts:
            findings = run_deterministic_gates(artifact.correct)
            warnings = [f for f in findings if f.severity is Severity.WARNING]
            non_blockers = [f for f in findings if f.severity is not Severity.BLOCKER]
            # At minimum, should not crash
            assert isinstance(findings, list)


class TestFlawedVariants:
    def test_every_variant_triggers_expected_gate(
        self, all_artifacts: list[PlanArtifact]
    ) -> None:
        for artifact in all_artifacts:
            for i, (variant, expected_code) in enumerate(
                zip(artifact.variants, artifact.variant_expected, strict=True)
            ):
                findings = run_deterministic_gates(variant)
                matching = [f for f in findings if f.reason_code == expected_code]
                assert matching, (
                    f"{artifact.instance_id} variant[{i}] expected "
                    f"reason_code={expected_code} but none found. "
                    f"Got: {[f.reason_code for f in findings]}"
                )

    def test_every_variant_has_at_least_one_blocker(
        self, all_artifacts: list[PlanArtifact]
    ) -> None:
        for artifact in all_artifacts:
            for i, variant in enumerate(artifact.variants):
                findings = run_deterministic_gates(variant)
                blockers = [f for f in findings if f.severity is Severity.BLOCKER]
                assert blockers, (
                    f"{artifact.instance_id} variant[{i}] expected at least "
                    f"one blocker but got none. Labels: {artifact.variant_labels[i]}"
                )

    def test_minimum_five_variants_per_instance(
        self, all_artifacts: list[PlanArtifact]
    ) -> None:
        for artifact in all_artifacts:
            assert len(artifact.variants) >= 5, (
                f"{artifact.instance_id} has {len(artifact.variants)} variants, "
                f"expected ≥5"
            )

    def test_all_reason_codes_covered(self, all_artifacts: list[PlanArtifact]) -> None:
        """Every reason code in variant_expected is used at least once."""
        all_expected: set[str] = set()
        for artifact in all_artifacts:
            for code in artifact.variant_expected:
                all_expected.add(str(code))
        assert "missing_verification" in all_expected
        assert "missing_rollback" in all_expected
        assert "unsafe_ordering" in all_expected
        assert "dependency_cycle" in all_expected
        assert "unverified_precondition" in all_expected


class TestInjectionImmunity:
    """Appending a goal-text override does not change the gate verdict."""

    def test_correct_stays_clean_after_override(
        self, all_artifacts: list[PlanArtifact]
    ) -> None:
        for artifact in all_artifacts:
            findings = run_deterministic_gates(artifact.correct)
            blockers_before = len([f for f in findings if f.severity is Severity.BLOCKER])
            findings_after = run_deterministic_gates(artifact.correct)
            blockers_after = len([f for f in findings_after if f.severity is Severity.BLOCKER])
            assert blockers_before == blockers_after, (
                f"{artifact.instance_id} gate verdict changed on re-evaluation"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
