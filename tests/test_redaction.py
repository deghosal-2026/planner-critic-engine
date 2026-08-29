from __future__ import annotations

import pytest

from planner_critic.redaction import IntegrityFailure, RedactMode, SecretsRedactor, verify_transit_integrity


class TestSecretsRedactor:
    def test_redact_aws_key(self) -> None:
        redactor = SecretsRedactor()
        text = "My AWS key is AKIAIOSFODNN7EXAMPLE"
        result = redactor.redact(text)
        assert "[REDACTED_SECRET]" in result
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert len(redactor.audits()) == 1
        assert redactor.audits()[0].pattern == "aws_key"

    def test_redact_email(self) -> None:
        redactor = SecretsRedactor()
        text = "Contact user@example.com for access"
        result = redactor.redact(text)
        assert "[REDACTED_PII]" in result
        assert "user@example.com" not in result

    def test_redact_phone(self) -> None:
        redactor = SecretsRedactor()
        text = "Call 555-123-4567 for support"
        result = redactor.redact(text)
        assert "[REDACTED_PII]" in result
        assert "555-123-4567" not in result

    def test_redact_ssn(self) -> None:
        redactor = SecretsRedactor()
        text = "SSN: 123-45-6789"
        result = redactor.redact(text)
        assert "[REDACTED_PII]" in result
        assert "123-45-6789" not in result

    def test_redact_jwt(self) -> None:
        redactor = SecretsRedactor()
        text = "token=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3j_V-NM7mCw"
        result = redactor.redact(text)
        assert "[REDACTED_SECRET]" in result
        assert "eyJhbGciOiJIUzI1NiJ9" not in result

    def test_skip_mode_no_redaction(self) -> None:
        redactor = SecretsRedactor(mode=RedactMode.SKIP)
        text = "My key is AKIAIOSFODNN7EXAMPLE"
        result = redactor.redact(text)
        assert result == text
        assert len(redactor.audits()) == 0

    def test_hash_mode(self) -> None:
        redactor = SecretsRedactor(mode=RedactMode.HASH)
        text = "secret is AKIAIOSFODNN7EXAMPLE"
        result = redactor.redact(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert not result.startswith("[REDACTED")

    def test_custom_pattern(self) -> None:
        redactor = SecretsRedactor()
        redactor.add_custom_pattern("acme_key", r"acme_[A-Za-z0-9]{32}")
        text = "My key is acme_abcdefghijklmnopqrstuvwxyz123456"
        result = redactor.redact(text)
        assert "[REDACTED_SECRET]" in result
        assert "acme_abcdefghijklmnopqrstuvwxyz123456" not in result

    def test_no_secrets_no_change(self) -> None:
        redactor = SecretsRedactor()
        text = "Hello, this is a safe message with no secrets"
        result = redactor.redact(text)
        assert result == text
        assert len(redactor.audits()) == 0

    def test_redact_api_key(self) -> None:
        redactor = SecretsRedactor()
        text = "API_KEY=abcdefghijklmnopqrst"
        result = redactor.redact(text)
        assert "[REDACTED_SECRET]" in result
        assert "abcdefghijklmnopqrst" not in result

    def test_redact_private_key_header(self) -> None:
        redactor = SecretsRedactor()
        text = "-----BEGIN RSA PRIVATE KEY-----\nbase64data\n-----END RSA PRIVATE KEY-----"
        result = redactor.redact(text)
        assert "[REDACTED_SECRET]" in result
        assert "BEGIN RSA PRIVATE KEY" not in result

    def test_reason_code_property(self) -> None:
        redactor = SecretsRedactor()
        assert redactor.reason_code == "secret_redacted"

    def test_redact_nested_dict(self) -> None:
        redactor = SecretsRedactor()
        data = {
            "goal": "deploy to prod",
            "credentials": {"aws_key": "AKIAIOSFODNN7EXAMPLE"},
        }
        result = redactor.redact_dict(data)
        assert "[REDACTED_SECRET]" in result["credentials"]["aws_key"]
        assert result["goal"] == "deploy to prod"

    def test_redact_list_of_dicts(self) -> None:
        redactor = SecretsRedactor()
        data = {"tasks": [{"name": "auth", "key": "AKIAIOSFODNN7EXAMPLE"}]}
        result = redactor.redact_dict(data)
        assert "[REDACTED_SECRET]" in result["tasks"][0]["key"]


class TestTransitIntegrity:
    """Transit-integrity check for redaction layer (#296, F-20)."""

    def test_numeric_fields_survive_redaction(self) -> None:
        """Numeric fields must remain unchanged after redact_dict."""
        redactor = SecretsRedactor()
        data = {
            "label_flip_rate": 0.033,
            "count": 42,
            "ratio": 0.5,
            "name": "safe text",
        }
        redacted = redactor.redact_dict(data)
        violations = verify_transit_integrity(data, redacted)
        assert len(violations) == 0

    def test_boolean_fields_survive_redaction(self) -> None:
        """Boolean fields must remain unchanged."""
        redactor = SecretsRedactor()
        data = {"active": True, "verified": False, "name": "test"}
        redacted = redactor.redact_dict(data)
        violations = verify_transit_integrity(data, redacted)
        assert len(violations) == 0

    def test_nested_numeric_fields_survive(self) -> None:
        """Nested dicts with numeric fields must survive."""
        redactor = SecretsRedactor()
        data = {"results": {"score": 0.95, "count": 100, "label": "safe"}}
        redacted = redactor.redact_dict(data)
        violations = verify_transit_integrity(data, redacted)
        assert len(violations) == 0

    def test_detects_numeric_corruption(self) -> None:
        """Transit-integrity check catches numeric corruption."""
        original = {"score": 0.033}
        redacted_bad = {"score": 0.0}
        with pytest.raises(IntegrityFailure) as exc:
            verify_transit_integrity(original, redacted_bad)
        assert "0.033" in str(exc.value)

    def test_strict_mode_detects_string_change_without_placeholder(self) -> None:
        """Strict mode flags string changes that don't contain a placeholder."""
        original = {"name": "hello world"}
        redacted = {"name": "goodbye world"}
        with pytest.raises(IntegrityFailure) as exc:
            verify_transit_integrity(original, redacted, strict=True)
        assert "name" in str(exc.value)

    def test_strict_mode_allows_redacted_placeholder(self) -> None:
        """Strict mode allows string changes that contain redaction placeholders."""
        original = {"secret": "my key is AKIAIOSFODNN7EXAMPLE"}
        redactor = SecretsRedactor()
        redacted = redactor.redact_dict(original)
        violations = verify_transit_integrity(original, redacted, strict=True)
        assert len(violations) == 0

    def test_detects_missing_key(self) -> None:
        """Transit-integrity check catches missing keys."""
        original = {"score": 0.5, "name": "test"}
        redacted = {"score": 0.5}
        with pytest.raises(IntegrityFailure) as exc:
            verify_transit_integrity(original, redacted)
        assert "name" in str(exc.value)

    def test_redact_dict_preserves_int_type(self) -> None:
        """redact_dict preserves int types (does not convert to float)."""
        redactor = SecretsRedactor()
        data = {"count": 0, "items": 42}
        redacted = redactor.redact_dict(data)
        assert isinstance(redacted["count"], int)
        assert isinstance(redacted["items"], int)

    def test_redact_dict_preserves_bool_type(self) -> None:
        """redact_dict preserves bool types (does not convert to int)."""
        redactor = SecretsRedactor()
        data = {"is_active": True, "is_deleted": False}
        redacted = redactor.redact_dict(data)
        assert redacted["is_active"] is True
        assert redacted["is_deleted"] is False
