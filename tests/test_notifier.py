from __future__ import annotations

import pytest

from planner_critic.notifier import (
    EscalationEvent,
    Notifier,
    SlackFormatter,
    TeamsFormatter,
    WebhookFormatter,
)


class TestSlackFormatter:
    def test_format_event_has_blocks(self) -> None:
        event = EscalationEvent(
            escalation_id="esc-1", plan_id="plan-1",
            reason_code="missing_rollback", question="Rollback required?",
            severity="blocker", environment="prod", service="api",
            summary="Deploy migration",
        )
        formatter = SlackFormatter("https://hooks.slack.com/test")
        payload = formatter.format_event(event)
        assert "blocks" in payload
        assert len(payload["blocks"]) >= 4

    def test_format_event_no_backstage(self) -> None:
        event = EscalationEvent(
            escalation_id="esc-1", plan_id="plan-1",
            reason_code="missing_rollback", question="Approve?",
        )
        formatter = SlackFormatter("https://hooks.slack.com/test")
        payload = formatter.format_event(event)
        blocks_text = str(payload)
        assert "Review in Backstage" not in blocks_text

    def test_format_event_with_backstage(self) -> None:
        event = EscalationEvent(
            escalation_id="esc-1", plan_id="plan-1",
            reason_code="missing_rollback", question="Approve?",
            backstage_url="https://backstage.example.com",
        )
        formatter = SlackFormatter("https://hooks.slack.com/test")
        payload = formatter.format_event(event)
        blocks_text = str(payload)
        assert "Review in Backstage" in blocks_text

    def test_verify_signature_valid(self) -> None:
        import hmac, hashlib, time
        formatter = SlackFormatter("https://hooks.slack.com/test", signing_secret="secret123")
        ts = str(int(time.time()))
        body = '{"test": true}'
        sig_basestring = f"v0:{ts}:{body}"
        sig = "v0=" + hmac.new(b"secret123", sig_basestring.encode(), hashlib.sha256).hexdigest()
        assert formatter.verify_signature(ts, body, sig)

    def test_verify_signature_expired(self) -> None:
        formatter = SlackFormatter("https://hooks.slack.com/test", signing_secret="secret123")
        ts = "0"
        assert not formatter.verify_signature(ts, "body", "v0=xxxx")


class TestTeamsFormatter:
    def test_format_event_has_adaptive_card(self) -> None:
        event = EscalationEvent(
            escalation_id="esc-1", plan_id="plan-1",
            reason_code="missing_rollback", question="Approve?",
        )
        formatter = TeamsFormatter("https://outlook.office.com/test")
        payload = formatter.format_event(event)
        assert "attachments" in payload
        content = payload["attachments"][0]["content"]
        assert content["type"] == "AdaptiveCard"
        assert "actions" in content


class TestWebhookFormatter:
    def test_format_event(self) -> None:
        event = EscalationEvent(
            escalation_id="esc-1", plan_id="plan-1",
            reason_code="missing_rollback", question="Approve?",
        )
        formatter = WebhookFormatter("https://hooks.example.com")
        payload = formatter.format_event(event)
        assert payload["event"] == "escalation"
        assert payload["escalation_id"] == "esc-1"


class TestNotifier:
    def test_register_and_dispatch(self) -> None:
        class _MockFormatter:
            def __init__(self) -> None:
                self.called = False

            def format_event(self, event: EscalationEvent) -> dict:
                self.called = True
                return {"event": event.escalation_id}

            def deliver(self, payload: dict) -> object:
                from planner_critic.notifier import NotificationResult
                return NotificationResult(surface="mock", success=True, status_code=200)

        mock = _MockFormatter()
        notifier = Notifier()
        notifier.register("mock", mock)  # type: ignore[arg-type]

        event = EscalationEvent(escalation_id="esc-1", plan_id="plan-1", reason_code="test", question="?")
        results = notifier.dispatch(event)
        assert len(results) == 1
        assert results[0].success

    def test_dedup_prevents_duplicate(self) -> None:
        notifier = Notifier()
        event = EscalationEvent(escalation_id="esc-1", plan_id="plan-1", reason_code="test", question="?")
        results1 = notifier.dispatch(event)
        results2 = notifier.dispatch(event)
        assert len(results1) == 0  # no surfaces registered
        assert len(results2) == 0  # dedup hit

    def test_no_surfaces(self) -> None:
        notifier = Notifier()
        event = EscalationEvent(escalation_id="esc-1", plan_id="plan-1", reason_code="test", question="?")
        results = notifier.dispatch(event)
        assert len(results) == 0