from __future__ import annotations

from datetime import UTC, datetime

from planner_critic.state import (
    LockStrategy,
    ResourceLock,
    StateLock,
    StateSnapshot,
    StateView,
)


class TestStateView:
    def test_read_from_snapshot(self) -> None:
        snapshot = StateSnapshot(
            version="v1",
            captured_at=datetime.now(UTC),
            snapshot={"db_healthy": True, "auth_configured": False},
        )
        view = StateView(snapshot)
        assert view.read("db_healthy") is True
        assert view.read("auth_configured") is False
        assert view.read("nonexistent") is None

    def test_version_access(self) -> None:
        snapshot = StateSnapshot(version="v2", captured_at=datetime.now(UTC), snapshot={})
        view = StateView(snapshot)
        assert view.version == "v2"

    def test_is_stale_version_mismatch(self) -> None:
        old = StateSnapshot(version="v1", captured_at=datetime.now(UTC), snapshot={})
        current = StateSnapshot(version="v2", captured_at=datetime.now(UTC), snapshot={})
        view = StateView(old)
        assert view.is_stale(current)

    def test_is_stale_timestamp_mismatch(self) -> None:
        old = StateSnapshot(version="v1", captured_at=datetime(2024, 1, 1, tzinfo=UTC), snapshot={})
        current = StateSnapshot(
            version="v1", captured_at=datetime(2024, 6, 1, tzinfo=UTC), snapshot={}
        )
        view = StateView(old)
        assert view.is_stale(current)

    def test_not_stale_when_same(self) -> None:
        ts = datetime.now(UTC)
        snapshot = StateSnapshot(version="v1", captured_at=ts, snapshot={})
        view = StateView(snapshot)
        assert not view.is_stale(snapshot)

    def test_reason_code(self) -> None:
        snapshot = StateSnapshot(version="v1", captured_at=datetime.now(UTC), snapshot={})
        view = StateView(snapshot)
        assert view.reason_code == "state_view_stale"


class TestStateLock:
    def test_acquire_new_resource(self) -> None:
        lock = StateLock()
        result = lock.acquire("aws:sg-123", "plan-1")
        assert result is None
        assert lock.is_locked("aws:sg-123")

    def test_double_acquire_fail_fast(self) -> None:
        lock = StateLock(strategy=LockStrategy.FAIL_FAST)
        lock.acquire("aws:sg-123", "plan-1")
        result = lock.acquire("aws:sg-123", "plan-2")
        assert result == "concurrent_resource_conflict"

    def test_double_acquire_escalate(self) -> None:
        lock = StateLock(strategy=LockStrategy.ESCALATE)
        lock.acquire("aws:sg-123", "plan-1")
        result = lock.acquire("aws:sg-123", "plan-2")
        assert result == "resource_locked_by_concurrent_execution"

    def test_release_and_reacquire(self) -> None:
        lock = StateLock()
        lock.acquire("aws:sg-123", "plan-1")
        lock.release("aws:sg-123")
        assert not lock.is_locked("aws:sg-123")
        result = lock.acquire("aws:sg-123", "plan-2")
        assert result is None

    def test_different_resources_no_conflict(self) -> None:
        lock = StateLock()
        r1 = lock.acquire("aws:sg-123", "plan-1")
        r2 = lock.acquire("k8s:deploy-api", "plan-2")
        assert r1 is None
        assert r2 is None

    def test_active_locks(self) -> None:
        lock = StateLock()
        lock.acquire("res-1", "plan-1")
        lock.acquire("res-2", "plan-2")
        assert len(lock.active_locks()) == 2

    def test_expired_lock_not_active(self) -> None:
        lock_ts = ResourceLock(resource_uri="res-1", plan_id="plan-1", lock_timeout=-1)
        inner = StateLock()
        inner._locks["res-1"] = lock_ts
        assert len(inner.active_locks()) == 0

    def test_pre_execution_conflict_none(self) -> None:
        lock = StateLock()
        conflicts = lock.pre_execution_conflict(["res-1", "res-2"])
        assert len(conflicts) == 0

    def test_pre_execution_conflict_detected(self) -> None:
        lock = StateLock()
        lock.acquire("res-1", "plan-1")
        conflicts = lock.pre_execution_conflict(["res-1", "res-2"])
        assert len(conflicts) == 1
        assert conflicts[0][0] == "res-1"
        assert conflicts[0][1] == "concurrent_resource_conflict"

    def test_lock_strategy_wait(self) -> None:
        lock = StateLock(strategy=LockStrategy.WAIT, wait_deadline=0.1)
        lock.acquire("res-1", "plan-1")
        result = lock.acquire("res-1", "plan-2")
        assert result == "resource_locked_by_concurrent_execution"
