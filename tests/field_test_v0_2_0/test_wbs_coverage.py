"""WBS coverage test cases for v0.2.0 field test (§4.8).

Deterministic (No-LLM) test scenarios derived from the WBS M1–M8 gap
analysis. LLM-required tests are marked with @pytest.mark.llm and skipped
unless --run-llm is passed.

Run deterministic tests only:
    pytest tests/field_test_v0_2_0/ -v

Run all tests (including LLM):
    pytest tests/field_test_v0_2_0/ -v --run-llm

Benchmarks (standalone scripts):
    python3 docs/field-test/v0.2.0/scripts/bench_auto_repair.py
    python3 docs/field-test/v0.2.0/scripts/bench_rollback.py
    python3 docs/field-test/v0.2.0/scripts/bench_stasis.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
import yaml

from conftest import EmptyCritic, ScriptedPlanner, hard_dep, make_goal, make_plan, make_task
from planner_critic.domains.base import pack_from_dict, find_domain_packs
from planner_critic.domains.secops.gates import BlastRadiusGate
from planner_critic.drift import compute_drift, compute_drift_summary
from planner_critic.eval.label_migration import IrreversibleInvariantGate, generate_boundary_cases
from planner_critic.eval.standing_rules import StandingRuleRegistry
from planner_critic.gates import run_deterministic_gates
from planner_critic.guardrail import EscalationRequired, PreconditionDrift, re_gate, escalate
from planner_critic.loop import LoopConfig, run_loop
from planner_critic.loop.autofix import apply_precondition_closer
from planner_critic.loop.oscillation import compute_plan_signature, detect_oscillation
from planner_critic.notifier import Notifier, SlackFormatter, EscalationEvent
from planner_critic.policy import CelGate
from planner_critic.quota import BlastRadiusQuotaConfig, BlastRadiusQuotaGate
from planner_critic.reason_codes import ReasonCode
from planner_critic.redaction import SecretsRedactor, RedactMode
from planner_critic.rollback_synth import InverseRollbackSynthesizer
from planner_critic.schema.goal import RiskTolerance
from planner_critic.schema.plan import PlanVersion, Task
from planner_critic.state import StateLock, LockStrategy
from planner_critic.types import Finding, Severity


def _task(tid: str, action: str = "do", **kw: object) -> Task:
    """Build a task with a custom action (conftest.make_task doesn't accept action)."""
    data = {"id": tid, "description": f"task {tid}", "action": action, "target": tid,
            "risk_class": kw.get("risk_class", "medium"), "blast_radius": kw.get("blast_radius", "medium")}
    for k in ("verification", "rollback", "parallel_group", "preconditions"):
        if k in kw:
            data[k] = kw[k]  # type: ignore[assignment]
    return Task.model_validate(data)


def _finding(reason_code: str, severity: Severity = Severity.BLOCKER, task_id: str | None = None) -> Finding:
    return Finding(id=f"f:{reason_code}", task_id=task_id, version=1, severity=severity,
                   reason_code=cast(ReasonCode, reason_code), message=reason_code)


GOALS_DIR = Path(__file__).parent.parent.parent / "docs" / "field-test" / "goals"


# ── M1: Positive Control ──────────────────────────────────────────────────


class TestM1PositiveControl:
    """M1-8: Known-clean golden plan through strict with all 4 packs — 0 false positives."""

    def test_clean_plan_strict_no_false_positives(self):
        from planner_critic.domains.secops import SecOpsDomainPack
        from planner_critic.domains.supply_chain import SupplyChainDomainPack
        from planner_critic.domains.finops import FinOpsDomainPack
        from planner_critic.domains.data_eng import DataEngineeringDomainPack

        clean_plan = make_plan(tasks=[
            _task("t1", risk_class="low", blast_radius="low",
                  verification={"what": "check", "how": "manual", "expected": "ok"},
                  rollback={"trigger": "fail", "action": "noop", "safety_guard": "none"}),
        ])
        for pack_cls in [SecOpsDomainPack, SupplyChainDomainPack, FinOpsDomainPack, DataEngineeringDomainPack]:
            pack = pack_cls()
            for gate in pack.gate_evaluators:
                findings = gate.run(clean_plan)
                assert not any(f.severity is Severity.BLOCKER for f in findings), \
                    f"{pack.name}/{gate.name} false positive on clean plan"


# ── M2: Loop Efficiency Edge Cases ─────────────────────────────────────────


class TestM2CloserScopeGuard:
    """M2-1: Precondition closer only fires on unverified_precondition."""

    def test_unsafe_sequencing_not_auto_closed(self):
        plan = make_plan(tasks=[_task("A"), _task("B")])
        findings = [_finding("unsafe_ordering", task_id="B")]
        closed, _ = apply_precondition_closer(plan, findings)
        assert closed is None, "closer must NOT fire on unsafe_ordering"


class TestM2OscillationKWindow:
    """M2-2: Oscillation K-window sensitivity."""

    def test_cycle_2_detected_at_k4(self):
        """Cycle of length 2 needs window >= 4 to see the repeat."""
        assert detect_oscillation(["a", "b", "a", "b"], window=4) is True

    def test_cycle_3_detected_at_k5(self):
        """Cycle of length 3 needs window >= 5 to see the repeat."""
        assert detect_oscillation(["a", "b", "c", "a", "b", "c"], window=5) is True

    def test_no_false_positive_converging(self):
        sigs = ["a", "b", "c", "d"]
        assert detect_oscillation(sigs, window=2) is False
        assert detect_oscillation(sigs, window=4) is False

    def test_k_too_small_for_cycle(self):
        """Window=2 can't see a cycle of length 2 (needs 2x length)."""
        assert detect_oscillation(["a", "b", "a", "b"], window=2) is False


# ── M3: Extensibility Framework ────────────────────────────────────────────


class TestM3CelGate:
    """M3-1: CEL policy engine without OPA binary."""

    def test_cel_fires_on_violation(self):
        gate = CelGate(name="must_have_tasks", expression="len(tasks) > 0", severity="blocker")
        plan = make_plan(tasks=[])
        findings = gate.evaluate(plan)
        assert len(findings) == 1
        assert findings[0].severity is Severity.BLOCKER

    def test_cel_passes_on_clean(self):
        gate = CelGate(name="must_have_tasks", expression="len(tasks) > 0")
        plan = make_plan(tasks=[_task("t1")])
        assert len(gate.evaluate(plan)) == 0

    def test_cel_additive_to_built_in(self):
        plan = make_plan(tasks=[_task("t1", risk_class="critical", blast_radius="high")])
        built_in = run_deterministic_gates(plan)
        cel = CelGate(name="extra", expression="len(tasks) > 0").evaluate(plan)
        assert len(built_in) > 0
        assert len(cel) == 0


class TestM3PytestPlugin:
    """M3-2: pytest-planner-critic plugin."""

    def test_plugin_imports(self):
        from planner_critic.pytest_plugin import assert_gate_fails, assert_gate_passes
        assert callable(assert_gate_fails)
        assert callable(assert_gate_passes)

    def test_assert_gate_passes_on_clean(self):
        from planner_critic.gates import GATES
        from planner_critic.pytest_plugin import assert_gate_passes
        plan = make_plan(tasks=[_task("t1", risk_class="low")])
        ordering_gate = [g for g in GATES if g.name == "ordering_sane"][0]
        assert_gate_passes(ordering_gate, plan)

    def test_assert_gate_fails_on_flawed(self):
        from planner_critic.gates import GATES
        from planner_critic.pytest_plugin import assert_gate_fails
        plan = make_plan(tasks=[_task("C"), _task("A")], dependencies=[hard_dep("A", "C")])
        ordering_gate = [g for g in GATES if g.name == "ordering_sane"][0]
        assert_gate_fails(ordering_gate, plan)


class TestM3ManifestLoading:
    """M3-3: DomainPack manifest loading round-trip."""

    def test_pack_from_dict(self):
        manifest = {
            "name": "test-pack", "gates": [],
            "preconditions": {"db_healthy": "Database is healthy"},
            "critic_prompt": "Audit from test-pack perspective.",
            "config": {"threshold": 5},
        }
        pack = pack_from_dict(manifest)
        assert pack.name == "test-pack"
        assert pack.pack_config == {"threshold": 5}

    def test_find_domain_packs(self):
        """Packs are importable classes (discovery via namespace scan requires domain_pack attribute)."""
        from planner_critic.domains.secops import SecOpsDomainPack
        from planner_critic.domains.supply_chain import SupplyChainDomainPack
        from planner_critic.domains.finops import FinOpsDomainPack
        from planner_critic.domains.data_eng import DataEngineeringDomainPack
        packs = [SecOpsDomainPack(), SupplyChainDomainPack(), FinOpsDomainPack(), DataEngineeringDomainPack()]
        names = [p.name for p in packs]
        assert "secops" in names
        assert "supply_chain" in names
        assert "finops" in names
        assert "data_eng" in names


# ── M4: Domain Packs + Rollback ────────────────────────────────────────────


class TestM4RollbackSynth:
    """M4-2: Rollback synthesizer DAG."""

    def test_rollback_reverses_edges(self):
        plan = make_plan(tasks=[_task("a"), _task("b"), _task("c")],
                         dependencies=[hard_dep("b", "a"), hard_dep("c", "b")])
        synth = InverseRollbackSynthesizer()
        rollback = synth.build_rollback(plan)
        assert rollback is not None
        assert len(rollback.tasks) == 3
        assert all(t.id.startswith("rollback:") for t in rollback.tasks)

    def test_non_reversible_emits_noop(self):
        plan = make_plan(tasks=[_task("x", action="custom_op")])
        synth = InverseRollbackSynthesizer()
        synth.build_rollback(plan)
        codes = {f.reason_code for f in synth.trace}
        assert "rollback_non_reversible_step_skipped" in codes

    def test_known_reversible(self):
        plan = make_plan(tasks=[_task("x", action="create")])
        synth = InverseRollbackSynthesizer()
        rollback = synth.build_rollback(plan)
        rb = [t for t in rollback.tasks if t.id == "rollback:x"][0]
        assert rb.action != "sys.noop"


class TestM4PartialRollback:
    """M4-3: Partial rollback."""

    def test_partial_rollback_all_steps(self):
        plan = make_plan(tasks=[_task(f"s{i}") for i in range(5)])
        synth = InverseRollbackSynthesizer()
        rollback = synth.build_rollback(plan)
        assert len(rollback.tasks) == 5


class TestM4SecOpsGates:
    """M4-1: BlastRadiusGate drain ordering (validates #198 fix)."""

    def test_isolation_before_drain_fires(self):
        plan = make_plan(tasks=[_task("i1", action="isolate"), _task("d1", action="drain")])
        findings = BlastRadiusGate().run(plan)
        assert len(findings) == 1
        assert findings[0].reason_code == "secops_isolation_without_traffic_drain"

    def test_drain_before_isolation_passes(self):
        plan = make_plan(tasks=[_task("d1", action="drain"), _task("i1", action="isolate")])
        assert len(BlastRadiusGate().run(plan)) == 0

    def test_isolation_without_drain_fires(self):
        plan = make_plan(tasks=[_task("i1", action="isolate")])
        assert len(BlastRadiusGate().run(plan)) == 1


# ── M5: Security Oracle Sub-behaviors ───────────────────────────────────────


class TestM5StandingRules:
    """M5-1: Standing-rule trust tiering + dedup."""

    def test_registry_importable(self):
        reg = StandingRuleRegistry()
        assert reg is not None

    def test_boundary_cases(self):
        cases = generate_boundary_cases()
        assert len(cases) >= 2
        for c in cases:
            assert c.case_id
            assert c.plan_a is not None
            assert c.plan_b is not None

    def test_invariant_fires_on_missing_precondition(self):
        task = Task.model_validate({
            "id": "t1", "description": "critical", "action": "alter", "target": "db",
            "risk_class": "critical", "blast_radius": "high",
            "rollback": {"trigger": "fail", "action": "revert", "safety_guard": "backup"},
            "verification": {"what": "check", "how": "manual", "expected": "pass"},
        })
        plan = PlanVersion(id="p1", goal_id="g1", version=1, tasks=[task])
        findings = IrreversibleInvariantGate().run(plan)
        assert len(findings) == 1

    def test_invariant_passes_with_precondition(self):
        task = Task.model_validate({
            "id": "t1", "description": "critical", "action": "alter", "target": "db",
            "risk_class": "critical", "blast_radius": "high",
            "rollback": {"trigger": "fail", "action": "revert", "safety_guard": "backup"},
            "verification": {"what": "check", "how": "manual", "expected": "pass"},
            "preconditions": [{"description": "backup", "fact": "backup", "established_by": "env:backup"}],
        })
        plan = PlanVersion(id="p1", goal_id="g1", version=1, tasks=[task])
        assert len(IrreversibleInvariantGate().run(plan)) == 0


# ── M6: Enterprise Safety ──────────────────────────────────────────────────


class TestM6RedactorModes:
    """M6-4: Redactor hash/skip/custom (validates #184, #185 fixes)."""

    def test_hash_mode_deterministic(self):
        r = SecretsRedactor(mode=RedactMode.HASH)
        assert r.redact("key=AKIAIOSFODNN7EXAMPLE") == r.redact("key=AKIAIOSFODNN7EXAMPLE")

    def test_skip_mode_no_redact(self):
        r = SecretsRedactor(mode=RedactMode.SKIP)
        assert r.redact("key=AKIAIOSFODNN7EXAMPLE") == "key=AKIAIOSFODNN7EXAMPLE"

    def test_custom_regex(self):
        r = SecretsRedactor()
        r.add_custom_pattern("internal_token", r"INT-[a-z0-9]+")
        result = r.redact("token=INT-abc123 here")
        assert "INT-abc123" not in result

    def test_offset_not_corrupted(self):
        r = SecretsRedactor()
        text = "key1=AKIAIOSFODNN7EXAMPLE key2=AKIAIOSFODNN7EXAMPLE"
        result = r.redact(text)
        assert "AKIA" not in result
        assert result.count("[REDACTED_SECRET]") == 2


class TestM6QuotaPosture:
    """M6-5: Quota-posture 2×2 matrix (validates #193 fix)."""

    def test_strict_quota_blocker(self):
        config = BlastRadiusQuotaConfig(max_resource_changes=1)
        gate = BlastRadiusQuotaGate(config, posture=RiskTolerance.STRICT)
        plan = make_plan(tasks=[_task("t1"), _task("t2")])
        assert any(f.severity is Severity.BLOCKER for f in gate.run(plan))

    def test_permissive_quota_breach_still_blocks(self):
        """Quota breach always produces BLOCKER (resource safety, not posture-dependent)."""
        config = BlastRadiusQuotaConfig(max_resource_changes=1)
        gate = BlastRadiusQuotaGate(config, posture=RiskTolerance.PERMISSIVE)
        plan = make_plan(tasks=[_task("t1"), _task("t2")])
        findings = gate.run(plan)
        assert any(f.severity is Severity.BLOCKER for f in findings), \
            "quota breach must always block regardless of posture"

    def test_restricted_exact_match_not_substring(self):
        config = BlastRadiusQuotaConfig(restricted_actions=["deploy"])
        gate = BlastRadiusQuotaGate(config, posture=RiskTolerance.STRICT)
        plan = make_plan(tasks=[_task("t1", action="undeploy")])
        assert not any(f.severity is Severity.BLOCKER for f in gate.run(plan))


class TestM6StateLock:
    """M6-3: StateLock WAIT strategy (validates #195 fix)."""

    def test_wait_times_out(self):
        lock = StateLock(strategy=LockStrategy.WAIT, wait_deadline=0.1)
        lock.acquire("res-1", "plan-1")
        result = lock.acquire("res-1", "plan-2")
        assert result == "resource_locked_by_concurrent_execution"

    def test_fail_fast(self):
        lock = StateLock(strategy=LockStrategy.FAIL_FAST)
        lock.acquire("res-1", "plan-1")
        assert lock.acquire("res-1", "plan-2") == "concurrent_resource_conflict"

    def test_escalate(self):
        lock = StateLock(strategy=LockStrategy.ESCALATE)
        lock.acquire("res-1", "plan-1")
        assert lock.acquire("res-1", "plan-2") == "resource_locked_by_concurrent_execution"


# ── M7: Developer Surfaces — Decorators ─────────────────────────────────────


class TestM7Decorators:
    """M7-4/5/6: @guardrail, @re_gate, @escalate (validates #187 fix)."""

    def test_re_gate_calls_func_with_satisfied_ledger(self):
        called: list[bool] = []

        class FakeLedger:
            def read(self, key):
                return {"satisfied": True}

        @re_gate(precondition_key="k", ledger=FakeLedger())
        def step():
            called.append(True)
            return "ok"

        assert step() == "ok"
        assert called == [True]

    def test_re_gate_raises_on_drift_with_ledger(self):
        class FakeLedger:
            def read(self, key):
                return {"satisfied": False}

        @re_gate(precondition_key="k", ledger=FakeLedger())
        def step():
            return "ok"

        with pytest.raises(PreconditionDrift):
            step()

    def test_re_gate_no_ledger_raises(self):
        @re_gate(precondition_key="db_healthy")
        def step():
            return "ok"

        with pytest.raises(PreconditionDrift):
            step()

    def test_re_gate_no_ledger_on_drift_callback(self):
        keys: list[str] = []

        def on_drift(key):
            keys.append(key)
            return "handled"

        @re_gate(precondition_key="auth", on_drift=on_drift)
        def step():
            return "ok"

        assert step() == "handled"
        assert "auth" in keys

    def test_escalate_passes_through(self):
        def handler(reason):
            return f"handled: {reason}"
        decorated = escalate(handler)
        assert decorated is handler
        assert decorated("test") == "handled: test"

    def test_escalate_requires_handler(self):
        with pytest.raises(TypeError):
            escalate()


# ── M8: Integration — Notifier + Drift ──────────────────────────────────────


class TestM8Notifier:
    """M8-3: Notifier dedup + signing_secret (validates #203, #210)."""

    def test_dedup_within_ttl(self):
        notifier = Notifier()
        event = EscalationEvent(
            escalation_id="e1", plan_id="p1", reason_code="test", question="what?")
        r1 = notifier.dispatch(event)
        r2 = notifier.dispatch(event)
        assert r2 == []

    def test_empty_secret_rejects(self):
        formatter = SlackFormatter("https://hooks.slack.com/test", signing_secret="")
        assert formatter.verify_signature("123", "body", "sig") is False

    def test_valid_secret_verifies(self):
        import hashlib
        import hmac
        import time
        secret = "test_secret"
        fmt = SlackFormatter("https://hooks.slack.com/test", signing_secret=secret)
        ts = str(int(time.time()))
        body = "test"
        sig = "v0=" + hmac.new(secret.encode(), f"v0:{ts}:{body}".encode(), hashlib.sha256).hexdigest()
        assert fmt.verify_signature(ts, body, sig) is True


class TestM8Drift:
    """M8-1: Drift metrics (validates #194 fix)."""

    def test_downgrade_rate_excludes_upgrades(self):
        f1 = _finding("missing_rollback", Severity.WARNING)
        f1 = f1.model_copy(update={"raw_severity": Severity.BLOCKER, "normalized_severity": Severity.WARNING, "drift_delta": -1})
        f2 = _finding("missing_rollback", Severity.BLOCKER)
        f2 = f2.model_copy(update={"raw_severity": Severity.WARNING, "normalized_severity": Severity.BLOCKER, "drift_delta": 1})
        summary = compute_drift_summary([f1, f2])
        assert summary["downgrade_rate"] == 0.5, f"expected 0.5, got {summary['downgrade_rate']}"

    def test_underclaims_excludes_non_downgraded(self):
        f1 = _finding("missing_rollback", Severity.BLOCKER)
        f1 = f1.model_copy(update={"raw_severity": Severity.BLOCKER, "normalized_severity": Severity.BLOCKER, "drift_delta": 0})
        summary = compute_drift_summary([f1])
        assert summary["critical_underclaims"] == 0, f"expected 0, got {summary['critical_underclaims']}"


# ── P0: Pre-run Assertion Validation ─────────────────────────────────────────


class TestP0AssertionValidation:
    """P0: Validate all 170 assertion YAMLs before running LLM tests."""

    def test_all_goals_have_assertions(self):
        missing = []
        for gfile in sorted(GOALS_DIR.rglob("*.json")):
            astub = gfile.relative_to(GOALS_DIR)
            afile = GOALS_DIR / astub.parent / "assertions" / (astub.stem + ".yaml")
            if not afile.exists():
                missing.append(str(afile))
        assert not missing, f"Missing assertions: {missing}"

    def test_all_assertions_have_invariants(self):
        for afile in sorted(GOALS_DIR.rglob("assertions/*.yaml")):
            data = yaml.safe_load(afile.read_text())
            assert isinstance(data, dict), f"{afile} not dict"
            assert "invariants" in data, f"{afile} missing invariants"

    def test_no_strict_goal_approve_expected_true(self):
        for gfile in sorted(GOALS_DIR.rglob("*.json")):
            goal = json.loads(gfile.read_text())
            if goal.get("risk_tolerance") != "strict":
                continue
            astub = gfile.relative_to(GOALS_DIR)
            afile = GOALS_DIR / astub.parent / "assertions" / (astub.stem + ".yaml")
            if not afile.exists():
                continue
            data = yaml.safe_load(afile.read_text())
            ae = data.get("invariants", {}).get("approve_expected")
            assert ae is not True, f"{afile}: strict goal with approve_expected=true"

    def test_no_duplicate_ir07(self):
        ir07 = list(GOALS_DIR.glob("incident-response/ir-07-*"))
        assert len(ir07) == 1, f"Expected 1 ir-07, found {len(ir07)}"
