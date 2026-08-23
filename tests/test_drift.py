from __future__ import annotations

from planner_critic.drift import check_drift_alert, compute_drift, compute_drift_summary
from planner_critic.reason_codes import (
    DRIFT_ALERT_TRIGGERED,
    FINDING_DRIFT_STORED,
    LLM_MISSING_STEPS,
)
from planner_critic.types import Finding, HeuristicFamily, Severity


def _finding(
    sev: Severity = Severity.WARNING,
    raw: Severity | None = Severity.BLOCKER,
    family: HeuristicFamily | None = HeuristicFamily.MISSING_STEPS,
) -> Finding:
    return Finding(
        id="f1", version=1, severity=sev,
        reason_code=LLM_MISSING_STEPS, message="test",
        heuristic_family=family,
        raw_severity=raw,
        normalized_severity=sev,
    )


def _deterministic_finding() -> Finding:
    from planner_critic.reason_codes import MISSING_ROLLBACK
    return Finding(
        id="f1", version=1, severity=Severity.BLOCKER,
        reason_code=MISSING_ROLLBACK, message="test",
        heuristic_family=None,
    )


class TestComputeDrift:
    def test_downgrade_blocker_to_warning(self) -> None:
        f = _finding(sev=Severity.WARNING, raw=Severity.BLOCKER)
        result = compute_drift(f)
        assert result.drift_delta == -1
        assert result.raw_severity is Severity.BLOCKER
        assert result.normalized_severity is Severity.WARNING

    def test_upgrade_not_applicable(self) -> None:
        f = _finding(sev=Severity.BLOCKER, raw=Severity.WARNING)
        result = compute_drift(f)
        assert result.drift_delta == 1

    def test_no_drift(self) -> None:
        f = _finding(sev=Severity.BLOCKER, raw=Severity.BLOCKER)
        result = compute_drift(f)
        assert result.drift_delta == 0

    def test_deterministic_gate_finding_no_drift(self) -> None:
        f = _deterministic_finding()
        result = compute_drift(f)
        assert result.drift_delta == 0
        assert result.raw_severity is None

    def test_legacy_finding_no_raw(self) -> None:
        from planner_critic.reason_codes import LLM_RISK
        f = Finding(
            id="f1", version=1, severity=Severity.WARNING,
            reason_code=LLM_RISK, message="test",
            heuristic_family=HeuristicFamily.RISK,
            raw_severity=None, normalized_severity=None,
        )
        result = compute_drift(f)
        assert result.raw_severity is Severity.WARNING
        assert result.normalized_severity is Severity.WARNING
        assert result.drift_delta == 0


class TestComputeDriftSummary:
    def test_no_drift(self) -> None:
        findings = [
            _finding(sev=Severity.BLOCKER, raw=Severity.BLOCKER),
            _finding(sev=Severity.WARNING, raw=Severity.WARNING),
        ]
        f2 = compute_drift(findings[0])
        f3 = compute_drift(findings[1])
        summary = compute_drift_summary([f2, f3])
        assert summary["drifted_count"] == 0
        assert summary["downgrade_rate"] == 0.0

    def test_some_drift(self) -> None:
        findings = [
            compute_drift(_finding(sev=Severity.WARNING, raw=Severity.BLOCKER)),
            compute_drift(_finding(sev=Severity.BLOCKER, raw=Severity.BLOCKER)),
        ]
        summary = compute_drift_summary(findings)
        assert summary["drifted_count"] == 1
        assert summary["downgrade_rate"] == 0.5

    def test_empty_findings(self) -> None:
        summary = compute_drift_summary([])
        assert summary["total_findings"] == 0
        assert summary["downgrade_rate"] == 0.0


class TestCheckDriftAlert:
    def test_insufficient_history(self) -> None:
        result = check_drift_alert([], "missing_steps")
        assert result["alert"] is False
        assert result["reason"] == "insufficient_history"

    def test_no_alert_when_stable(self) -> None:
        history = [
            [_finding(sev=Severity.WARNING, raw=Severity.WARNING) for _ in range(10)],
            [_finding(sev=Severity.WARNING, raw=Severity.WARNING) for _ in range(10)],
            [_finding(sev=Severity.WARNING, raw=Severity.WARNING) for _ in range(10)],
            [_finding(sev=Severity.WARNING, raw=Severity.WARNING) for _ in range(10)],
            [_finding(sev=Severity.WARNING, raw=Severity.WARNING) for _ in range(10)],
            [_finding(sev=Severity.WARNING, raw=Severity.WARNING) for _ in range(10)],
            [_finding(sev=Severity.WARNING, raw=Severity.WARNING) for _ in range(10)],
        ]
        result = check_drift_alert(history, "missing_steps")
        assert result["alert"] is False

    def test_alert_on_high_drift(self) -> None:
        history = [
            [_finding(sev=Severity.WARNING, raw=Severity.WARNING) for _ in range(10)],
            [_finding(sev=Severity.WARNING, raw=Severity.WARNING) for _ in range(10)],
            [_finding(sev=Severity.WARNING, raw=Severity.WARNING) for _ in range(10)],
            [_finding(sev=Severity.WARNING, raw=Severity.WARNING) for _ in range(10)],
            [_finding(sev=Severity.WARNING, raw=Severity.WARNING) for _ in range(10)],
            [_finding(sev=Severity.WARNING, raw=Severity.WARNING) for _ in range(10)],
            [_finding(sev=Severity.WARNING, raw=Severity.BLOCKER) for _ in range(8)],
        ]
        for i in range(len(history)):
            history[i] = [compute_drift(f) for f in history[i]]
        result = check_drift_alert(history, "missing_steps")
        assert result["alert"] is True
        assert result["reason_code"] == DRIFT_ALERT_TRIGGERED


class TestReasonCodes:
    def test_finding_drift_stored_exists(self) -> None:
        assert FINDING_DRIFT_STORED == "finding_drift_stored"

    def test_drift_alert_triggered_exists(self) -> None:
        assert DRIFT_ALERT_TRIGGERED == "drift_alert_triggered"
