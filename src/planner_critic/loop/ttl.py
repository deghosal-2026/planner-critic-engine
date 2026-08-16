"""Approval expiry / stale-plan handling (F-18 — M1 deterministic TTL check).

An approved plan carries an ``approval_ttl`` on the goal. If the approval is
older than the TTL, the plan is stale and must be replanned before use. M1
ships the expiry predicate; the re-gate (M4) consumes it.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def approval_expired(
    approved_at: datetime,
    approval_ttl: timedelta | None,
    now: datetime | None = None,
) -> bool:
    """True when an approval has outlived its TTL.

    Args:
        approved_at: When the plan was approved.
        approval_ttl: Time-to-live; None means the approval never expires.
        now: Reference clock (injectable for tests; defaults to UTC now).

    Returns:
        True when ``approval_ttl`` is set and ``now - approved_at`` exceeds it.
    """
    if approval_ttl is None:
        return False
    reference = now if now is not None else datetime.now(UTC)
    return (reference - approved_at) > approval_ttl
