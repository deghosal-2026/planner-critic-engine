"""rollback_credible gate tests (#216).

``rollback_present`` (#F-15) only proves a rollback section exists. This gate
proves the section can mean something, using schema-derived structure only
(no new schema fields — patch invariant):

* **Unreachable** — the forward action has no automated inverse in the
  #160 action-inversion registry (publish / destroy / commit), so the named
  rollback cannot execute.
* **Self-dependent** — the task's own preconditions claim establishment by
  the task itself; the guarded step (and its rollback) sits on a circular
  basis.
* **Inconsistent-state** — a later task's precondition fact is established
  by this task, but that later task neither verifies nor can roll back:
  restoring pre-write state silently invalidates its basis.
* **Post-consumed recovery** — a hard-dependency consumer runs inside the
  write→rollback window with neither verification nor rollback: if the
  producer ever rolls back, the consumed state is erased with nothing to
  re-sync (the dual-write case from the Part 3 thread).
"""

from __future__ import annotations

from conftest import hard_dep, make_plan, make_task
from planner_critic.gates import run_deterministic_gates
from planner_critic.reason_codes import (
    ROLLBACK_INCONSISTENT_STATE,
    ROLLBACK_POST_CONSUMED,
    ROLLBACK_SELF_DEPENDENT,
    ROLLBACK_UNREACHABLE,
)
from planner_critic.schema.plan import Task
from planner_critic.types import Severity

_RB: dict[str, object] = {"trigger": "fail", "action": "revert", "safety_guard": "backup"}
_VERIF: dict[str, object] = {"what": "health", "how": "check", "expected": "pass"}


def _high(task_id: str, *, action: str = "migrate") -> Task:
    """High-risk task carrying a rollback (the gate's subject)."""
    return make_task(task_id, action=action, risk_class="high", blast_radius="high", rollback=_RB)


class TestRollbackCredibleGate:
    def test_non_reversible_action_flagged(self) -> None:
        """publish/destroy/commit have no automated inverse — rollback cannot run."""
        plan = make_plan(tasks=[_high("t1", action="publish")])
        findings = [
            f for f in run_deterministic_gates(plan) if f.reason_code == ROLLBACK_UNREACHABLE
        ]
        assert len(findings) == 1
        assert findings[0].severity is Severity.BLOCKER

    def test_reversible_action_clean(self) -> None:
        """Actions with an inverse (or snapshot restore) keep their rollback."""
        for action in ("migrate", "create", "update"):
            plan = make_plan(tasks=[_high("t1", action=action)])
            assert ROLLBACK_UNREACHABLE not in {
                f.reason_code for f in run_deterministic_gates(plan)
            }, action

    def test_self_referential_precondition_flagged(self) -> None:
        """A task established by itself guards a circular basis."""
        task = make_task(
            "t1",
            risk_class="high",
            blast_radius="high",
            rollback=_RB,
            preconditions=[
                {"description": "service healthy", "fact": "healthy", "established_by": "t1"}
            ],
        )
        plan = make_plan(tasks=[task])
        findings = [
            f for f in run_deterministic_gates(plan) if f.reason_code == ROLLBACK_SELF_DEPENDENT
        ]
        assert len(findings) == 1
        assert findings[0].task_id == "t1"

    def test_inconsistent_state_consumer_flagged(self) -> None:
        """Later task's fact basis is this task, yet it cannot verify or undo."""
        consumer = make_task(
            "t2",
            preconditions=[
                {"description": "schema migrated", "fact": "schema_v2", "established_by": "t1"}
            ],
        )
        plan = make_plan(tasks=[_high("t1"), consumer])
        findings = [
            f for f in run_deterministic_gates(plan) if f.reason_code == ROLLBACK_INCONSISTENT_STATE
        ]
        assert len(findings) == 1
        assert findings[0].task_id == "t2"

    def test_post_consumed_window_flagged(self) -> None:
        """Hard-dep consumer inside the write→rollback window, bare."""
        consumer = make_task("t2")
        plan = make_plan(
            tasks=[_high("t1"), consumer],
            dependencies=[hard_dep("t1", "t2")],
        )
        findings = [
            f for f in run_deterministic_gates(plan) if f.reason_code == ROLLBACK_POST_CONSUMED
        ]
        assert len(findings) == 1
        assert findings[0].task_id == "t2"

    def test_verified_consumer_passes(self) -> None:
        """A consumer that verifies re-establishes validity after any restore."""
        consumer = make_task("t2", verification=_VERIF)
        plan = make_plan(
            tasks=[_high("t1"), consumer],
            dependencies=[hard_dep("t1", "t2")],
        )
        codes = {f.reason_code for f in run_deterministic_gates(plan)}
        assert ROLLBACK_POST_CONSUMED not in codes
        assert ROLLBACK_INCONSISTENT_STATE not in codes

    def test_low_risk_producer_out_of_scope(self) -> None:
        """Only high-blast-radius producers are audited."""
        plan = make_plan(
            tasks=[
                make_task("t1", rollback=_RB),
                make_task("t2"),
            ],
            dependencies=[hard_dep("t1", "t2")],
        )
        codes = {f.reason_code for f in run_deterministic_gates(plan)}
        assert not codes & {
            ROLLBACK_UNREACHABLE,
            ROLLBACK_SELF_DEPENDENT,
            ROLLBACK_INCONSISTENT_STATE,
            ROLLBACK_POST_CONSUMED,
        }


class TestGateRegistration:
    def test_gate_registered_after_presence_gate(self) -> None:
        """Joins the pipeline right after rollback_present."""
        from planner_critic.gates import GATES

        names = [g.name for g in GATES]
        assert "rollback_credible" in names
        assert names.index("rollback_credible") == names.index("rollback_present") + 1


class TestBoundaryCases:
    def test_post_consumed_twin_registered(self) -> None:
        """One-fact-diff twin: verified consumer passes, bare consumer blocks."""
        from planner_critic.eval.label_migration import generate_boundary_cases

        cases = {c.case_id: c for c in generate_boundary_cases()}
        case = cases["credible-rollback-vs-post-consumed-window"]
        codes_b = {f.reason_code for f in run_deterministic_gates(case.plan_b)}
        assert ROLLBACK_POST_CONSUMED in codes_b
        codes_a = {f.reason_code for f in run_deterministic_gates(case.plan_a)}
        assert ROLLBACK_POST_CONSUMED not in codes_a
        assert case.expected_reason_code == "rollback_post_consumed"
