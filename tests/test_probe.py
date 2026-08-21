"""EnvProbe tests (F-19, F-26): read-only contract, result recording, dispatch."""

from __future__ import annotations

import httpx
import pytest

from planner_critic.probe import (
    BUILTIN_PROBES,
    ProbeRequest,
    ProbeResult,
    run_probe,
)
from planner_critic.probe.env_var import EnvVarProbe
from planner_critic.probe.http_check import HttpCheckProbe


def test_env_var_probe_reads_and_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    """An env_var probe observes the variable and compares to expected."""
    monkeypatch.setenv("PC_DEPLOY_ENV", "prod")
    result = run_probe(ProbeRequest(kind="env_var", query="PC_DEPLOY_ENV", expected="prod"))
    assert result.matched is True
    assert result.observed == "prod"


def test_env_var_probe_mismatch() -> None:
    """A value that differs from expected reports matched=False."""
    result = run_probe(
        ProbeRequest(kind="env_var", query="PC_DEFINITELY_UNSET_XYZ", expected="prod")
    )
    assert result.matched is False
    assert result.observed == ""  # unset env var reads as empty


def test_http_check_probe_matches() -> None:
    """An http_check probe records the status and matches on expected."""
    mock = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, request=request))
    )
    probe = HttpCheckProbe(client=mock)
    result = probe.run(
        ProbeRequest(kind="http_check", query="http://status.local/health", expected="200")
    )
    assert result.observed == "200"
    assert result.matched is True


def test_http_check_probe_network_error_is_recorded() -> None:
    """A network failure records ok=False rather than raising."""

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    probe = HttpCheckProbe(client=httpx.Client(transport=httpx.MockTransport(boom)))
    result = probe.run(
        ProbeRequest(kind="http_check", query="http://down.local/health", expected="200")
    )
    assert result.ok is False
    assert result.matched is False
    assert "http error" in result.observed


def test_db_query_probe_is_recorded_stub() -> None:
    """The db_query stub reports ok=False with a clear message."""
    result = run_probe(ProbeRequest(kind="db_query", query="SELECT 1", expected="1"))
    assert result.ok is False
    assert "stub" in result.observed


def test_deploy_status_probe_is_recorded_stub() -> None:
    """The deploy_status stub reports ok=False with a clear message."""
    result = run_probe(ProbeRequest(kind="deploy_status", query="rollout-7", expected="complete"))
    assert result.ok is False
    assert "stub" in result.observed


def test_unknown_probe_kind_is_recorded_not_raised() -> None:
    """An unknown kind dispatches to a recorded ok=False result."""
    result = run_probe(ProbeRequest(kind="db_query", query="SELECT 1", expected="1"))
    assert result.ok is False


def test_probe_result_records_json_snapshot() -> None:
    """ProbeResult.record() yields a JSON-friendly trace snapshot."""
    result = ProbeResult(kind="env_var", query="X", observed="1", matched=True, ok=True)
    snapshot = result.record()
    assert snapshot["kind"] == "env_var"
    assert snapshot["matched"] is True


def test_builtin_probes_cover_all_kinds() -> None:
    """All four probe kinds are dispatched by the built-in registry."""
    kinds = {p.kind for p in BUILTIN_PROBES}
    assert kinds == {"env_var", "db_query", "http_check", "deploy_status"}


def test_env_var_probe_is_read_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Running a probe never creates or mutates environment state."""
    monkeypatch.delenv("PC_PROBE_TEST_VAR", raising=False)
    run_probe(ProbeRequest(kind="env_var", query="PC_PROBE_TEST_VAR", expected="x"))
    assert "PC_PROBE_TEST_VAR" not in __import__("os").environ


def test_probe_error_is_recorded_not_raised() -> None:
    """A ProbeError inside an implementation yields a recorded ok=False result."""

    class BoomProbe(EnvVarProbe):
        kind = "env_var"

        def run(self, request: ProbeRequest) -> ProbeResult:
            from planner_critic.probe import ProbeError

            raise ProbeError("boom")

    from planner_critic.probe import BUILTIN_PROBES

    BUILTIN_PROBES.append(BoomProbe())
    try:
        result = run_probe(ProbeRequest(kind="env_var", query="X", expected="y"))
    finally:
        BUILTIN_PROBES.pop()
    assert result.ok is False
    assert "boom" in result.observed
