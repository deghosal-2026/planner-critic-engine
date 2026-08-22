"""Tests for the security oracle eval harness (M5, #124)."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import ScriptedCritic, ScriptedPlanner, make_plan, make_task
from planner_critic.corpus.types import CWEBucket, SecurityInstance
from planner_critic.eval.oracle import EvalScorecard, InstanceResult, OracleEvalHarness, save_report


class TestInstanceResult:
    def test_counts(self) -> None:
        result = InstanceResult(
            instance_id="TEST-001", cwe="CWE-79", cwe_bucket="XSS"
        )
        assert result.aligned_count == 0
        assert result.missed_count == 0
        assert result.spurious_count == 0


class TestEvalScorecard:
    def test_compute_accuracy(self) -> None:
        scorecard = EvalScorecard(total_aligned=8, total_missed=2)
        scorecard.compute()
        assert scorecard.accuracy == 0.8

    def test_perfect_accuracy(self) -> None:
        scorecard = EvalScorecard(total_aligned=10, total_missed=0)
        scorecard.compute()
        assert scorecard.accuracy == 1.0

    def test_zero_total_does_not_divide(self) -> None:
        scorecard = EvalScorecard()
        scorecard.compute()
        assert scorecard.accuracy == 0.0

    def test_to_dict_structure(self) -> None:
        scorecard = EvalScorecard(
            total_instances=3, total_aligned=5, total_missed=2
        )
        scorecard.compute()
        d = scorecard.to_dict()
        assert d["total_instances"] == 3
        assert d["total_aligned"] == 5
        assert "accuracy" in d


class TestOracleEvalHarness:
    def test_run_instance_with_scripted_roles(self) -> None:
        """Run the harness with scripted planner/critic (no LLM)."""
        planner = ScriptedPlanner([make_plan(tasks=[make_task("fix-encoding")])])
        critic = ScriptedCritic([[]])

        instance = SecurityInstance(
            instance_id="TEST-001",
            cwe="CWE-79",
            cwe_bucket=CWEBucket.XSS,
            vulnerability_class="xss",
            issue_description="XSS in search page",
            goal_text="Fix XSS vulnerability in search page by adding output encoding",
            ground_truth_summary="Apply HTML encoding to all user-controlled data",
            expected_critic_signal=None,
            expected_reason_codes=["missing_verification"],
        )

        harness = OracleEvalHarness(planner, critic)
        result = harness.run_instance(instance)
        assert result.instance_id == "TEST-001"
        assert isinstance(result, InstanceResult)

    def test_run_all_returns_scorecard(self) -> None:
        """run_all produces a scorecard with all corpus instances."""
        planner = ScriptedPlanner([make_plan(tasks=[make_task("t1")])])
        critic = ScriptedCritic([[]])

        harness = OracleEvalHarness(planner, critic)
        scorecard, results = harness.run_all()
        assert isinstance(scorecard, EvalScorecard)
        assert len(results) > 0


class TestSaveReport:
    def test_save_json_report(self, tmp_path: Path) -> None:
        scorecard = EvalScorecard(total_instances=1, total_aligned=2, total_missed=1)
        scorecard.compute()

        out = tmp_path / "report.json"
        save_report(scorecard, str(out))
        assert out.exists()
        content = out.read_text()
        assert '"total_instances"' in content
        assert '"accuracy"' in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])