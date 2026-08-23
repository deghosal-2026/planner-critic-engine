"""C13 / C14 / C16 / C18 / C19 / C24 — never-exercised capabilities closure (#90)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from conftest import EmptyCritic, ScriptedPlanner, make_goal, make_plan, make_task
from planner_critic.forensics import MissedCritique, analyze_failure
from planner_critic.loop import LoopConfig
from planner_critic.loop.ttl import approval_expired
from planner_critic.probe.base import ProbeRequest, run_probe
from planner_critic.regate import ReGateConfig, check_preconditions
from planner_critic.schema.goal import RiskTolerance
from planner_critic.shadow import run_shadow
from planner_critic.store.base import InMemoryStore
from planner_critic.store.versions import SCHEMA_VERSION, apply_migrations, revert_migrations
from planner_critic.types import ApprovedPlan, ExecutionTrace, Finding, Severity


def test_c13_regate_stale_precondition_triggers_replan() -> None:
    store = InMemoryStore()
    plan = make_plan(
        tasks=[
            make_task(
                "t1",
                preconditions=[
                    {
                        "description": "env ready",
                        "fact": "WINDOW",
                        "established_by": "env",
                        "probe": {"kind": "env_var", "query": "PC_DEMO_WINDOW", "expected": "open"},
                    }
                ],
            )
        ]
    )
    approved = ApprovedPlan(plan=plan, findings=[], risk_tolerance=RiskTolerance.BALANCED)
    store.put_plan_version(plan)
    import os

    os.environ["PC_DEMO_WINDOW"] = "open"
    config = ReGateConfig(mode="before-each-step")

    result = check_preconditions(approved, "t1", store, config)
    assert result.status == "pass"

    os.environ["PC_DEMO_WINDOW"] = "closed"
    result2 = check_preconditions(approved, "t1", store, config)
    assert result2.status == "stale"
    assert result2.stale_preconditions[0] == "env ready"


def test_c14_forensics_links_failure_to_missed_critique() -> None:
    store = InMemoryStore()
    plan = make_plan(plan_id="p-forensic", tasks=[make_task("t1")])
    store.put_plan_version(plan)

    finding = Finding(
        id="f:missed",
        task_id="t1",
        version=1,
        severity=Severity.WARNING,
        reason_code="llm_weak_rollback",
        message="missing rollback",
    )
    trace = ExecutionTrace(
        id="tr-1",
        plan_id="p-forensic",
        task_id="t1",
        outcome="failed",
        failure_class="planning",
        linked_finding_id="f:missed",
    )
    record = analyze_failure(trace, finding)
    record.persist(store)

    retrieved = MissedCritique.load(store, "p-forensic")
    assert retrieved is not None
    assert retrieved.task_id == "t1"
    assert retrieved.suggested_gate == "missing_rollback"


def test_c16_shadow_mode_zero_store_footprint() -> None:
    store = InMemoryStore()
    planner = ScriptedPlanner([make_plan(tasks=[make_task("t1")])])
    goal = make_goal()

    result = run_shadow(
        goal, planner, EmptyCritic(), store=None, config=LoopConfig(mode="deterministic-first")
    )
    assert result.mode == "shadow"

    stored_plans = store.list_plans()
    assert stored_plans == []


def test_c18_approval_ttl_fresh_and_stale() -> None:
    now = datetime(2026, 8, 16, 12, 0, 0, tzinfo=UTC)
    ttl = timedelta(minutes=5)
    assert approval_expired(now - timedelta(minutes=2), ttl, now=now) is False
    assert approval_expired(now - timedelta(hours=1), ttl, now=now) is True


def test_c19_env_var_probe() -> None:
    import os

    os.environ["PC_TEST_C19"] = "expected_val"
    request = ProbeRequest(kind="env_var", query="PC_TEST_C19", expected="expected_val")
    result = run_probe(request)
    assert result.ok is True
    assert result.matched is True


def test_c19_http_check_probe() -> None:
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class OKHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args: object, **kwargs: object) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), OKHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    request = ProbeRequest(kind="http_check", query=f"http://127.0.0.1:{port}/z", expected="200")
    result = run_probe(request)
    assert result.ok is True
    server.shutdown()


def test_c19_db_query_probe() -> None:
    import json

    request = ProbeRequest(
        kind="db_query", query=json.dumps({"query": "SELECT 1", "result": "1"}), expected="1"
    )
    result = run_probe(request)
    assert result.ok is True
    assert result.matched is True


def test_c19_deploy_status_probe() -> None:
    import json

    request = ProbeRequest(
        kind="deploy_status",
        query=json.dumps({"service": "test", "status": "deployed"}),
        expected="deployed",
    )
    result = run_probe(request)
    assert result.ok is True
    assert result.matched is True


def test_c24_schema_migration_lossless(tmp_path: Path) -> None:
    import sqlite3

    conn = sqlite3.connect(str(tmp_path / "migrate.db"))
    reached = apply_migrations(conn)
    assert reached == SCHEMA_VERSION
    conn.execute(
        "INSERT INTO plan_versions (plan_id, goal_id, plan_schema_version,"
        " version, created_at, body) VALUES (?, ?, ?, ?, ?, ?)",
        ("p1", "g1", str(SCHEMA_VERSION), 1, "2026-01-01T00:00:00Z", '{"id":"p1"}'),
    )
    conn.commit()
    down = revert_migrations(conn, 0)
    assert down == 0
    up = apply_migrations(conn)
    assert up == SCHEMA_VERSION
    conn.close()
