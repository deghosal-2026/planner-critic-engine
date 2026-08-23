"""``plancritic eval`` CLI tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from planner_critic.cli.eval import run_eval


def _make_corpus(tmp_path: Path) -> str:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir(parents=True)
    manifest = corpus_dir / "manifest.json"
    manifest.write_text(json.dumps({
        "name": "test-corpus", "version": "1.0", "instance_count": 0,
        "created": "2026-01-01",
    }))
    return str(corpus_dir)


def test_eval_no_manifest(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    rc = run_eval(["swebench-security", "--corpus-dir", str(tmp_path / "empty")])
    assert rc == 1
    out = capsys.readouterr().out
    assert "not found" in out.lower()


def test_eval_no_flags(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    corpus_dir = _make_corpus(tmp_path)
    rc = run_eval(["swebench-security", "--corpus-dir", corpus_dir])
    assert rc == 0
    out = capsys.readouterr().out
    assert "--regression" in out or "--adversarial" in out


def test_eval_regression(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    corpus_dir = _make_corpus(tmp_path)
    rc = run_eval(["swebench-security", "--corpus-dir", corpus_dir, "--regression"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Corpus" in out


def test_eval_adversarial(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    corpus_dir = _make_corpus(tmp_path)
    rc = run_eval(["swebench-security", "--corpus-dir", corpus_dir, "--adversarial"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Adversarial" in out


def test_eval_with_report_dir(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    corpus_dir = _make_corpus(tmp_path)
    report_dir = tmp_path / "reports"
    rc = run_eval(["swebench-security", "--corpus-dir", corpus_dir,
                   "--regression", "--report-dir", str(report_dir)])
    assert rc == 0
