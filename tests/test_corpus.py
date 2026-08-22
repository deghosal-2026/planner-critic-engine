"""Security corpus types and loader tests (M5, #123)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from planner_critic.corpus.types import (
    CWEBucket,
    CorpusManifest,
    ExpectedCriticSignal,
    SecurityInstance,
)
from planner_critic.corpus.loader import (
    load_all_instances,
    load_corpus_manifest,
    load_instance,
    list_instances,
)


class TestCWEBucket:
    def test_has_seven_buckets(self) -> None:
        assert len(CWEBucket) == 7

    def test_all_buckets_have_cwe_labels(self) -> None:
        from planner_critic.corpus.types import CWE_LABELS
        for bucket in CWEBucket:
            assert bucket in CWE_LABELS
            assert len(CWE_LABELS[bucket]) >= 1


class TestSecurityInstance:
    def test_minimal_instance(self) -> None:
        inst = SecurityInstance(
            instance_id="TEST-001",
            cwe="CWE-79",
            cwe_bucket=CWEBucket.XSS,
            vulnerability_class="xss",
            issue_description="test",
            goal_text="fix xss",
            ground_truth_summary="encode output",
        )
        assert inst.instance_id == "TEST-001"
        assert inst.cwe_bucket is CWEBucket.XSS
        assert inst.expected_critic_signal is None

    def test_full_instance(self) -> None:
        inst = SecurityInstance(
            instance_id="FULL-001",
            cwe="CWE-89",
            cwe_bucket=CWEBucket.SQL_INJECTION,
            vulnerability_class="sql_injection",
            issue_description="SQL injection in user lookup",
            goal_text="Fix SQL injection",
            ground_truth_summary="Use parameterised queries",
            expected_critic_signal=ExpectedCriticSignal.MISSING_STEPS,
            expected_reason_codes=["missing_verification"],
            ground_truth_patch="diff --git a/app.py b/app.py\n...",
            checksum="abc123",
            provenance={"type": "synthetic", "source": "test"},
        )
        assert inst.expected_critic_signal is ExpectedCriticSignal.MISSING_STEPS
        assert "missing_verification" in inst.expected_reason_codes
        assert inst.checksum == "abc123"


class TestCorpusManifest:
    def test_minimal_manifest(self) -> None:
        manifest = CorpusManifest(
            name="test-corpus",
            created=date(2026, 8, 22),
            instance_count=0,
        )
        assert manifest.name == "test-corpus"
        assert manifest.instance_count == 0

    def test_with_instances(self) -> None:
        manifest = CorpusManifest(
            name="swebench-security",
            created=date(2026, 8, 22),
            instance_count=2,
            instances={"CWE-001": "aaa", "CWE-002": "bbb"},
            cwe_counts={CWEBucket.XSS: 1, CWEBucket.SQL_INJECTION: 1},
        )
        assert manifest.instances["CWE-001"] == "aaa"
        assert manifest.cwe_counts[CWEBucket.XSS] == 1


class TestCorpusLoader:
    def test_load_manifest(self) -> None:
        manifest = load_corpus_manifest(
            "docs/field-test/corpus/swebench-security"
        )
        assert manifest is not None
        assert manifest.name == "swebench-security"
        assert manifest.instance_count == 7

    def test_load_all_instances(self) -> None:
        instances = load_all_instances(
            "docs/field-test/corpus/swebench-security"
        )
        assert len(instances) == 7
        ids = {inst.instance_id for inst in instances}
        assert "CWE-079-001" in ids
        assert "CWE-089-001" in ids
        assert "CWE-022-001" in ids
        assert "CWE-287-001" in ids
        assert "CWE-502-001" in ids
        assert "CWE-918-001" in ids
        assert "CWE-798-001" in ids

    def test_load_instance(self) -> None:
        inst = load_instance(
            "docs/field-test/corpus/swebench-security", "CWE-079-001"
        )
        assert inst is not None
        assert inst.cwe == "CWE-79"
        assert inst.cwe_bucket is CWEBucket.XSS

    def test_load_instance_not_found(self) -> None:
        inst = load_instance(
            "docs/field-test/corpus/swebench-security", "NONEXISTENT"
        )
        assert inst is None

    def test_list_instances_returns_metadata(self) -> None:
        rows = list_instances("docs/field-test/corpus/swebench-security")
        assert len(rows) == 7
        assert all("instance_id" in r for r in rows)
        assert all("cwe_bucket" in r for r in rows)

    def test_cwe_buckets_covered(self) -> None:
        instances = load_all_instances(
            "docs/field-test/corpus/swebench-security"
        )
        buckets = {inst.cwe_bucket for inst in instances}
        assert CWEBucket.XSS in buckets
        assert CWEBucket.SQL_INJECTION in buckets
        assert CWEBucket.PATH_TRAVERSAL in buckets
        assert CWEBucket.AUTHENTICATION in buckets
        assert CWEBucket.DESERIALIZATION in buckets
        assert CWEBucket.SSRF in buckets
        assert CWEBucket.SECRET_HANDLING in buckets

    def test_all_instances_have_goal_text(self) -> None:
        instances = load_all_instances(
            "docs/field-test/corpus/swebench-security"
        )
        for inst in instances:
            assert inst.goal_text, f"{inst.instance_id} missing goal_text"

    def test_all_instances_have_expected_signal(self) -> None:
        instances = load_all_instances(
            "docs/field-test/corpus/swebench-security"
        )
        for inst in instances:
            assert inst.expected_critic_signal is not None, (
                f"{inst.instance_id} missing expected_critic_signal"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestLoaderCoverage:
    """Targeted tests for coverage of loader edge cases."""

    def test_compute_sha256_returns_hex(self) -> None:
        from planner_critic.corpus.loader import _compute_sha256
        digest = _compute_sha256({"key": "value"})
        assert isinstance(digest, str)
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)

    def test_load_manifest_nonexistent_dir(self) -> None:
        manifest = load_corpus_manifest("/nonexistent/path")
        assert manifest is None

    def test_load_all_instances_nonexistent_instances_dir(self, tmp_path) -> None:
        instances = load_all_instances(str(tmp_path))
        assert instances == []

    def test_load_all_instances_with_verify_checksums(self) -> None:
        instances = load_all_instances(
            "docs/field-test/corpus/swebench-security",
            verify_checksums=True,
        )
        assert len(instances) > 0