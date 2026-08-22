from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from planner_critic.cli.eval import _run_regression_eval, build_eval_parser, run_eval
from planner_critic.cli.lessons import build_lessons_parser, run_lessons
from planner_critic.eval.label_migration import generate_boundary_cases
from planner_critic.eval.regression import generate_artifact
from planner_critic.gates import run_deterministic_gates
from planner_critic.corpus import load_all_instances

CORPUS_DIR = str(Path(__file__).resolve().parent.parent / "docs" / "field-test" / "corpus" / "swebench-security")


class TestEvalRegressionCLI:
    def test_regression_eval(self) -> None:
        results = _run_regression_eval(CORPUS_DIR)
        assert results["total_instances"] >= 1
        assert results["correct_plans_total"] >= 1

    def test_run_eval_regression(self) -> None:
        code = run_eval(["swebench-security", "--regression"])
        assert code == 0


class TestLessonsCLI:
    def test_lessons_propose(self) -> None:
        code = run_lessons(["propose"])
        assert code == 0

    def test_lessons_list_empty(self) -> None:
        code = run_lessons(["list"])
        assert code == 0

    def test_lessons_promote_unknown(self) -> None:
        code = run_lessons(["promote", "NONEXISTENT"])
        assert code == 1


class TestBoundaryCases:
    def test_generate_boundary_cases(self) -> None:
        cases = generate_boundary_cases()
        assert len(cases) >= 2
        for case in cases:
            assert case.case_id
            assert case.plan_a.id
            assert case.plan_b.id
            assert case.expected_reason_code


class TestRegressionArtifact:
    def test_artifact_generated_from_instances(self) -> None:
        instances = load_all_instances(CORPUS_DIR)
        assert len(instances) >= 1
        for inst in instances:
            artifact = generate_artifact(inst)
            assert artifact.correct is not None
            assert len(artifact.variants) >= 5

    def test_correct_skeleton_passes_gates(self) -> None:
        instances = load_all_instances(CORPUS_DIR)
        for inst in instances[:3]:
            artifact = generate_artifact(inst)
            findings = run_deterministic_gates(artifact.correct)
            assert len(findings) == 0

    def test_variants_trigger_expected_gates(self) -> None:
        instances = load_all_instances(CORPUS_DIR)
        for inst in instances[:3]:
            artifact = generate_artifact(inst)
            for i, variant in enumerate(artifact.variants):
                findings = run_deterministic_gates(variant)
                blockers = [f for f in findings if f.severity.value == "blocker"]
                expected = artifact.variant_expected[i] if i < len(artifact.variant_expected) else ""
                if expected:
                    assert any(
                        str(f.reason_code) == str(expected) for f in blockers
                    ), f"{inst.instance_id} variant {i} expected {expected} but got {[str(f.reason_code) for f in blockers]}"


def test_eval_parser_builds() -> None:
    parser = build_eval_parser()
    assert parser is not None


def test_lessons_parser_builds() -> None:
    parser = build_lessons_parser()
    assert parser is not None