from __future__ import annotations

from pathlib import Path

import pytest

from planner_critic.notifier import EscalationEvent, Notifier, SlackFormatter, TeamsFormatter, WebhookFormatter


class TestM8ConfigSurfaces:
    def test_action_yml_exists(self) -> None:
        path = Path(__file__).resolve().parent.parent / "action.yml"
        assert path.exists()
        content = path.read_text()
        assert "plancritic check" in content
        assert "shadow" in content

    def test_gitlab_template_exists(self) -> None:
        path = Path(__file__).resolve().parent.parent / ".gitlab-ci.yml-planner-critic.yml"
        assert path.exists()
        content = path.read_text()
        assert "plancritic check" in content
        assert "allow_failure" in content

    def test_d26_design_doc_exists(self) -> None:
        path = Path(__file__).resolve().parent.parent / "docs" / "design" / "integration-surfaces-design.md"
        assert path.exists()


class TestSlackEscalation:
    def test_event_build_with_all_fields(self) -> None:
        event = EscalationEvent(
            escalation_id="e1", plan_id="p1", reason_code="unsafe_ordering",
            question="Reordering needed?", severity="warning", environment="staging",
            service="payments", summary="Deploy schema change", backstage_url="https://x",
        )
        formatter = SlackFormatter("https://hooks.slack.com/x")
        payload = formatter.format_event(event)
        assert "e1" in str(payload)
        assert "unsafe_ordering" in str(payload)

    def test_notifier_dedup(self) -> None:
        notifier = Notifier()
        event = EscalationEvent(escalation_id="e2", plan_id="p2", reason_code="r", question="q")
        notifier.dispatch(event)
        # Second dispatch is deduped
        assert notifier.dispatch(event) == []