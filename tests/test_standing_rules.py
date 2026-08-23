"""Tests for standing-rule promotion (M5, #127)."""

from __future__ import annotations

import pytest

from planner_critic.eval.standing_rules import (
    CWE_PATTERN_MAP,
    HEURISTIC_FAMILY_FOR_BUCKET,
    StandingRule,
    StandingRuleRegistry,
)


class TestCWEPatternMap:
    def test_all_buckets_have_patterns(self) -> None:
        expected = {"XSS", "SQLI", "PATH_TRAVERSAL", "AUTH", "DESERIALIZATION", "SSRF", "SECRETS"}
        assert set(CWE_PATTERN_MAP.keys()) == expected

    def test_all_buckets_have_heuristic_family(self) -> None:
        for bucket in CWE_PATTERN_MAP:
            assert bucket in HEURISTIC_FAMILY_FOR_BUCKET


class TestStandingRule:
    def test_default_status_is_proposed(self) -> None:
        rule = StandingRule(
            rule_id="SR-XSS-OUTPUT_ENCODING",
            cwe_bucket="XSS",
            pattern="output_encoding",
            heuristic_family="missing_steps",
            reason_code="missing_verification",
        )
        assert rule.status == "proposed"
        assert rule.trust == "high"

    def test_full_standing_rule(self) -> None:
        rule = StandingRule(
            rule_id="SR-SQLI-PARAMETERIZED_QUERY",
            cwe_bucket="SQLI",
            pattern="parameterized_query",
            heuristic_family="missing_steps",
            reason_code="missing_verification",
            status="promoted",
            coverage_count=3,
            source_instance_ids=["CWE-089-001", "CWE-089-002"],
        )
        assert rule.status == "promoted"
        assert rule.coverage_count == 3


class TestStandingRuleRegistry:
    def test_propose_creates_rules(self) -> None:
        registry = StandingRuleRegistry()
        proposed = registry.propose_from_misses(
            cwe_bucket="XSS",
            instance_ids=["CWE-079-001"],
            missed_reason_codes=["missing_verification"],
        )
        assert len(proposed) > 0
        for rule in proposed:
            assert rule.cwe_bucket == "XSS"
            assert rule.status == "proposed"

    def test_propose_dedup_reuses_existing(self) -> None:
        registry = StandingRuleRegistry()
        _ = registry.propose_from_misses(
            cwe_bucket="XSS",
            instance_ids=["CWE-079-001"],
            missed_reason_codes=["missing_verification"],
        )
        second = registry.propose_from_misses(
            cwe_bucket="XSS",
            instance_ids=["CWE-079-002"],
            missed_reason_codes=["missing_verification"],
        )
        # No new rules created — existing ones incremented
        assert len(second) == 0

    def test_promote_changes_status(self) -> None:
        registry = StandingRuleRegistry()
        proposed = registry.propose_from_misses(
            cwe_bucket="SQLI",
            instance_ids=["CWE-089-001"],
            missed_reason_codes=["missing_verification"],
        )
        assert proposed
        rule_id = proposed[0].rule_id
        assert registry.promote(rule_id) is True
        promoted = registry.list_rules(status="promoted")
        assert len(promoted) == 1
        assert promoted[0].rule_id == rule_id

    def test_promote_idempotent(self) -> None:
        registry = StandingRuleRegistry()
        proposed = registry.propose_from_misses(
            cwe_bucket="AUTH",
            instance_ids=["CWE-287-001"],
            missed_reason_codes=["unsafe_ordering"],
        )
        rule_id = proposed[0].rule_id
        assert registry.promote(rule_id) is True
        assert registry.promote(rule_id) is False  # already promoted

    def test_promote_unknown_returns_false(self) -> None:
        registry = StandingRuleRegistry()
        assert registry.promote("NONEXISTENT") is False

    def test_list_filters_by_status(self) -> None:
        registry = StandingRuleRegistry()
        registry.propose_from_misses(
            cwe_bucket="SSRF",
            instance_ids=["CWE-918-001"],
            missed_reason_codes=["unverified_precondition"],
        )
        proposed = registry.list_rules(status="proposed")
        promoted = registry.list_rules(status="promoted")
        assert len(proposed) >= 1
        assert len(promoted) == 0

    def test_coverage_count_increments(self) -> None:
        registry = StandingRuleRegistry()
        registry.propose_from_misses(
            cwe_bucket="XSS",
            instance_ids=["CWE-079-001"],
            missed_reason_codes=["missing_verification"],
        )
        registry.propose_from_misses(
            cwe_bucket="XSS",
            instance_ids=["CWE-079-002"],
            missed_reason_codes=["missing_verification"],
        )
        rules = registry.list_rules()
        for rule in rules:
            if rule.cwe_bucket == "XSS":
                assert rule.coverage_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
