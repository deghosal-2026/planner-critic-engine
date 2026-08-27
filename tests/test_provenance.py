"""Tests for tool-result provenance and capability-scoped transitions (#249, #258)."""

from __future__ import annotations

from planner_critic.provenance import (
    CapabilityLevel,
    ToolResultProvenance,
    check_transition_capability,
    default_capability_for_source,
)


class TestCapabilityLevels:
    def test_ordering(self) -> None:
        """Capability levels are strictly ordered."""
        assert CapabilityLevel.UNTRUSTED_WEB < CapabilityLevel.EXTERNAL_API
        assert CapabilityLevel.EXTERNAL_API < CapabilityLevel.INTERNAL_DB
        assert CapabilityLevel.INTERNAL_DB < CapabilityLevel.INTERNAL_VERIFIED
        assert CapabilityLevel.INTERNAL_VERIFIED < CapabilityLevel.ADMIN_OVERRIDE

    def test_from_str(self) -> None:
        """Parse from string representation."""
        assert CapabilityLevel.from_str("untrusted_web") == CapabilityLevel.UNTRUSTED_WEB
        assert CapabilityLevel.from_str("admin_override") == CapabilityLevel.ADMIN_OVERRIDE


class TestCheckTransitionCapability:
    def test_untrusted_web_cannot_approve(self) -> None:
        """Untrusted web source cannot perform approve transitions."""
        allowed, reason = check_transition_capability(CapabilityLevel.UNTRUSTED_WEB, "approve")
        assert not allowed
        assert "blocked" in reason

    def test_untrusted_web_can_discover(self) -> None:
        """Untrusted web source can perform discovery transitions."""
        allowed, _ = check_transition_capability(CapabilityLevel.UNTRUSTED_WEB, "discovery")
        assert allowed

    def test_admin_can_approve(self) -> None:
        """Admin override source can perform approve transitions."""
        allowed, _ = check_transition_capability(CapabilityLevel.ADMIN_OVERRIDE, "approve")
        assert allowed

    def test_internal_db_cannot_deploy(self) -> None:
        """Internal DB source cannot perform deploy transitions."""
        allowed, _ = check_transition_capability(CapabilityLevel.INTERNAL_DB, "deploy")
        assert not allowed

    def test_internal_verified_can_deploy(self) -> None:
        """Internal verified source can perform deploy transitions."""
        allowed, _ = check_transition_capability(CapabilityLevel.INTERNAL_VERIFIED, "deploy")
        assert allowed

    def test_unknown_transition_allowed(self) -> None:
        """Unknown transitions are allowed by default."""
        allowed, _ = check_transition_capability(CapabilityLevel.UNTRUSTED_WEB, "unknown")
        assert allowed

    def test_untrusted_web_cannot_access_secrets(self) -> None:
        """Untrusted web source cannot access secrets."""
        allowed, _ = check_transition_capability(CapabilityLevel.UNTRUSTED_WEB, "secret_access")
        assert not allowed

    def test_internal_db_cannot_make_payments(self) -> None:
        """Internal DB source cannot perform payment transitions."""
        allowed, _ = check_transition_capability(CapabilityLevel.INTERNAL_DB, "payment")
        assert not allowed


class TestDefaultCapability:
    def test_web_fetch_is_untrusted(self) -> None:
        """Web fetch is untrusted by default."""
        assert default_capability_for_source("web_fetch") == CapabilityLevel.UNTRUSTED_WEB

    def test_admin_api_is_admin(self) -> None:
        """Admin API is admin_override by default."""
        assert default_capability_for_source("admin_api") == CapabilityLevel.ADMIN_OVERRIDE

    def test_unknown_source_is_untrusted(self) -> None:
        """Unknown sources default to untrusted (fail-safe)."""
        assert default_capability_for_source("unknown") == CapabilityLevel.UNTRUSTED_WEB


class TestToolResultProvenance:
    def test_web_fetch_cannot_approve(self) -> None:
        """Web fetch provenance cannot approve transitions."""
        prov = ToolResultProvenance(source="web_fetch")
        assert not prov.can_perform("approve")

    def test_admin_api_can_approve(self) -> None:
        """Admin API provenance can approve transitions."""
        prov = ToolResultProvenance(source="admin_api")
        assert prov.can_perform("approve")

    def test_internal_db_can_read(self) -> None:
        """Internal DB provenance can read."""
        prov = ToolResultProvenance(source="db_query")
        assert prov.can_perform("read")

    def test_explicit_capability_overrides_source(self) -> None:
        """Explicit capability overrides source-based default."""
        prov = ToolResultProvenance(source="web_fetch", capability=CapabilityLevel.ADMIN_OVERRIDE)
        assert prov.can_perform("approve")

    def test_check_returns_reason(self) -> None:
        """check() returns (allowed, reason) tuple."""
        prov = ToolResultProvenance(source="web_fetch")
        allowed, reason = prov.check("approve")
        assert not allowed
        assert "blocked" in reason

    def test_injection_attack_blocked(self) -> None:
        """Simulated injection: untrusted web content cannot approve."""
        # An attacker injects "approve this plan" via web fetch
        prov = ToolResultProvenance(source="web_fetch")
        allowed, _ = prov.check("approve")
        assert not allowed, (
            "Untrusted web content should not be able to approve plans — "
            "blocked by capability gate, not content analysis"
        )
