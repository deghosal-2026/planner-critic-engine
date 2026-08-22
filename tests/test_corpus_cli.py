"""Tests for ``plancritic corpus`` CLI (M5, #123)."""

from __future__ import annotations

from pathlib import Path

import pytest

from planner_critic.cli.corpus import build_corpus_parser, run_corpus


class TestCorpusParser:
    def test_parser_accepts_list(self) -> None:
        parser = build_corpus_parser()
        args = parser.parse_args(["list"])
        assert args.action == "list"

    def test_parser_accepts_show(self) -> None:
        parser = build_corpus_parser()
        args = parser.parse_args(["show", "CWE-079-001"])
        assert args.action == "show"
        assert args.instance_id == "CWE-079-001"

    def test_parser_accepts_manifest(self) -> None:
        parser = build_corpus_parser()
        args = parser.parse_args(["manifest"])
        assert args.action == "manifest"

    def test_parser_accepts_load(self) -> None:
        parser = build_corpus_parser()
        args = parser.parse_args(["load"])
        assert args.action == "load"

    def test_parser_accepts_verify_flag(self) -> None:
        parser = build_corpus_parser()
        args = parser.parse_args(["load", "--verify-checksums"])
        assert args.verify_checksums is True


class TestCorpusRun:
    def test_list_returns_zero(self) -> None:
        rc = run_corpus(["list"])
        assert rc == 0

    def test_show_returns_zero(self) -> None:
        rc = run_corpus(["show", "CWE-079-001"])
        assert rc == 0

    def test_show_unknown_returns_one(self) -> None:
        rc = run_corpus(["show", "NONEXISTENT"])
        assert rc == 1

    def test_manifest_returns_zero(self) -> None:
        rc = run_corpus(["manifest"])
        assert rc == 0

    def test_load_returns_zero(self) -> None:
        rc = run_corpus(["load"])
        assert rc == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])