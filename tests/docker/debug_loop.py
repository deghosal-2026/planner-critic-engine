#!/usr/bin/env python3
"""Standalone debug script — send a goal to the containerized engine, print and
save the full LLM interaction.

Usage:
    # Adversarial goal (critical-risk, should escalate)
    python3 tests/docker/debug_loop.py adversarial

    # Normal goal (should approve or escalate cleanly)
    python3 tests/docker/debug_loop.py normal

    # Custom goal file
    python3 tests/docker/debug_loop.py path/to/goal.json

Output:
    - Pretty-prints the full response (status, plan, findings, reason_code, escalation)
    - Saves to docs/test/docker/<timestamp>_debug_<label>.json
    - Prints docker compose logs tail for LLM transport logging
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

BASE = "http://localhost:8080"
DX = Path(__file__).parent / "fixtures"
LOG_DIR = Path(__file__).resolve().parents[2] / "docs" / "test" / "docker"

FIXTURES = {
    "adversarial": "adversarial_goal.json",
    "normal": "goal.json",
}


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: debug_loop.py <adversarial|normal|path/to/goal.json>")
        return 1

    arg = sys.argv[1]
    if arg in FIXTURES:
        goal_path = DX / FIXTURES[arg]
        label = arg
    else:
        goal_path = Path(arg)
        label = goal_path.stem

    if not goal_path.exists():
        print(f"goal file not found: {goal_path}")
        return 1

    goal = json.loads(goal_path.read_text())
    print(f"{'=' * 70}")
    print(f"GOAL ({label}):")
    print(f"{'=' * 70}")
    print(json.dumps(goal, indent=2))

    print(f"\n{'=' * 70}")
    print(f"SENDING POST /plan to {BASE}/plan ...")
    print(f"{'=' * 70}")

    try:
        r = httpx.post(f"{BASE}/plan", json=goal, timeout=300.0)
    except httpx.HTTPError as err:
        print(f"HTTP ERROR: {err}")
        return 1

    print(f"\nHTTP status: {r.status_code}")
    body = r.json()

    print(f"\n{'=' * 70}")
    print("FULL RESPONSE:")
    print(f"{'=' * 70}")
    print(json.dumps(body, indent=2))

    data = body.get("data", body)

    print(f"\n{'=' * 70}")
    print("SUMMARY:")
    print(f"{'=' * 70}")
    print(f"  status:       {data.get('status')}")
    print(f"  reason_code:  {data.get('reason_code')}")
    print(f"  findings:     {len(data.get('findings', []))} finding(s)")

    for i, f in enumerate(data.get("findings", [])):
        sev = str(f.get("severity", "?"))[:10]
        rcode = str(f.get("reason_code", "?"))[:30]
        msg = str(f.get("message", ""))[:80]
        print(f"    [{i}] {sev:10s} {rcode:30s} {msg}")

    plan = data.get("plan")
    if plan:
        print(f"\n  plan_id:      {plan.get('id')}")
        print(f"  version:      {plan.get('version')}")
        print(f"  tasks:        {len(plan.get('tasks', []))} task(s)")
        for t in plan.get("tasks", []):
            tid = str(t.get("id", "?"))[:15]
            risk = str(t.get("risk_class", "?"))[:10]
            desc = str(t.get("description", ""))[:60]
            print(f"    - {tid:15s} risk={risk:10s} {desc}")

    escalation = data.get("escalation")
    if escalation:
        print(f"\n  escalation_id: {escalation.get('id')}")
        print(f"  question:      {escalation.get('question')}")
        print(f"  esc_status:    {escalation.get('status')}")

    # Save evidence
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    out = LOG_DIR / f"{ts}_debug_{label}.json"
    out.write_text(
        json.dumps(
            {"timestamp": ts, "label": label, "request": {"goal": goal}, "response": body},
            indent=2,
            sort_keys=True,
        )
    )
    print(f"\nEvidence saved: {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
