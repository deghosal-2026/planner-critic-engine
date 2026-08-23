"""Wiring test for the #218 live-critic boundary bench script.

Hermetic ($0): exercises the script's self-test path and report-artifact
writing with a stub critic, proving the end-to-end wiring (cases → harness →
JSON + markdown files) is correct before a paid live run. The live run itself
is invoked separately via ``python3 docs/field-test/v0.2.1/scripts/bench_live_boundary.py``
and is NOT part of CI (it spends money).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "docs" / "field-test" / "v0.2.1" / "scripts"
BENCH_PATH = SCRIPTS_DIR / "bench_live_boundary.py"


@pytest.fixture()
def bench_module() -> object:
    """Import the bench script as a module (it lives outside the package)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("bench_live_boundary", BENCH_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["bench_live_boundary"] = module
    spec.loader.exec_module(module)
    return module


def test_self_test_passes(bench_module: object) -> None:
    """The script's hermetic self-test reports all wiring checks passing."""
    result = bench_module.self_test()  # type: ignore[attr-defined]
    assert result["all_pass"] is True
    for check_name, ok in result["checks"].items():
        assert ok, f"self-test check failed: {check_name}"


def test_run_boundary_writes_artifacts(bench_module: object, tmp_path: Path) -> None:
    """run_boundary writes JSON + markdown with the required metric keys."""
    bench_module.RESULTS_DIR = tmp_path  # type: ignore[attr-defined]
    bench_module.run_boundary(  # type: ignore[attr-defined]
        bench_module._StubCritic(),  # type: ignore[attr-defined]
        trials=3,
        model="stub",
    )

    json_path = tmp_path / "live-boundary-report.json"
    md_path = tmp_path / "live-boundary-report.md"
    assert json_path.exists()
    assert md_path.exists()

    written = json.loads(json_path.read_text())
    for key in (
        "label_flip_rate",
        "family_migration_rate",
        "evidence_drift_rate",
        "underclaim_approvals",
        "cases_evaluated",
        "trials_per_plan",
        "cases",
        "model",
    ):
        assert key in written, f"missing metric in report: {key}"
    assert written["trials_per_plan"] == 3
    assert written["model"] == "stub"
    assert len(written["cases"]) == written["cases_evaluated"]

    md = md_path.read_text()
    assert "# Live-critic boundary-case report" in md
    assert "`stub`" in md
    assert "| label_flip_rate |" in md


def test_build_provider_errors_without_config(
    bench_module: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """build_provider fails closed when no toml and no env vars are set."""
    monkeypatch.setattr(bench_module, "REPO_ROOT", tmp_path)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="no critic provider configured"):
        bench_module.build_provider()  # type: ignore[attr-defined]
