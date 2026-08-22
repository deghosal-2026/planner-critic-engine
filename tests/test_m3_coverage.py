"""Targeted coverage tests for M3 modules (policy, domain, pytest_plugin)."""

from __future__ import annotations

from planner_critic.domains.base import find_domain_packs
from planner_critic.policy import CelGate
from planner_critic.pytest_plugin import format_dag_diff


class TestDomainPackDiscoveryEdgeCases:
    """Edge cases for find_domain_packs."""

    def test_find_in_nonexistent_namespace(self) -> None:
        """A namespace that doesn't exist returns an empty dict."""
        packs = find_domain_packs("planner_critic.does_not_exist")
        assert packs == {}

    def test_find_in_empty_subpackage(self) -> None:
        """A subpackage with no domain_pack attribute returns nothing."""
        packs = find_domain_packs("planner_critic.adapters")
        assert isinstance(packs, dict)


class TestPolicyEdgeCases:
    """Edge cases for the policy engine."""

    def test_cel_gate_invalid_expression_returns_finding(self) -> None:
        """An expression that raises during eval produces a finding."""
        gate = CelGate(name="bad-expr", expression="1/0")
        from conftest import make_plan

        findings = gate.evaluate(make_plan())
        assert len(findings) == 1
        assert findings[0].reason_code == "policy_violation"

    def test_cel_gate_syntax_error_returns_finding(self) -> None:
        """A syntax error in the CEL expression produces a finding."""
        gate = CelGate(name="syntax", expression="invalid syntax!!!")
        from conftest import make_plan

        findings = gate.evaluate(make_plan())
        assert len(findings) == 1


class TestPytestPluginEdgeCases:
    """Edge cases for the pytest plugin."""

    def test_format_diff_with_different_edges(self) -> None:
        """Two plans with different edge sets produce edge diffs."""
        from conftest import hard_dep, make_plan, make_task

        a = make_plan(
            tasks=[make_task("A"), make_task("B")],
            dependencies=[hard_dep("A", "B")],
        )
        b = make_plan(
            tasks=[make_task("A"), make_task("B")],
            dependencies=[hard_dep("B", "A")],
        )
        diff = format_dag_diff(a, b)
        assert "edge" in diff.lower() or "edge" in diff

    def test_format_diff_with_different_tasks(self) -> None:
        """Two plans with different task sets produce task diffs."""
        from conftest import make_plan, make_task

        a = make_plan(tasks=[make_task("A"), make_task("B")])
        b = make_plan(tasks=[make_task("A")])
        diff = format_dag_diff(a, b)
        assert "only" in diff.lower()
