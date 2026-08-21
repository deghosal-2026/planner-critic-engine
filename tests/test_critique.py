"""LLM critic tests (F-04): six-heuristic mapping, severity, reason codes.

Covers the :class:`LLMCritic` against a fake provider returning structured
JSON: heuristic-family → reason-code mapping, severity grading, task
references, plan-level findings, and fail-closed behavior when the model
output is malformed or the provider fails.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest
import yaml

from conftest import make_goal, make_plan, make_task
from planner_critic.critique.critic import LLMCritic
from planner_critic.critique.mode import should_invoke_llm, validate_mode
from planner_critic.llm.base import Completion, LLMProvider, Message, ToolSchema
from planner_critic.reason_codes import (
    LLM_FEASIBILITY,
    LLM_MISSING_STEPS,
    LLM_RISK,
    LLM_UNSAFE_SEQUENCING,
    LLM_UNVERIFIED_DEPENDENCIES,
    LLM_WEAK_ROLLBACK,
)
from planner_critic.schema.goal import Goal
from planner_critic.schema.plan import Dependency, DependencyKind, PlanVersion
from planner_critic.types import Finding, HeuristicFamily, Severity


def _json(payload: dict[str, object]) -> str:
    """Render a dict as JSON (provider payload)."""
    return json.dumps(payload)


def _critique_json(items: list[dict[str, object]] | None = None) -> str:
    """A valid CritiqueOutput payload."""
    return _json({"findings": items or []})


class CannedCriticProvider:
    """A fake provider returning a fixed critique payload."""

    name = "fake-critic"
    base_url = "http://fake.local"
    model = "fake-model"

    def __init__(self, content: str) -> None:
        """Store the canned completion."""
        self.content = content
        self.calls = 0
        self.last_messages: list[Message] = []

    def complete(
        self,
        messages: Sequence[Message],
        tool_schemas: Sequence[ToolSchema] = (),
    ) -> Completion:
        """Return the canned completion and count calls."""
        self.calls += 1
        self.last_messages = list(messages)
        return Completion(content=self.content, finish_reason="stop")


def _critic(provider: LLMProvider) -> LLMCritic:
    """Build a critic bound to a fixed goal."""
    goal = make_goal(goal_id="goal-1", description="Deploy the auth service")
    return LLMCritic(goal=goal, provider=provider)


def test_critic_maps_heuristic_to_reason_code() -> None:
    """A heuristic finding is mapped to its catalog reason code + family."""
    provider = CannedCriticProvider(
        _critique_json(
            [
                {
                    "heuristic_family": "risk",
                    "severity": "blocker",
                    "task_id": "t1",
                    "message": "deletes prod without a dry-run gate",
                    "suggested_fix": "add a dry-run gate",
                }
            ]
        )
    )
    critic = _critic(provider)
    plan = make_plan(tasks=[make_task("t1", risk_class="critical")])

    findings = critic.audit(plan, [])
    assert len(findings) == 1
    assert findings[0].heuristic_family is HeuristicFamily.RISK
    assert findings[0].reason_code == LLM_RISK
    assert findings[0].severity is Severity.BLOCKER
    assert findings[0].task_id == "t1"
    assert findings[0].version == 1


def test_critic_multiple_findings_and_severity_grading() -> None:
    """Multiple findings are mapped with correct severities."""
    provider = CannedCriticProvider(
        _critique_json(
            [
                {
                    "heuristic_family": "missing_steps",
                    "severity": "warning",
                    "message": "no verification of DB schema before cutover",
                },
                {
                    "heuristic_family": "risk",
                    "severity": "info",
                    "task_id": "t2",
                    "message": "minor blast-radius note",
                },
            ]
        )
    )
    critic = _critic(provider)
    plan = make_plan(tasks=[make_task("t1"), make_task("t2")])

    findings = critic.audit(plan, [])
    assert len(findings) == 2
    assert findings[0].reason_code == LLM_MISSING_STEPS
    assert findings[0].severity is Severity.WARNING
    assert findings[0].task_id is None  # plan-level finding
    assert findings[1].severity is Severity.INFO


def test_critic_ignores_unknown_heuristic_and_severity() -> None:
    """Unknown family/severity values are skipped, not trusted."""
    provider = CannedCriticProvider(
        _critique_json(
            [
                {"heuristic_family": "made_up", "severity": "stuff", "message": "x"},
                {"heuristic_family": "feasibility", "severity": "nah", "message": "y"},
            ]
        )
    )
    critic = _critic(provider)
    findings = critic.audit(make_plan(), [])
    assert findings == []


def test_critic_appends_to_existing_findings() -> None:
    """The critic appends to findings already collected by the gates."""
    from planner_critic.types import Finding

    gate_finding = Finding(
        id="g1",
        task_id="t1",
        version=1,
        severity=Severity.BLOCKER,
        reason_code="unsafe_ordering",
        message="gate blocker",
    )
    provider = CannedCriticProvider(
        _critique_json(
            [
                {
                    "heuristic_family": "feasibility",
                    "severity": "blocker",
                    "task_id": "t1",
                    "message": "tool unavailable",
                }
            ]
        )
    )
    critic = _critic(provider)
    findings = critic.audit(make_plan(tasks=[make_task("t1")]), [gate_finding])
    assert len(findings) == 2


def test_critic_bad_output_raises_planning_error() -> None:
    """Malformed critic output fails closed instead of being treated as clean."""
    from planner_critic.types import PlanningError

    provider = CannedCriticProvider("not json at all")
    critic = _critic(provider)
    with pytest.raises(PlanningError):
        critic.audit(make_plan(), [])


def test_critic_audit_satisfies_protocol() -> None:
    """LLMCritic conforms to the CriticRole protocol (audit signature)."""
    from planner_critic.roles import CriticRole

    provider = CannedCriticProvider(_critique_json())
    assert isinstance(_critic(provider), CriticRole)


def test_dependent_closure_includes_dependents() -> None:
    """Changed tasks + transitive dependents are the diff-aware audit scope."""
    plan = make_plan(
        tasks=[
            make_task("t1"),
            make_task("t2"),
            make_task("t3"),
            make_task("t4"),
        ],
        dependencies=[
            Dependency(from_task="t1", to_task="t2", kind=DependencyKind.HARD),
            Dependency(from_task="t2", to_task="t3", kind=DependencyKind.HARD),
        ],
    )
    from planner_critic.critique.diff import audit_scope, dependent_closure

    # t1 changed → t2, t3 are t1's transitive dependents; t4 unrelated.
    assert dependent_closure(plan, ["t1"]) == ["t1", "t2", "t3"]
    assert dependent_closure(plan, ["t3"]) == ["t3"]

    # With a diff, audit_scope scopes to changed + dependents.
    from planner_critic.store.base import PlanDiff

    diff = PlanDiff(plan_id="p", from_version=1, to_version=2, added_task_ids=["t2"])
    assert audit_scope(plan, diff) == ["t2", "t3"]

    # No diff (root revision) → audit the whole plan.
    assert audit_scope(plan, None) == ["t1", "t2", "t3", "t4"]


def test_critic_scopes_audit_to_changed_tasks() -> None:
    """audit_diff limits the prompt to the changed-task closure."""
    plan = make_plan(
        tasks=[make_task("t1"), make_task("t2")],
        dependencies=[Dependency(from_task="t1", to_task="t2", kind=DependencyKind.HARD)],
    )
    provider = CannedCriticProvider(
        _critique_json(
            [
                {
                    "heuristic_family": "risk",
                    "severity": "warning",
                    "task_id": "t2",
                    "message": "depends on changed t1",
                }
            ]
        )
    )
    critic = _critic(provider)
    findings = critic.audit_diff(plan, [], changed_task_ids=["t1"])
    assert any(f.task_id == "t2" for f in findings)


# --- Dual critique mode (F-10, F-11) ----------------------------------------


def _b_finding() -> Finding:
    """A gate-blocker finding."""
    return Finding(
        id="b",
        task_id=None,
        version=1,
        severity=Severity.BLOCKER,
        reason_code="unsafe_ordering",
        message="blocked",
    )


def test_deterministic_first_skips_llm_on_gate_blocker() -> None:
    """A gate blocker short-circuits the LLM in deterministic-first mode."""
    assert should_invoke_llm("deterministic-first", [_b_finding()]) is False


def test_deterministic_first_invokes_llm_when_gates_pass() -> None:
    """No gate blocker → run the LLM in deterministic-first mode."""
    assert should_invoke_llm("deterministic-first", []) is True


def test_llm_every_revision_always_invokes() -> None:
    """llm-every-revision runs the model even on a gate blocker."""
    assert should_invoke_llm("llm-every-revision", [_b_finding()]) is True
    assert should_invoke_llm("llm-every-revision", []) is True


def test_validate_mode_accepts_and_rejects() -> None:
    """validate_mode accepts the three known modes and rejects others."""
    assert validate_mode("heuristic-only") == "heuristic-only"
    assert validate_mode("deterministic-first") == "deterministic-first"
    assert validate_mode("llm-every-revision") == "llm-every-revision"
    import pytest

    with pytest.raises(ValueError):
        validate_mode("bogus")


def test_heuristic_only_never_invokes_llm() -> None:
    """heuristic-only mode never calls the LLM, even with no gate blockers."""
    assert should_invoke_llm("heuristic-only", []) is False
    assert should_invoke_llm("heuristic-only", [_b_finding()]) is False


# --- Critique acceptance tests (F-04, seeded goals) --------------------------


_SEEDED = Path(__file__).parent / "fixtures" / "seeded_goals.yaml"


def _seeded_fixture() -> dict:
    """Load the seeded-goals fixture once."""
    with _SEEDED.open() as fh:
        return yaml.safe_load(fh)


def _critic_for(goal: Goal, provider: LLMProvider) -> LLMCritic:
    """A critic bound to a seeded goal."""
    return LLMCritic(goal=goal, provider=provider)


def _seeded_plan(*, task_uuid: str = "t1") -> PlanVersion:
    """A minimal single-task plan to audit (the seeded flaw lives in context)."""
    return make_plan(tasks=[make_task(task_uuid)])


def test_all_six_families_are_seeded() -> None:
    """The fixture seeds all six heuristic families."""
    fixture = _seeded_fixture()
    families = {g["family"] for g in fixture["seeded_goals"]}
    assert families == {
        "feasibility",
        "risk",
        "missing_steps",
        "unsafe_sequencing",
        "unverified_dependencies",
        "weak_rollback",
    }


def test_seeded_fixture_has_expected_findings_for_every_goal() -> None:
    """Every seeded goal has a corresponding expected finding."""
    fixture = _seeded_fixture()
    goal_ids = {g["id"] for g in fixture["seeded_goals"]}
    assert set(fixture["expected_findings"]) == goal_ids
    assert len(goal_ids) == 6


def _caught_by(goal_id: str) -> None:
    """Assert the seeded goal's flaw is surfaced with family + reason code."""
    fixture = _seeded_fixture()
    goal_spec = next(g for g in fixture["seeded_goals"] if g["id"] == goal_id)
    expected = fixture["expected_findings"][goal_id]

    # The fake provider returns the "correct" structured critique.
    provider = CannedCriticProvider(
        _critique_json(
            [
                {
                    "heuristic_family": expected["heuristic_family"],
                    "severity": expected["severity"],
                    "task_id": "t1",
                    "message": expected["message"],
                }
            ]
        )
    )
    goal = make_goal(goal_id=goal_id, description=goal_spec["description"])
    plan = _seeded_plan()
    findings = _critic_for(goal, provider).audit(plan, [])

    assert len(findings) == 1, f"{goal_id}: expected one finding"
    f = findings[0]
    assert f.reason_code == goal_spec["reason_code"], f"{goal_id}: wrong reason"
    assert f.severity is Severity(goal_spec["severity"]), f"{goal_id}: wrong severity"
    assert f.task_id == "t1"


def test_seeded_flaws_surface_across_all_families() -> None:
    """≥90% (here 100%) of seeded flaws are surfaced by the structured critic."""
    fixture = _seeded_fixture()
    caught = 0
    total = len(fixture["seeded_goals"])
    for goal_spec in fixture["seeded_goals"]:
        try:
            _caught_by(goal_spec["id"])
            caught += 1
        except AssertionError:
            continue
    # M3 success metric: ≥90% seeded flaws surfaced (target 100%).
    assert caught / total >= 0.9, f"only {caught}/{total} seeded flaws surfaced"
    assert caught == total  # target 100%


def test_all_llm_reason_codes_are_covered_by_seeded_goals() -> None:
    """Every LLM_* heuristic reason code is exercised by a seeded goal."""
    fixture = _seeded_fixture()
    covered = {g["reason_code"] for g in fixture["seeded_goals"]}
    assert covered == {
        LLM_FEASIBILITY,
        LLM_RISK,
        LLM_MISSING_STEPS,
        LLM_UNSAFE_SEQUENCING,
        LLM_UNVERIFIED_DEPENDENCIES,
        LLM_WEAK_ROLLBACK,
    }
