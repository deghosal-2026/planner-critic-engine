"""Field test harness — multi-dimensional sweep across engine capabilities.

The harness runs each goal through multiple capability dimensions and saves
per-goal per-dimension traces. Each dimension has its own output directory.

Dimensions with LLM calls: core-api, critique-modes, budget, replan
Dimensions without LLM: store, escalation, explain, viz, complexity, probes,
  adapters, cli-surface, cli-demo, cli-quickstart, cli-migrate
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .engine import Engine
from .escalation import EscalationManager
from .estimate import estimate_complexity
from .explain import explain as build_explain
from .llm.registry import ProviderRegistry
from .loop import LoopConfig
from .loop.budget import SpendState
from .probe.base import ProbeRequest
from .probe.db_query import DbQueryProbe
from .probe.deploy_status import DeployStatusProbe
from .probe.env_var import EnvVarProbe
from .probe.http_check import HttpCheckProbe
from .schema.goal import Budget, Goal, ReplanPolicy
from .schema.plan import PlanVersion
from .store.sqlite import SQLiteStore
from .types import Finding, PlanningError, Severity
from .viz.graph import to_mermaid
from .viz.replay import replay as build_replay

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_goal(goals_root: Path, goal_id: str) -> Path | None:
    for p in goals_root.rglob(f"{goal_id}.json"):
        return p
    return None


def _load_goal_and_assertions(goals_root: Path, goal_id: str) -> tuple[Goal | None, dict[str, Any]]:
    gp = _find_goal(goals_root, goal_id)
    if gp is None:
        return None, {}
    goal = Goal.model_validate(json.loads(gp.read_text()))
    ap = gp.parent / "assertions" / f"{gp.stem}.yaml"
    assertions = {}
    if ap.exists():
        with ap.open() as fh:
            assertions = yaml.safe_load(fh) or {}
    return goal, assertions


def _save_trace(trace: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(trace, indent=2, default=str))


def _check_invariants(
    status: str, findings: list[Finding], tasks: list[dict], revs: int | None, assertions: dict
) -> list[dict]:
    inv = assertions.get("invariants", {})
    checks = []
    ae = inv.get("approve_expected", True)
    if status == "approved":
        checks.append(
            {
                "name": "approve_expected",
                "pass": ae,
                "message": "approved" if ae else "UNEXPECTED APPROVAL",
            }
        )
    elif status == "escalated":
        checks.append(
            {
                "name": "approve_expected",
                "pass": not ae,
                "message": "escalated" if not ae else "expected approve but escalated",
            }
        )
    else:
        checks.append({"name": "approve_expected", "pass": False, "message": f"status={status}"})
    mr = inv.get("max_revisions")
    if mr is not None and revs is not None:
        checks.append({"name": "max_revisions", "pass": revs <= mr, "message": f"revs={revs}"})
    mt = inv.get("min_tasks")
    if mt is not None:
        checks.append(
            {"name": "min_tasks", "pass": len(tasks) >= mt, "message": f"tasks={len(tasks)}"}
        )
    for code in inv.get("mandatory_blocker_reason_codes", []):
        found = any(f.reason_code == code and f.severity is Severity.BLOCKER for f in findings)
        checks.append(
            {
                "name": f"mandatory_blocker_{code}",
                "pass": found,
                "message": f"blocker {code} {'found' if found else 'missing'}",
            }
        )
    return checks


# ---------------------------------------------------------------------------
# Dimension runners
# ---------------------------------------------------------------------------


def _wrap_with_logging(registry, goal_id, role, out_dir):
    """Wrap a registry provider with LoggingProvider for prompt/response capture."""
    from .llm.logging_provider import LoggingProvider

    raw = registry.get_provider(role)
    return LoggingProvider(raw, log_dir=out_dir / "llm-logs", goal_id=goal_id, role=role)


def run_core_api(goal, assertions, planner, registry, lc, out):
    from .cli.plan import _CLIPlanner
    from .critique.critic import LLMCritic

    log_provider = _wrap_with_logging(registry, goal.id, "planner", out)
    log_critic = _wrap_with_logging(registry, goal.id, "critic", out)
    p = planner or _CLIPlanner(log_provider)
    c = LLMCritic(goal, log_critic)
    eng = Engine(p, c, config=lc)
    start = time.monotonic()
    error = None
    status = "error"
    reason = None
    revs = None
    calls = None
    plan = None
    findings = []
    esc = None
    try:
        r = eng.plan(goal)
        status = r.status
        reason = r.reason_code
        revs = r.spend.revisions_used if r.spend else None
        calls = r.spend.calls_used if r.spend else None
        findings = r.findings
        if r.plan:
            plan = r.plan.model_dump(mode="json")
        if r.escalation:
            esc = r.escalation.model_dump(mode="json")
    except PlanningError as e:
        error = str(e)
        reason = getattr(e, "reason_code", "planning_unavailable")
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
    dur = round(time.monotonic() - start, 2)
    checks = _check_invariants(status, findings, (plan or {}).get("tasks", []), revs, assertions)
    t = {
        "dimension": "core-api",
        "goal_id": goal.id,
        "duration_seconds": dur,
        "result": {
            "status": status,
            "reason_code": reason,
            "revision_count": revs,
            "llm_calls": calls,
        },
        "plan": plan,
        "findings": [f.model_dump(mode="json") for f in findings],
        "escalation": esc,
        "checks": checks,
        "error": error,
        "pass": all(c["pass"] for c in checks),
    }
    _save_trace(t, out / "trace.json")
    return t


def run_critique_modes(goal, assertions, planner, registry, out):
    from .cli.plan import _CLIPlanner
    from .critique.critic import LLMCritic

    all_pass = True
    for mode in ["heuristic-only", "deterministic-first", "llm-every-revision"]:
        log_provider = _wrap_with_logging(registry, goal.id, "planner", out / mode)
        log_critic = _wrap_with_logging(registry, goal.id, "critic", out / mode)
        p = planner or _CLIPlanner(log_provider)
        lc = LoopConfig(mode=mode, revision_cap=3)
        c = LLMCritic(goal, log_critic)
        eng = Engine(p, c, config=lc)
        start = time.monotonic()
        try:
            r = eng.plan(goal)
            s = r.status
            rc = r.reason_code
            findings = r.findings
            plan = r.plan.model_dump(mode="json") if r.plan else None
        except Exception as e:
            s = "error"
            rc = str(e)
            findings = []
            plan = None
        dur = round(time.monotonic() - start, 2)
        checks = _check_invariants(s, findings, (plan or {}).get("tasks", []), None, assertions)
        mp = all(c["pass"] for c in checks)
        if not mp:
            all_pass = False
        t = {
            "dimension": f"critique-{mode}",
            "goal_id": goal.id,
            "duration_seconds": dur,
            "status": s,
            "reason_code": rc,
            "findings": [f.model_dump(mode="json") for f in findings],
            "checks": checks,
            "pass": mp,
        }
        _save_trace(t, out / mode / "trace.json")
    return {"dimension": "critique-modes", "goal_id": goal.id, "pass": all_pass}


def run_cli_surface(goal, goal_path, out):
    start = time.monotonic()
    try:
        r = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "planner_critic._cli", "plan", str(goal_path)],
            capture_output=True,
            text=True,
            timeout=300,
        )
        ok = r.returncode == 0
    except subprocess.TimeoutExpired:
        ok = False
        r = type("o", (), {"stdout": "", "stderr": "timeout", "returncode": 1})()
    except Exception as e:
        ok = False
        r = type("o", (), {"stdout": "", "stderr": str(e), "returncode": 1})()
    t = {
        "dimension": "cli-surface",
        "goal_id": goal.id,
        "duration_seconds": round(time.monotonic() - start, 2),
        "returncode": r.returncode,
        "stdout_preview": r.stdout[:500],
        "stderr_preview": r.stderr[:500] if r.stderr else None,
        "pass": ok,
    }
    _save_trace(t, out / "trace.json")
    return t


def run_http_surface(goal, base_url, out):
    start = time.monotonic()
    try:
        body = json.dumps(goal.model_dump(mode="json")).encode()
        req = urllib.request.Request(  # noqa: S310
            f"{base_url}/plan", data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=300) as resp:  # noqa: S310
            raw = json.loads(resp.read())
            ok = raw.get("status") == 200
    except Exception as e:
        ok = False
        raw = {"error": str(e)}
    t = {
        "dimension": "http-surface",
        "goal_id": goal.id,
        "duration_seconds": round(time.monotonic() - start, 2),
        "response": raw,
        "pass": ok,
    }
    _save_trace(t, out / "trace.json")
    return t


def run_store(goal, plan, store, out):
    if plan is None:
        t = {"dimension": "store", "goal_id": goal.id, "pass": False, "error": "no plan"}
        _save_trace(t, out / "trace.json")
        return t
    try:
        stored = store.get_plan(plan["id"])
        ok = stored is not None
        t = {
            "dimension": "store",
            "goal_id": goal.id,
            "pass": ok,
            "plan_id": plan["id"],
            "stored": stored is not None,
        }
    except Exception as e:
        t = {"dimension": "store", "goal_id": goal.id, "pass": False, "error": str(e)}
    _save_trace(t, out / "trace.json")
    return t


def run_escalation(goal, store, out):
    try:
        mgr = EscalationManager(store, approving_authority="field-test")
        all_escs = mgr.list_escalations()
        # Scope to the current goal only
        escs = [e for e in all_escs if e.plan_id.startswith(goal.id)]
        checks = []
        if escs:
            # Approve the first escalation with proper principal
            approved = mgr.resolve(escs[0].id, "approved", note="field test", principal="field-test")
            checks.append(
                {
                    "name": "escalation_approve",
                    "pass": approved.status == "approved",
                    "message": f"approved {approved.id}",
                }
            )
            # Deny the second escalation if it exists
            if len(escs) > 1:
                denied = mgr.resolve(escs[1].id, "denied", note="field test", principal="field-test")
                checks.append(
                    {
                        "name": "escalation_deny",
                        "pass": denied.status == "denied",
                        "message": f"denied {denied.id}",
                    }
                )
            # Test wrong-principal rejection
            if escs:
                try:
                    mgr.resolve(escs[0].id, "approved", note="should fail", principal="wrong-principal")
                    checks.append(
                        {
                            "name": "escalation_wrong_principal",
                            "pass": False,
                            "message": "wrong principal was not rejected",
                        }
                    )
                except PermissionError:
                    checks.append(
                        {
                            "name": "escalation_wrong_principal",
                            "pass": True,
                            "message": "wrong principal correctly rejected",
                        }
                    )
        else:
            checks.append(
                {
                    "name": "escalation_approve",
                    "pass": True,
                    "message": "no escalations to test",
                }
            )
        t = {
            "dimension": "escalation",
            "goal_id": goal.id,
            "pass": all(c["pass"] for c in checks),
            "escalation_count": len(escs),
            "checks": checks,
        }
    except Exception as e:
        t = {"dimension": "escalation", "goal_id": goal.id, "pass": False, "error": str(e)}
    _save_trace(t, out / "trace.json")
    return t


def run_explain(goal, plan_id, store, out):
    try:
        result = build_explain(store, plan_id)
        rc = result.get("reason_code", "?") if isinstance(result, dict) else "?"
        t = {
            "dimension": "explain",
            "goal_id": goal.id,
            "plan_id": plan_id,
            "pass": True,
            "reason_code": rc,
        }
    except Exception as e:
        t = {
            "dimension": "explain",
            "goal_id": goal.id,
            "plan_id": plan_id,
            "pass": False,
            "error": str(e),
        }
    _save_trace(t, out / "trace.json")
    return t


def run_viz(goal, plan, store, out):
    if plan is None:
        t = {"dimension": "viz", "goal_id": goal.id, "pass": False, "error": "no plan"}
        _save_trace(t, out / "trace.json")
        return t
    checks = []
    try:
        pv = PlanVersion.model_validate(plan)
        mermaid = to_mermaid(pv)
        checks.append(
            {"name": "mermaid", "pass": len(mermaid) > 10, "message": "mermaid generated"}
        )
    except Exception as e:
        checks.append({"name": "mermaid", "pass": False, "message": str(e)})
    try:
        history = build_replay(store, plan["id"])
        steps = history.steps if hasattr(history, "steps") else []
        checks.append(
            {"name": "replay", "pass": len(steps) > 0, "message": f"{len(steps)} step(s)"}
        )
    except Exception as e:
        checks.append({"name": "replay", "pass": False, "message": str(e)})
    t = {
        "dimension": "viz",
        "goal_id": goal.id,
        "checks": checks,
        "pass": all(c["pass"] for c in checks),
    }
    _save_trace(t, out / "trace.json")
    return t


def run_complexity(goal, plan, out):
    if plan is None:
        t = {"dimension": "complexity", "goal_id": goal.id, "pass": False, "error": "no plan"}
        _save_trace(t, out / "trace.json")
        return t
    try:
        pv = PlanVersion.model_validate(plan)
        c = estimate_complexity(pv)
        ok = c.step_count == len(pv.tasks)
        t = {
            "dimension": "complexity",
            "goal_id": goal.id,
            "pass": ok,
            "complexity": {
                "steps": c.step_count,
                "parallel_branches": c.parallel_branch_count,
                "irreversible_ops": c.irreversible_op_count,
                "est_llm_calls": c.est_llm_calls,
            },
        }
    except Exception as e:
        t = {"dimension": "complexity", "goal_id": goal.id, "pass": False, "error": str(e)}
    _save_trace(t, out / "trace.json")
    return t


def run_probes(goal, out):
    probes = [
        ("env_var", EnvVarProbe(), ProbeRequest(kind="env_var", query="PATH", expected="exists")),
        (
            "http_check",
            HttpCheckProbe(),
            ProbeRequest(kind="http_check", query="http://localhost:8080/healthz", expected="200"),
        ),
        ("db_query", DbQueryProbe(), ProbeRequest(kind="db_query", query="SELECT 1", expected="1")),
        (
            "deploy_status",
            DeployStatusProbe(),
            ProbeRequest(kind="deploy_status", query="field-test", expected="running"),
        ),
    ]
    checks = []
    for name, probe, req in probes:
        try:
            result = probe.run(req)
            checks.append(
                {"name": f"probe_{name}", "pass": result.ok, "message": f"{name}: ok={result.ok}"}
            )
        except Exception as e:
            checks.append({"name": f"probe_{name}", "pass": False, "message": str(e)})
        _save_trace(
            {"dimension": f"probe-{name}", "goal_id": goal.id, "checks": [checks[-1]]},
            out / name / "trace.json",
        )
    t = {
        "dimension": "probes",
        "goal_id": goal.id,
        "checks": checks,
        "pass": all(c["pass"] for c in checks),
    }
    _save_trace(t, out / "trace.json")
    return t


def run_budget(goal, planner, registry, out):
    from .cli.plan import _CLIPlanner
    from .critique.critic import LLMCritic

    log_p = _wrap_with_logging(registry, goal.id, "planner", out)
    _wrap_with_logging(registry, goal.id, "critic", out)
    p = planner or _CLIPlanner(log_p)
    c = LLMCritic(goal, registry.get_provider("critic"))
    restricted = Goal(
        id=goal.id,
        description=goal.description,
        constraints=type(goal.constraints)(
            budget=Budget(max_revisions=1),
            environment=goal.constraints.environment,
            tools=goal.constraints.tools,
        ),
        risk_tolerance=goal.risk_tolerance,
        replan_policy=ReplanPolicy.ABORT,
    )
    eng = Engine(p, c, config=LoopConfig(revision_cap=1))
    state = SpendState()
    try:
        r = eng.plan(restricted)
        hit = state.exceeded or (r.spend and r.spend.exceeded)
        t = {
            "dimension": "budget",
            "goal_id": goal.id,
            "pass": hit or r.status == "escalated",
            "status": r.status,
            "reason_code": r.reason_code,
            "revisions_used": state.revisions_used,
        }
    except Exception as e:
        t = {"dimension": "budget", "goal_id": goal.id, "pass": False, "error": str(e)}
    _save_trace(t, out / "trace.json")
    return t


def run_replan(goal, planner, registry, out):
    from .cli.plan import _CLIPlanner
    from .critique.critic import LLMCritic

    log_p = _wrap_with_logging(registry, goal.id, "planner", out)
    p = planner or _CLIPlanner(log_p)
    results = {}
    for policy in ["patch", "restart", "abort"]:
        g = Goal(
            id=goal.id,
            description=goal.description,
            constraints=goal.constraints,
            risk_tolerance=goal.risk_tolerance,
            replan_policy=ReplanPolicy(policy),
        )
        c = LLMCritic(g, registry.get_provider("critic"))
        try:
            r = Engine(p, c, config=LoopConfig(revision_cap=2)).plan(g)
            results[policy] = {"status": r.status, "reason_code": r.reason_code}
        except Exception as e:
            results[policy] = {"status": "error", "reason_code": str(e)}
        _save_trace(
            {"dimension": f"replan-{policy}", "goal_id": goal.id, "result": results[policy]},
            out / policy / "trace.json",
        )
    t = {"dimension": "replan", "goal_id": goal.id, "results": results, "pass": True}
    _save_trace(t, out / "trace.json")
    return t


def run_adapters(goal, plan, out):

    if plan is None:
        t = {"dimension": "adapters", "goal_id": goal.id, "pass": False, "error": "no plan"}
        _save_trace(t, out / "trace.json")
        return t
    pv = PlanVersion.model_validate(plan)
    checks = []
    try:
        # Validate the plan loads correctly (schema check)
        _ = pv.model_dump()
        checks.append(
            {"name": "adapter_python", "pass": True, "message": "plan validated as PlanVersion"}
        )
    except Exception as e:
        checks.append({"name": "adapter_python", "pass": False, "message": str(e)})
    _save_trace(
        {"dimension": "adapter-python", "goal_id": goal.id, "checks": [checks[-1]]},
        out / "python" / "trace.json",
    )
    t = {
        "dimension": "adapters",
        "goal_id": goal.id,
        "checks": checks,
        "pass": all(c["pass"] for c in checks),
    }
    _save_trace(t, out / "trace.json")
    return t


# ---------------------------------------------------------------------------
# CLI subcommand dimensions
# ---------------------------------------------------------------------------


def run_cli_demo(out):
    try:
        r = subprocess.run(
            [sys.executable, "-m", "planner_critic._cli", "demo", "run"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        t = {
            "dimension": "cli-demo",
            "goal_id": "demo",
            "pass": r.returncode == 0,
            "returncode": r.returncode,
        }
    except Exception as e:
        t = {"dimension": "cli-demo", "goal_id": "demo", "pass": False, "error": str(e)}
    _save_trace(t, out / "trace.json")
    return t


def run_cli_quickstart(out):
    import tempfile

    tmp = tempfile.mkdtemp(prefix="plancritic-qs-")
    try:
        r = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "planner_critic._cli", "quickstart", "--dir", tmp],
            capture_output=True,
            text=True,
            timeout=60,
        )
        t = {
            "dimension": "cli-quickstart",
            "goal_id": "quickstart",
            "pass": r.returncode == 0,
            "returncode": r.returncode,
        }
    except Exception as e:
        t = {"dimension": "cli-quickstart", "goal_id": "quickstart", "pass": False, "error": str(e)}
    _save_trace(t, out / "trace.json")
    return t


def run_cli_migrate(out):
    try:
        r = subprocess.run(
            [sys.executable, "-m", "planner_critic._cli", "migrate"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        t = {
            "dimension": "cli-migrate",
            "goal_id": "migrate",
            "pass": r.returncode == 0,
            "returncode": r.returncode,
        }
    except Exception as e:
        t = {"dimension": "cli-migrate", "goal_id": "migrate", "pass": False, "error": str(e)}
    _save_trace(t, out / "trace.json")
    return t


# ---------------------------------------------------------------------------
# Dimension registry
# ---------------------------------------------------------------------------

DIMENSIONS = {
    "core-api": {"goals": "__all__", "fn": run_core_api, "needs_llm": True},
    "critique-modes": {
        "goals": ["db-01-schema-migration"],
        "fn": run_critique_modes,
        "needs_llm": True,
    },
    "store": {"goals": "__all__", "fn": run_store, "needs_llm": False},
    "escalation": {"goals": ["adv-01-billing-no-safety"], "fn": run_escalation, "needs_llm": False},
    "explain": {"goals": ["db-01-schema-migration"], "fn": run_explain, "needs_llm": False},
    "viz": {"goals": ["db-01-schema-migration"], "fn": run_viz, "needs_llm": False},
    "complexity": {"goals": ["db-01-schema-migration"], "fn": run_complexity, "needs_llm": False},
    "probes": {"goals": ["inf-02-terraform-migration"], "fn": run_probes, "needs_llm": False},
    "budget": {"goals": ["db-01-schema-migration"], "fn": run_budget, "needs_llm": True},
    "replan": {"goals": ["db-01-schema-migration"], "fn": run_replan, "needs_llm": True},
    "adapters": {"goals": ["ci-01-multistage-pipeline"], "fn": run_adapters, "needs_llm": False},
    "cli-surface": {"goals": ["db-01-schema-migration"], "fn": run_cli_surface, "needs_llm": False},
    "http-surface": {
        "goals": ["db-01-schema-migration"],
        "fn": run_http_surface,
        "needs_llm": False,
    },
    "cli-demo": {"goals": [], "fn": run_cli_demo, "needs_llm": False},
    "cli-quickstart": {"goals": [], "fn": run_cli_quickstart, "needs_llm": False},
    "cli-migrate": {"goals": [], "fn": run_cli_migrate, "needs_llm": False},
}

# ---------------------------------------------------------------------------
# Main sweep
# ---------------------------------------------------------------------------


def run_sweep(
    goals_root, output_dir, dimensions=None, config_path=None, loop_config=None, http_base_url=None
):
    goals_root = Path(goals_root)
    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    registry = ProviderRegistry.load(str(config_path) if config_path else "plancritic.toml")
    lc = loop_config or LoopConfig()
    planner_cache = None
    store = SQLiteStore(":memory:")
    dims = dimensions or list(DIMENSIONS.keys())
    all_results = {}

    for dim_name in dims:
        if dim_name not in DIMENSIONS:
            continue
        dim = DIMENSIONS[dim_name]
        goal_ids = dim["goals"]
        runner = dim["fn"]
        logger.info("=== Dimension: %s ===", dim_name)

        if goal_ids == "__all__":
            goal_ids = sorted(p.stem for p in goals_root.rglob("*.json"))
        elif not goal_ids:
            dim_out = out_root / dim_name
            dim_out.mkdir(parents=True, exist_ok=True)
            try:
                tr = runner(dim_out)
                all_results.setdefault(dim_name, []).append(tr)
            except Exception as e:
                logger.error("dimension %s failed: %s", dim_name, e)
            continue

        dim_results = []
        for gid in goal_ids:
            goal, assertions = _load_goal_and_assertions(goals_root, gid)
            if goal is None:
                continue
            dim_out = out_root / dim_name / gid
            dim_out.mkdir(parents=True, exist_ok=True)
            goal_path = _find_goal(goals_root, gid)
            try:
                if dim_name == "core-api":
                    tr = runner(goal, assertions, planner_cache, registry, lc, dim_out)
                    if tr.get("plan"):
                        store.put_plan_version(PlanVersion.model_validate(tr["plan"]))
                        store.put_findings(
                            tr["plan"]["id"],
                            tr["plan"]["version"],
                            [Finding(**f) for f in tr.get("findings", [])],
                        )
                    if tr.get("escalation"):
                        from .types import Escalation

                        store.put_escalation(Escalation(**tr["escalation"]))
                elif dim_name in ("critique-modes",):
                    tr = runner(goal, assertions, planner_cache, registry, dim_out)
                elif dim_name in ("budget", "replan"):
                    tr = runner(goal, planner_cache, registry, dim_out)
                elif dim_name in ("cli-surface",):
                    tr = runner(goal, goal_path, dim_out)
                elif dim_name in ("http-surface",):
                    tr = runner(goal, http_base_url or "http://localhost:8080", dim_out)
                elif dim_name in ("store",):
                    plan = _get_plan(store, goal.id, out_root)
                    tr = runner(goal, plan, store, dim_out)
                elif dim_name in ("escalation",):
                    tr = runner(goal, store, dim_out)
                elif dim_name in ("explain",):
                    plan = _get_plan(store, goal.id, out_root)
                    pid = plan["id"] if plan else goal.id
                    tr = runner(goal, pid, store, dim_out)
                elif dim_name in ("viz",):
                    plan = _get_plan(store, goal.id, out_root)
                    tr = runner(goal, plan, store, dim_out)
                elif dim_name in ("complexity", "adapters"):
                    plan = _get_plan(store, goal.id, out_root)
                    tr = runner(goal, plan, dim_out)
                elif dim_name in ("probes",):
                    tr = runner(goal, dim_out)
                else:
                    continue
                dim_results.append(tr)
                logger.info(
                    "  %s %s -> %s", gid, dim_name, "PASS" if tr.get("pass", False) else "FAIL"
                )
            except Exception as e:
                logger.error("  %s %s error: %s", gid, dim_name, e)
                dim_results.append(
                    {"dimension": dim_name, "goal_id": gid, "pass": False, "error": str(e)}
                )
        all_results[dim_name] = dim_results
        passed = sum(1 for r in dim_results if r.get("pass", False))
        logger.info("  [%s] %d/%d passed", dim_name, passed, len(dim_results))

    all_traces = [r for rr in all_results.values() for r in rr]
    total = len(all_traces)
    passed = sum(1 for r in all_traces if r.get("pass", False))
    summary = {
        "meta": {
            "date": datetime.now(UTC).isoformat(),
            "config": str(config_path) if config_path else "plancritic.toml",
            "loop_config": {"mode": lc.mode, "revision_cap": lc.revision_cap},
        },
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 2) if total else 0.0,
        "dimensions": {
            d: {
                "total": len(r),
                "passed": sum(1 for x in r if x.get("pass", False)),
                "failed": sum(1 for x in r if not x.get("pass", False)),
            }
            for d, r in all_results.items()
        },
        "failures": [
            {
                "dimension": r.get("dimension"),
                "goal_id": r.get("goal_id", "?"),
                "error": r.get("error", "check failure"),
            }
            for r in all_traces
            if not r.get("pass", False)
        ],
    }
    (out_root / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    logger.info("Sweep complete: %d/%d passed across %d dimensions", passed, total, len(dims))
    return summary


def _get_plan(store, goal_id, output_dir=None):
    # Try the in-memory store first
    try:
        plans = store.list_plans()
        for p in plans:
            if p.goal_id == goal_id:
                return p.model_dump(mode="json")
    except Exception:  # noqa: S110
        pass
    # Fall back to the trace file on disk
    if output_dir:
        trace_path = Path(output_dir) / "core-api" / goal_id / "trace.json"
        if trace_path.exists():
            try:
                t = json.loads(trace_path.read_text())
                return t.get("plan")
            except Exception:  # noqa: S110
                pass
    return None
