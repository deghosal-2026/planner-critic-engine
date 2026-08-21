"""Tests for the shared audit trail (_audit.py)."""

from planner_critic.adapters._audit import AuditEvent, AuditTrail


class TestAuditEvent:
    def test_create_minimal(self):
        event = AuditEvent("raw", "plan_requested")
        assert event.adapter == "raw"
        assert event.event == "plan_requested"
        assert event.plan_id is None
        assert event.details == {}

    def test_create_full(self):
        event = AuditEvent("langgraph", "re_gate_check", plan_id="plan-1", details={"found": True})
        assert event.plan_id == "plan-1"
        assert event.details == {"found": True}


class TestAuditTrail:
    def test_empty_trail(self):
        trail = AuditTrail()
        assert trail.get_events() == []
        assert trail.last_event() is None

    def test_record_and_get(self):
        trail = AuditTrail()
        trail.record(AuditEvent("raw", "plan_requested"))
        trail.record(AuditEvent("raw", "plan_approved", plan_id="plan-1"))
        events = trail.get_events()
        assert len(events) == 2
        assert events[0].event == "plan_requested"
        assert events[1].event == "plan_approved"

    def test_last_event(self):
        trail = AuditTrail()
        trail.record(AuditEvent("raw", "plan_requested"))
        assert trail.last_event().event == "plan_requested"
        trail.record(AuditEvent("raw", "plan_approved", plan_id="plan-1"))
        assert trail.last_event().event == "plan_approved"

    def test_get_events_returns_copy(self):
        trail = AuditTrail()
        trail.record(AuditEvent("raw", "plan_requested"))
        events = trail.get_events()
        events.append(AuditEvent("raw", "injected"))
        assert len(trail.get_events()) == 1
