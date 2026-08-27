"""M7 demo-runner tests (F-66, F-86): scripted roles + hermetic full loop.

The demo is fully hermetic — scripted planner/critic roles, no LLM, no
network. These tests drive the *real* engine loop, the *real* re-gate, and
the *real* replan against the corpus goals, and assert the runner produces
the five-stage narrative with v1 → v2 → v3 history in the store.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from planner_critic.approval import ApprovalGate, ThresholdOutcome
from planner_critic.demo.roles import ScriptedCritic, ScriptedPlanner
from planner_critic.demo.runner import narrative, run_demo
from planner_critic.engine import Engine
from planner_critic.gates import run_deterministic_gates
from planner_critic.loop import LoopConfig
from planner_critic.reason_codes import ROLLBACK_STATE_UNDECLARED
from planner_critic.regate import ReGateResult
from planner_critic.schema.goal import Goal
from planner_critic.store.base import InMemoryStore
from planner_critic.types import Severity

CORPUS_DIR = Path(__file__).parents[1] / "examples" / "goals"
MIGRATION = CORPUS_DIR / "migration.json"
CORPUS_FILES = [
    "migration.json",
    "rollout.json",
    "refactor.json",
    "incident.json",
    "adversarial.json",
]


@pytest.fixture(scope="module")
def corpus_goals() -> dict[str, Goal]:
    """Every corpus goal parsed as a typed Goal."""
    return {
        name: Goal.model_validate(json.loads((CORPUS_DIR / name).read_text()))
        for name in CORPUS_FILES
    }


# -- scripted roles ------------------------------------------------------------


def test_scripted_planner_decomposes_every_corpus_goal(corpus_goals: dict[str, Goal]) -> None:
    """decompose builds a valid v1 for every corpus goal (F-65 -> F-86)."""
    planner = ScriptedPlanner()
    for name, goal in corpus_goals.items():
        v1 = planner.decompose(goal)
        assert v1.version == 1, name
        assert v1.goal_id == goal.id, name
        gate_findings = run_deterministic_gates(v1)
        if goal.id == "demo-adversarial":
            assert any(f.severity is Severity.BLOCKER for f in gate_findings), name
        else:
            assert not any(f.severity is Severity.BLOCKER for f in gate_findings), name


def test_scripted_critic_flags_v1_and_passes_v2(corpus_goals: dict[str, Goal]) -> None:
    """The critic flags v1 with the seeded family, and clears v2."""
    planner = ScriptedPlanner()
    critic = ScriptedCritic()
    for name, goal in corpus_goals.items():
        flaw = json.loads((CORPUS_DIR / name).read_text())["_seeded_flaw"]
        v1 = planner.decompose(goal)
        findings = critic.audit(v1, [])
        assert findings, name
        assert findings[0].heuristic_family == flaw["family"], name
        assert findings[0].task_id == flaw["task_id"], name

        v2 = planner.revise(v1, findings)
        # Filter out the v0.2.2 advisory for legacy rollbacks without typed restoration
        v2_blockers = [
            f for f in run_deterministic_gates(v2) if f.reason_code != ROLLBACK_STATE_UNDECLARED
        ]
        assert v2_blockers == [], name
        assert critic.audit(v2, []) == [], name


def test_loop_approves_every_corpus_goal_at_v2(corpus_goals: dict[str, Goal]) -> None:
    """The real loop converges to approval on revision 2 for every goal."""
    for name, goal in corpus_goals.items():
        result = Engine(
            planner=ScriptedPlanner(), critic=ScriptedCritic(), config=LoopConfig()
        ).plan(goal)
        assert result.is_approved, name
        assert result.approved_plan is not None, name
        assert result.approved_plan.plan.version == 2, name


def test_scripted_roles_are_deterministic(corpus_goals: dict[str, Goal]) -> None:
    """Identical inputs produce identical plans (F-74, demo contract)."""
    goal = corpus_goals["migration.json"]
    a = ScriptedPlanner().decompose(goal)
    b = ScriptedPlanner().decompose(goal)
    # created_at is inherently noisy; the plan structure must be identical.
    assert a.model_dump(exclude={"created_at"}) == b.model_dump(exclude={"created_at"})


# -- narrative -----------------------------------------------------------------


def test_narrative_is_pure_and_covers_all_five_stages(
    corpus_goals: dict[str, Goal],
) -> None:
    """narrative returns the five-stage story given explicit inputs."""
    goal = corpus_goals["migration.json"]
    planner = ScriptedPlanner()
    v1 = planner.decompose(goal)
    v1_findings = ScriptedCritic().audit(v1, [])
    v2 = planner.revise(v1, v1_findings)
    approved = ApprovalGate(goal.risk_tolerance).approve(v2, ThresholdOutcome())
    replanned = planner.revise(v2, []).model_copy(update={"version": 3})

    lines = narrative(
        goal=goal,
        v1=v1,
        v1_findings=v1_findings,
        approved=approved,
        re_gate=ReGateResult(status="stale", stale_preconditions=["maintenance window is open"]),
        replanned=replanned,
    )
    joined = "\n".join(lines)
    assert "[1/5 draft]" in joined
    assert "[2/5 approve]" in joined and "v2" in joined
    assert "[3/5 re-gate]" in joined and "stale" in joined
    assert "[4/5 replan]" in joined and "v3" in joined
    assert "[5/5 complete]" in joined
    assert v1_findings[0].message in joined


# -- run_demo ------------------------------------------------------------------


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the demo window var is absent before and after each run."""
    monkeypatch.delenv("PC_DEMO_MAINTENANCE_WINDOW", raising=False)


