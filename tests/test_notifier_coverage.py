"""Coverage tests for notifier.py — deliver and notify paths."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from planner_critic.notifier import (
    EscalationEvent,
    Notifier,
    SlackFormatter,
    TeamsFormatter,
    WebhookFormatter,
)


def _make_event() -> EscalationEvent:
    return EscalationEvent(
        escalation_id="esc-1",
        plan_id="plan-1",
        reason_code="budget_exceeded",
        question="What should we do?",
        severity="blocker",
        environment="prod",
        service="api",
        summary="3 tasks",
    )


def test_slack_deliver_success() -> None:
    fmt = SlackFormatter(webhook_url="https://hooks.slack.com/test", channel="#ops")
    payload = fmt.format_event(_make_event())
    assert "blocks" in payload
    assert payload["channel"] == "#ops"

    mock_resp = MagicMock()
    mock_resp.is_success = True
    mock_resp.status_code = 200
    mock_resp.text = "ok"

    with patch("httpx.post", return_value=mock_resp):
        result = fmt.deliver(payload)
    assert result.success
    assert result.status_code == 200


def test_slack_deliver_failure() -> None:
    fmt = SlackFormatter(webhook_url="https://hooks.slack.com/test")
    payload = fmt.format_event(_make_event())

    mock_resp = MagicMock()
    mock_resp.is_success = False
    mock_resp.status_code = 500
    mock_resp.text = "error"

    with patch("httpx.post", return_value=mock_resp):
        result = fmt.deliver(payload)
    assert not result.success
    assert result.status_code == 500


def test_slack_deliver_exception() -> None:
    fmt = SlackFormatter(webhook_url="https://hooks.slack.com/test")
    payload = fmt.format_event(_make_event())

    with patch("httpx.post", side_effect=Exception("network error")):
        result = fmt.deliver(payload)
    assert not result.success
    assert "network error" in (result.error or "")


def test_teams_deliver_success() -> None:
    fmt = TeamsFormatter(webhook_url="https://hooks.teams.com/test")
    payload = fmt.format_event(_make_event())
    assert "@type" in payload or "type" in str(payload)

    mock_resp = MagicMock()
    mock_resp.is_success = True
    mock_resp.status_code = 200
    mock_resp.text = "ok"

    with patch("httpx.post", return_value=mock_resp):
        result = fmt.deliver(payload)
    assert result.success


def test_teams_deliver_exception() -> None:
    fmt = TeamsFormatter(webhook_url="https://hooks.teams.com/test")
    payload = fmt.format_event(_make_event())

    with patch("httpx.post", side_effect=Exception("timeout")):
        result = fmt.deliver(payload)
    assert not result.success


def test_webhook_deliver_success() -> None:
    fmt = WebhookFormatter(webhook_url="https://example.com/webhook")
    payload = fmt.format_event(_make_event())
    assert "escalation_id" in payload
    assert payload["reason_code"] == "budget_exceeded"

    mock_resp = MagicMock()
    mock_resp.is_success = True
    mock_resp.status_code = 200
    mock_resp.text = "ok"

    with patch("httpx.post", return_value=mock_resp):
        result = fmt.deliver(payload)
    assert result.success


def test_webhook_deliver_exception() -> None:
    fmt = WebhookFormatter(webhook_url="https://example.com/webhook")
    payload = fmt.format_event(_make_event())

    with patch("httpx.post", side_effect=Exception("dns error")):
        result = fmt.deliver(payload)
    assert not result.success


def test_notifier_notify_success() -> None:
    notifier = Notifier()
    fmt = SlackFormatter(webhook_url="https://hooks.slack.com/test")
    notifier.register("slack", fmt)

    mock_resp = MagicMock()
    mock_resp.is_success = True
    mock_resp.status_code = 200
    mock_resp.text = "ok"

    with patch("httpx.post", return_value=mock_resp):
        results = notifier.dispatch(_make_event())
    assert len(results) == 1
    assert results[0].success


def test_notifier_notify_dedup() -> None:
    notifier = Notifier()
    fmt = WebhookFormatter(webhook_url="https://example.com/webhook")
    notifier.register("webhook", fmt)

    mock_resp = MagicMock()
    mock_resp.is_success = True
    mock_resp.status_code = 200
    mock_resp.text = "ok"

    event = _make_event()
    with patch("httpx.post", return_value=mock_resp):
        results1 = notifier.dispatch(event)
        results2 = notifier.dispatch(event)
    assert len(results1) == 1
    assert results2 == []  # dedup


def test_notifier_notify_retry() -> None:
    notifier = Notifier()
    fmt = WebhookFormatter(webhook_url="https://example.com/webhook")
    notifier.register("webhook", fmt)

    mock_fail = MagicMock()
    mock_fail.is_success = False
    mock_fail.status_code = 500
    mock_fail.text = "error"

    mock_ok = MagicMock()
    mock_ok.is_success = True
    mock_ok.status_code = 200
    mock_ok.text = "ok"

    with patch("httpx.post", side_effect=[mock_fail, mock_ok]):
        with patch("time.sleep"):
            results = notifier.dispatch(_make_event())
    assert len(results) >= 1
    assert any(r.success for r in results)


def test_notifier_notify_exception_retry() -> None:
    notifier = Notifier()
    fmt = WebhookFormatter(webhook_url="https://example.com/webhook")
    notifier.register("webhook", fmt)

    with patch("httpx.post", side_effect=Exception("fail")):
        with patch("time.sleep"):
            results = notifier.dispatch(_make_event())
    assert len(results) >= 1
    assert all(not r.success for r in results)


def test_slack_verify_signature_no_secret() -> None:
    fmt = SlackFormatter(webhook_url="https://hooks.slack.com/test", signing_secret="")
    assert fmt.verify_signature("123", "body", "sig") is False


def test_slack_verify_signature_expired() -> None:
    fmt = SlackFormatter(webhook_url="https://hooks.slack.com/test", signing_secret="test-secret")  # noqa: S106
    old_ts = str(0)
    assert fmt.verify_signature(old_ts, "body", "sig") is False
