"""verification_ordering gate tests (#219).

A high-blast-radius task's verification must be able to mean something: if a
consumer of the mutated state runs before the mutation+verification point
(reversed order) or races it inside the same parallel_group against the same
target, the verification result is vacuous — the consumer acted on state the
verification never got to bless.

Semantics pinned here (inline-after-task): a task's VerificationStep executes
immediately after its own action and before the next linear task begins.
Under those semantics the detectable vacuous cases are exactly:

* reversed order — a hard-dependency consumer positioned before its
  high-risk verified producer;
* parallel race — a same-group, same-target sibling scheduled concurrently
  with the high-risk verified task.
"""

from __future__ import annotations

from conftest import hard_dep, make_plan, make_task
from planner_critic.eval.label_migration import generate_boundary_cases
from planner_critic.gates import run_deterministic_gates
from planner_critic.gates.verification_ordering import Gate as VerificationOrderingGate
from planner_critic.reason_codes import (
    UNSAFE_ORDERING,
    VERIFICATION_AFTER_CONSUMER,
)
from planner_critic.types import Severity

_VERIFIED_HIGH = {
    "trigger": "fail",
    "action": "revert",
    "safety_guard": "backup",
}


def _high_mutate(task_id: str, *, parallel_group: str | None = None):
    """High-risk mutate carrying verification (and rollback)."""
    return make_task(
        task_id,
        risk_class="high",
        blast_radius="high",
        parallel_group=parallel_group,
        verification={"what": "health", "how": "check", "expected": "pass"},
        rollback=_VERIFIED_HIGH,
    )


class TestVerificationOrderingGate:
    def test_consumer_before_verified_mutate_flagged(self) -> None:
        """Consumer listed before its verified high-risk producer is vacuous."""
        plan = make_plan(
            tasks=[make_task("consume"), _high_mutate("deploy")],
            dependencies=[hard_dep("deploy", "consume")],
        )
        findings = [
            f for f in run_deterministic_gates(plan)
            if f.reason_code == VERIFICATION_AFTER_CONSUMER
        ]
        assert len(findings) == 1
        assert findings[0].severity is Severity.BLOCKER
        assert findings[0].task_id == "consume"

    def test_clean_order_passes(self) -> None:
        """Consumer ordered after its verified producer is fine."""
        plan = make_plan(
            tasks=[_high_mutate("deploy"), make_task("consume")],
            dependencies=[hard_dep("deploy", "consume")],
        )
        assert VERIFICATION_AFTER_CONSUMER not in {
            f.reason_code for f in run_deterministic_gates(plan)
        }

    def test_reversed_order_also_trips_ordering_sane(self) -> None:
        """The reversed-order case co-reports with ordering_sane (documented)."""
        plan = make_plan(
            tasks=[make_task("consume"), _high_mutate("deploy")],
            dependencies=[hard_dep("deploy", "consume")],
        )
        codes = {f.reason_code for f in run_deterministic_gates(plan)}
        assert VERIFICATION_AFTER_CONSUMER in codes
        assert UNSAFE_ORDERING in codes

    def test_parallel_sibling_same_target_flagged(self) -> None:
        """Same-group same-target sibling races the verified mutation."""
        plan = make_plan(
            tasks=[
                _high_mutate("deploy", parallel_group="g1"),
                make_task("rotate", target="deploy", parallel_group="g1"),
            ],
        )
        findings = [
            f for f in run_deterministic_gates(plan)
            if f.reason_code == VERIFICATION_AFTER_CONSUMER
        ]
        assert len(findings) == 1
        assert findings[0].task_id == "rotate"

    def test_parallel_sibling_different_target_passes(self) -> None:
        """Same group but disjoint target does not race this task's state."""
        rotate = make_task("rotate", parallel_group="g1")
        plan = make_plan(
            tasks=[_high_mutate("deploy", parallel_group="g1"), rotate],
        )
        assert VERIFICATION_AFTER_CONSUMER not in {
            f.reason_code for f in run_deterministic_gates(plan)
        }

    def test_low_risk_scope_untouched(self) -> None:
        """Low-risk producers are outside this gate's scope."""
        plan = make_plan(
            tasks=[make_task("consume"), make_task("deploy")],
            dependencies=[hard_dep("deploy", "consume")],
        )
        assert VERIFICATION_AFTER_CONSUMER not in {
            f.reason_code for f in run_deterministic_gates(plan)
        }

    def test_unverified_producer_stays_with_presence_gate(self) -> None:
        """Absence of verification is verification_present's job, not ours."""
        from planner_critic.reason_codes import MISSING_VERIFICATION  # noqa: F401

        unverified_high = make_task(
            "deploy",
            risk_class="high",
            blast_radius="high",
            rollback=_VERIFIED_HIGH,
        )
        plan = make_plan(
            tasks=[unverified_high, make_task("consume")],
            dependencies=[hard_dep("deploy", "consume")],
        )
        assert VERIFICATION_AFTER_CONSUMER not in {
            f.reason_code for f in run_deterministic_gates(plan)
        }


class TestGateRegistration:
    def test_gate_registered_in_stable_order(self) -> None:
        """The gate joins the pipeline right after verification_present."""
        from planner_critic.gates import GATES

        names = [g.name for g in GATES]
        assert "verification_ordering" in names
        assert names.index("verification_ordering") == names.index("verification_present") + 1


class TestBoundaryCase:
    def test_boundary_pair_registered(self) -> None:
        """The one-fact-diff twin pair is part of the label-migration corpus."""
        cases = {c.case_id: c for c in generate_boundary_cases()}
        case = cases["verifies-before-consume-vs-consumes-before-verified"]
        assert VerificationOrderingGate().run(case.plan_b), (
            "plan_b must be blocked by verification_ordering"
        )
        assert not VerificationOrderingGate().run(case.plan_a)
        assert case.expected_reason_code == "verification_after_consumer"