def test_run_demo_hermetic_full_run(clean_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    """plan -> approve -> re-gate stale -> replan -> complete, store history."""
    store = InMemoryStore()
    rc = run_demo(MIGRATION, store)
    assert rc == 0

    out = capsys.readouterr().out
    assert "[1/5 draft]" in out
    assert "[2/5 approve]" in out
    assert "[3/5 re-gate]" in out and "stale" in out
    assert "[4/5 replan]" in out
    assert "[5/5 complete]" in out
    assert "graph TD" in out
    assert "v1:" in out and "v2:" in out and "v3:" in out

    versions = sorted(p.version for p in store.list_plans(goal_id="demo-migration"))
    assert versions == [1, 2, 3]

    v1 = store.get_plan("plan-demo-migration", 1)
    v2 = store.get_plan("plan-demo-migration-r2", 2)
    v3 = store.get_plan("plan-demo-migration-r2", 3)
    assert v1 is not None and v2 is not None and v3 is not None
    assert {t.id for t in v1.tasks} == {"snapshot", "backfill", "cutover"}
    assert {t.id for t in v2.tasks} == {"snapshot", "backfill", "verify", "cutover"}
    assert v3.version == 3
    assert v3.parent_version == v2.id

    link = store.get_replan_link("plan-demo-migration-r2", 3)
    assert link is not None
    assert link.policy == "patch"
    assert link.parent_version == 2

    traces = store.get_execution_traces("plan-demo-migration-r2")
    # v2 = snapshot, backfill, verify, cutover: the first three run ok, then
    # the drifted cutover is blocked by the stale re-gate.
    assert [t.outcome for t in traces] == ["ok", "ok", "ok", "blocked: re-gate stale"]


def test_run_demo_no_graph_skips_visuals(
    clean_env: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """--no-graph suppresses replay text and the Mermaid DAG."""
    rc = run_demo(MIGRATION, InMemoryStore(), no_graph=True)
    assert rc == 0
    out = capsys.readouterr().out
    assert "graph TD" not in out
    assert "replay:" not in out
    assert "[5/5 complete]" in out


def test_run_demo_invalid_goal_returns_one(
    clean_env: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing or invalid goal file fails closed with exit code 1."""
    rc = run_demo(CORPUS_DIR / "nope.json", InMemoryStore())
    assert rc == 1
    assert "is not a valid Goal" in capsys.readouterr().out


def test_run_demo_unknown_goal_id_fails_closed(
    clean_env: None, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A well-formed goal with an unknown id fails closed (D11 §8)."""
    unknown = tmp_path / "unknown.json"
    unknown.write_text(
        json.dumps({"id": "demo-whoami", "description": "a goal with no demo scenario"})
    )
    rc = run_demo(unknown, InMemoryStore())
    assert rc == 1
    assert "demo failed: no demo scenario" in capsys.readouterr().out


def test_run_demo_restores_drift_env(
    clean_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The runner restores the drifted env var after the re-gate step."""
    monkeypatch.setenv("PC_DEMO_MAINTENANCE_WINDOW", "open")
    rc = run_demo(MIGRATION, InMemoryStore())
    assert rc == 0
    assert os.environ["PC_DEMO_MAINTENANCE_WINDOW"] == "open"


def test_run_demo_refactor_goal_uses_probe_precondition(
    clean_env: None,
) -> None:
    """The refactor goal's swap precondition is probe-gated (unverified deps)."""
    refactor = corpus_refactor_goal()
    planner = ScriptedPlanner()
    v2 = planner.revise(planner.decompose(refactor), [])
    swap = next(t for t in v2.tasks if t.id == "swap")
    probes = [pc.probe for pc in swap.preconditions if pc.probe is not None]
    assert len(probes) == 1
    assert probes[0].query == "PC_DEMO_MAINTENANCE_WINDOW"
    assert probes[0].expected == "open"


def corpus_refactor_goal() -> Goal:
    """Load the refactor corpus goal."""
    return Goal.model_validate(json.loads((CORPUS_DIR / "refactor.json").read_text()))
