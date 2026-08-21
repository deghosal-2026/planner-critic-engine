"""Re-gate module tests (F-19): precondition re-verification at execution time."""

from __future__ import annotations

import pytest

from planner_critic.probe.base import ProbeRequest, ProbeResult
from planner_critic.regate import ReGateConfig, check_preconditions
from planner_critic.schema.goal import RiskTolerance
from planner_critic.schema.plan import EnvProbe, PlanVersion, Precondition, Task
from planner_critic.store.base import InMemoryStore
from planner_critic.types import ApprovedPlan


def _make_approved_plan(tasks: list[Task]) -> ApprovedPlan:
    plan = PlanVersion(
        id="plan-1",
        goal_id="goal-1",
        version=1,
        tasks=tasks,
    )
    return ApprovedPlan(plan=plan, risk_tolerance=RiskTolerance.BALANCED)


def test_mode_off_returns_pass_regardless_of_preconditions() -> None:
    """When mode is off, check_preconditions always returns pass."""
    task = Task(
        id="t1",
        description="a task",
        preconditions=[
            Precondition(
                description="must be prod",
                fact="env=prod",
                probe=EnvProbe(kind="env_var", query="ENV", expected="prod"),
            )
        ],
    )
    approved = _make_approved_plan([task])
    store = InMemoryStore()
    config = ReGateConfig(mode="off")

    result = check_preconditions(approved, "t1", store, config)

    assert result.status == "pass"
    assert result.stale_preconditions == []
    assert result.replan_triggered is False


def test_before_each_step_no_preconditions_returns_pass() -> None:
    """A task with no preconditions passes re-gate."""
    task = Task(id="t1", description="a task")
    approved = _make_approved_plan([task])
    store = InMemoryStore()

    result = check_preconditions(approved, "t1", store, ReGateConfig(mode="before-each-step"))

    assert result.status == "pass"
    assert result.stale_preconditions == []


def test_before_each_step_precondition_without_probe_returns_pass() -> None:
    """A precondition with no probe has nothing to re-check, so it passes."""
    task = Task(
        id="t1",
        description="a task",
        preconditions=[Precondition(description="must be prod", fact="env=prod")],
    )
    approved = _make_approved_plan([task])
    store = InMemoryStore()

    result = check_preconditions(approved, "t1", store, ReGateConfig(mode="before-each-step"))

    assert result.status == "pass"
    assert result.stale_preconditions == []


def test_before_each_step_matching_probe_returns_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    """A precondition whose probe matches live state passes."""
    task = Task(
        id="t1",
        description="a task",
        preconditions=[
            Precondition(
                description="must be prod",
                fact="env=prod",
                probe=EnvProbe(kind="env_var", query="ENV", expected="prod"),
            )
        ],
    )
    approved = _make_approved_plan([task])
    store = InMemoryStore()

    def _fake_run_probe(request: ProbeRequest) -> ProbeResult:
        return ProbeResult(
            kind=request.kind, query=request.query, observed="prod", matched=True, ok=True
        )

    monkeypatch.setattr("planner_critic.regate.run_probe", _fake_run_probe)

    result = check_preconditions(approved, "t1", store, ReGateConfig(mode="before-each-step"))

    assert result.status == "pass"
    assert result.stale_preconditions == []


def test_before_each_step_mismatched_probe_returns_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    """A precondition whose probe does not match live state returns stale."""
    task = Task(
        id="t1",
        description="a task",
        preconditions=[
            Precondition(
                description="must be prod",
                fact="env=prod",
                probe=EnvProbe(kind="env_var", query="ENV", expected="prod"),
            )
        ],
    )
    approved = _make_approved_plan([task])
    store = InMemoryStore()

    def _fake_run_probe(request: ProbeRequest) -> ProbeResult:
        return ProbeResult(
            kind=request.kind, query=request.query, observed="staging", matched=False, ok=True
        )

    monkeypatch.setattr("planner_critic.regate.run_probe", _fake_run_probe)

    result = check_preconditions(approved, "t1", store, ReGateConfig(mode="before-each-step"))

    assert result.status == "stale"
    assert result.stale_preconditions == ["must be prod"]
    assert result.replan_triggered is False


def test_multiple_stale_preconditions_all_listed(monkeypatch: pytest.MonkeyPatch) -> None:
    """When multiple preconditions are stale, all are listed."""
    task = Task(
        id="t1",
        description="a task",
        preconditions=[
            Precondition(
                description="must be prod",
                fact="env=prod",
                probe=EnvProbe(kind="env_var", query="ENV", expected="prod"),
            ),
            Precondition(
                description="feature flag on",
                fact="ff=on",
                probe=EnvProbe(kind="env_var", query="FF", expected="on"),
            ),
            Precondition(
                description="always valid",
                fact="ok=true",
                probe=EnvProbe(kind="env_var", query="OK", expected="true"),
            ),
        ],
    )
    approved = _make_approved_plan([task])
    store = InMemoryStore()

    call_count = 0

    def _fake_run_probe(request: ProbeRequest) -> ProbeResult:
        nonlocal call_count
        call_count += 1
        # First two probes mismatch, third matches
        if call_count <= 2:
            return ProbeResult(
                kind=request.kind, query=request.query, observed="wrong", matched=False, ok=True
            )
        return ProbeResult(
            kind=request.kind, query=request.query, observed="true", matched=True, ok=True
        )

    monkeypatch.setattr("planner_critic.regate.run_probe", _fake_run_probe)

    result = check_preconditions(approved, "t1", store, ReGateConfig(mode="before-each-step"))

    assert result.status == "stale"
    assert sorted(result.stale_preconditions) == ["feature flag on", "must be prod"]


def test_unknown_task_id_raises_value_error() -> None:
    """Requesting a task_id not in the plan raises ValueError."""
    task = Task(id="t1", description="a task")
    approved = _make_approved_plan([task])
    store = InMemoryStore()

    with pytest.raises(ValueError, match="t2"):
        check_preconditions(approved, "t2", store, ReGateConfig(mode="before-each-step"))
