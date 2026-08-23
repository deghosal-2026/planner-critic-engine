from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Pattern

from planner_critic.reason_codes import SECRET_REDACTED

logger = logging.getLogger(__name__)


class RedactMode(StrEnum):
    REDACT = "redact"
    HASH = "hash"
    SKIP = "skip"


BUILTIN_PATTERNS: dict[str, Pattern[str]] = {
    "aws_key": re.compile(r"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    "api_key": re.compile(r"[A-Za-z0-9]{16,}"),
    "oauth_token": re.compile(r"(?:Bearer|bearer)\s+[A-Za-z0-9\-._~+/]+=*"),
    "jwt": re.compile(r"eyJ[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_.+/=]+"),
    "private_key": re.compile(r"-----BEGIN\s+[A-Z\s]+\s+KEY-----|-----END\s+[A-Z\s]+\s+KEY-----"),
    "slack_token": re.compile(r"xox[baprs]-[A-Za-z0-9\-]+"),
    "github_pat": re.compile(r"ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{84,}"),
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}

PLACEHOLDER_REDACT = "[REDACTED_SECRET]"
PLACEHOLDER_PII = "[REDACTED_PII]"


@dataclass
class RedactionAudit:
    pattern: str
    count: int
    locations: list[str]

    def to_log(self) -> dict[str, Any]:
        return {"pattern": self.pattern, "count": self.count, "locations": self.locations}


class SecretsRedactor:
    def __init__(self, mode: RedactMode = RedactMode.REDACT) -> None:
        self._mode = mode
        self._patterns: dict[str, Pattern[str]] = dict(BUILTIN_PATTERNS)
        self._audits: list[RedactionAudit] = []

    def add_custom_pattern(self, name: str, pattern: str) -> None:
        self._patterns[name] = re.compile(pattern)

    def set_mode(self, mode: RedactMode) -> None:
        self._mode = mode

    def redact(self, text: str, surface: str = "") -> str:
        if self._mode is RedactMode.SKIP:
            return text
        result = text
        for name, pattern in self._patterns.items():
            matches = list(pattern.finditer(result))
            if not matches:
                continue
            placeholder = PLACEHOLDER_PII if name in ("email", "phone", "ssn") else PLACEHOLDER_REDACT
            self._audits.append(
                RedactionAudit(
                    pattern=name,
                    count=len(matches),
                    locations=[surface] if surface else [],
                )
            )
            for m in reversed(matches):
                if self._mode is RedactMode.HASH:
                    secret_hash = hashlib.sha256(m.group().encode()).hexdigest()[:16]
                    result = result[:m.start()] + secret_hash + result[m.end():]
                else:
                    result = result[:m.start()] + placeholder + result[m.end():]
        return result

    def audits(self) -> list[RedactionAudit]:
        return list(self._audits)

    @property
    def reason_code(self) -> str:
        return SECRET_REDACTED

    def redact_dict(self, data: dict[str, Any], surface: str = "") -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.redact(value, surface=f"{surface}.{key}" if surface else key)
            elif isinstance(value, dict):
                result[key] = self.redact_dict(value, surface=f"{surface}.{key}" if surface else key)
            elif isinstance(value, list):
                result[key] = [
                    self.redact_dict(v, surface=f"{surface}.{key}[i]") if isinstance(v, dict)
                    else self.redact(str(v), surface=f"{surface}.{key}[i]") if isinstance(v, str)
                    else v
                    for i, v in enumerate(value)
                ]
            else:
                result[key] = value
        return result
