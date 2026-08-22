from __future__ import annotations

import pytest

from planner_critic.store.base import InMemoryStore


class TestPlanSignaturePersistence:
    def test_put_and_get_signature(self) -> None:
        store = InMemoryStore()
        store.put_plan_signature("plan-1", 1, "sig-a")
        sigs = store.get_plan_signatures("plan-1")
        assert len(sigs) == 1
        assert sigs[0] == (1, "sig-a")

    def test_multiple_versions(self) -> None:
        store = InMemoryStore()
        store.put_plan_signature("plan-1", 1, "sig-a")
        store.put_plan_signature("plan-1", 2, "sig-b")
        store.put_plan_signature("plan-1", 3, "sig-c")
        sigs = store.get_plan_signatures("plan-1")
        assert len(sigs) == 3
        assert sigs[0][0] == 3
        assert sigs[1][0] == 2
        assert sigs[2][0] == 1

    def test_different_plan_isolation(self) -> None:
        store = InMemoryStore()
        store.put_plan_signature("plan-1", 1, "sig-a")
        store.put_plan_signature("plan-2", 1, "sig-b")
        sigs_1 = store.get_plan_signatures("plan-1")
        sigs_2 = store.get_plan_signatures("plan-2")
        assert len(sigs_1) == 1
        assert len(sigs_2) == 1

    def test_replace_existing(self) -> None:
        store = InMemoryStore()
        store.put_plan_signature("plan-1", 1, "sig-a")
        store.put_plan_signature("plan-1", 1, "sig-b")
        sigs = store.get_plan_signatures("plan-1")
        assert len(sigs) == 1
        assert sigs[0][1] == "sig-b"

    def test_empty_plan(self) -> None:
        store = InMemoryStore()
        sigs = store.get_plan_signatures("nonexistent")
        assert len(sigs) == 0


class TestSQLitePlanSignature:
    def test_round_trip(self) -> None:
        from planner_critic.store.sqlite import SQLiteStore

        store = SQLiteStore(":memory:")
        store.put_plan_signature("plan-1", 1, "sig-a")
        store.put_plan_signature("plan-1", 2, "sig-b")
        sigs = store.get_plan_signatures("plan-1")
        assert len(sigs) == 2
        assert sigs[0] == (2, "sig-b")
        assert sigs[1] == (1, "sig-a")
        store.close()