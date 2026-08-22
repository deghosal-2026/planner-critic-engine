from __future__ import annotations

import pytest

from planner_critic.redaction import RedactMode, SecretsRedactor


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