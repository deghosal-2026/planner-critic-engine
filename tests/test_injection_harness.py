"""Tests for the adversarial injection harness (M5, #125)."""

from __future__ import annotations

import pytest

from conftest import ScriptedCritic, ScriptedPlanner, make_plan, make_task
from planner_critic.eval.injection_harness import (
    injection_summary,
    run_injection_harness,
)
from planner_critic.loop import LoopConfig


class TestRunInjectionHarness:
    def test_runs_hermetically(self) -> None:
        """Run injection harness with scripted roles (no LLM)."""
        planner = ScriptedPlanner([make_plan(tasks=[make_task("t1")])])
        critic = ScriptedCritic([[]])

        results = run_injection_harness(planner, critic)
        assert len(results) > 0
        assert all(isinstance(r.blocking_layer, (str, type(None))) for r in results)

    def test_instance_filter(self) -> None:
        """Filter to specific instance IDs."""
        planner = ScriptedPlanner([make_plan(tasks=[make_task("t1")])])
        critic = ScriptedCritic([[]])

        results = run_injection_harness(planner, critic, instance_ids=["CWE-079-001"])
        # 1 instance x 3 trap types = 3 traps
        assert len(results) == 3
        for r in results:
            assert "CWE-079-001" in r.trap.trap_id

    def test_deterministic_first_mode(self) -> None:
        """Run with deterministic-first loop mode."""
        planner = ScriptedPlanner([make_plan(tasks=[make_task("t1")])])
        critic = ScriptedCritic([[]])

        results = run_injection_harness(
            planner,
            critic,
            loop_config=LoopConfig(mode="deterministic-first"),
        )
        assert len(results) > 0


class TestInjectionSummary:
    def test_summary_structure(self) -> None:
        planner = ScriptedPlanner([make_plan(tasks=[make_task("t1")])])
        critic = ScriptedCritic([[]])

        results = run_injection_harness(planner, critic)
        summary = injection_summary(results)

        assert summary["total_traps"] == len(results)
        assert "injection_immunity_rate" in summary
        assert "blocked" in summary
        assert "bypassed" in summary
        assert "blocked_by_gate" in summary
        assert "blocked_by_llm" in summary

    def test_immunity_rate_between_0_and_100(self) -> None:
        planner = ScriptedPlanner([make_plan(tasks=[make_task("t1")])])
        critic = ScriptedCritic([[]])

        results = run_injection_harness(planner, critic)
        summary = injection_summary(results)
        assert 0.0 <= summary["injection_immunity_rate"] <= 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
