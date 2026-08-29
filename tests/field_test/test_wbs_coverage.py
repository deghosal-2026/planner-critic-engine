"""WBS coverage test cases for v0.2.0 field test (§4.8).

All tests here are deterministic (No-LLM). LLM-required tests are in
run-field.py only.

Run:
    pytest tests/field_test_v0_2_0/ -v --no-cov
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
import yaml

from conftest import hard_dep, make_plan
from planner_critic.domains.base import DomainPack, pack_from_dict
from planner_critic.domains.secops.gates import BlastRadiusGate
from planner_critic.drift import compute_drift_summary
from planner_critic.eval.label_migration import IrreversibleInvariantGate, generate_boundary_cases
from planner_critic.eval.standing_rules import StandingRuleRegistry
from planner_critic.gates import run_deterministic_gates
from planner_critic.guardrail import PreconditionDrift, escalate, re_gate
from planner_critic.loop import CriticMode, LoopConfig
from planner_critic.loop.autofix import SEED_TEMPLATES, apply_precondition_closer
from planner_critic.loop.oscillation import compute_plan_signature, detect_oscillation
from planner_critic.notifier import EscalationEvent, Notifier, SlackFormatter
from planner_critic.policy import CelGate
from planner_critic.quota import BlastRadiusQuotaConfig, BlastRadiusQuotaGate
from planner_critic.reason_codes import ReasonCode
from planner_critic.redaction import RedactMode, SecretsRedactor
from planner_critic.rollback_synth import InverseRollbackSynthesizer
from planner_critic.schema.goal import RiskTolerance
from planner_critic.schema.plan import PlanVersion, Task
from planner_critic.state import LockStrategy, StateLock, StateSnapshot, StateView
from planner_critic.types import Finding, Severity

GOALS_DIR = Path(__file__).parent.parent.parent / "docs" / "field-test" / "goals"


def _task(tid: str, action: str = "do", **kw: object) -> Task:
    data = {
        "id": tid,
        "description": f"task {tid}",
        "action": action,
        "target": tid,
        "risk_class": kw.get("risk_class", "medium"),
        "blast_radius": kw.get("blast_radius", "medium"),
    }
    for k in ("verification", "rollback", "parallel_group", "preconditions"):
        if k in kw:
            data[k] = kw[k]
    return Task.model_validate(data)


def _finding(
    reason_code: str, severity: Severity = Severity.BLOCKER, task_id: str | None = None
) -> Finding:
    return Finding(
        id=f"f:{reason_code}",
        task_id=task_id,
        version=1,
        severity=severity,
        reason_code=cast(ReasonCode, reason_code),
        message=reason_code,
    )


# ── M1: Positive Control ──────────────────────────────────────────────────


class TestM1PositiveControl:
    """M1-8: Known-clean golden plan through strict with all 4 packs — 0 false positives."""

    def test_clean_plan_strict_no_false_positives(self) -> None:
        from planner_critic.domains.data_eng import DataEngineeringDomainPack
        from planner_critic.domains.finops import FinOpsDomainPack
        from planner_critic.domains.secops import SecOpsDomainPack
        from planner_critic.domains.supply_chain import SupplyChainDomainPack

        clean_plan = make_plan(
            tasks=[
                _task(
                    "t1",
                    risk_class="low",
                    blast_radius="low",
                    verification={"what": "check", "how": "manual", "expected": "ok"},
                    rollback={"trigger": "fail", "action": "noop", "safety_guard": "none"},
                ),
            ]
        )
        packs = cast(
            "list[DomainPack]",
            [
                SecOpsDomainPack(),
                SupplyChainDomainPack(),
                FinOpsDomainPack(),
                DataEngineeringDomainPack(),
            ],
        )
        for pack in packs:
            for gate in pack.gate_evaluators:
                findings = gate.run(clean_plan)
                assert not any(f.severity is Severity.BLOCKER for f in findings), (
                    f"{pack.name}/{gate.name} false positive on clean plan"
                )


class TestM1Adapters:
    """M1-3: All adapters importable and functional."""

    def test_all_adapters_importable(self) -> None:
        """All adapter modules import cleanly (#236: restored from vacuous `pass`)."""
        import importlib

        adapter_modules = [
            "planner_critic.adapters.python",
            "planner_critic.adapters.crewai",
            "planner_critic.adapters.langgraph",
            "planner_critic.adapters.openai_agents",
            "planner_critic.adapters.pydantic_ai",
            "planner_critic.adapters.autogen",
        ]
        for module_name in adapter_modules:
            importlib.import_module(module_name)

    def test_python_adapter_plan_method_exists(self) -> None:
        from planner_critic.adapters.python import PlannerCriticPlan

        assert hasattr(PlannerCriticPlan, "plan")


class TestM1CritiqueModes:
    """M1-4: All three critique modes exist."""

    @pytest.mark.parametrize(
        "mode", ["heuristic-only", "deterministic-first", "llm-every-revision"]
    )
    def test_mode_configurable(self, mode: CriticMode) -> None:
        config = LoopConfig(mode=mode)
        assert config.mode == mode


class TestM1Concurrency:
    """M1-5: StateLock concurrency."""

    def test_concurrent_lock_blocks(self) -> None:
        lock = StateLock(strategy=LockStrategy.ESCALATE)
        lock.acquire("res-1", "plan-1")
        result = lock.acquire("res-1", "plan-2")
        assert result == "resource_locked_by_concurrent_execution"

    def test_store_no_corruption(self) -> None:
        from planner_critic.store.sqlite import SQLiteStore

        store = SQLiteStore(":memory:")
        plan = make_plan()
        store.put_plan_version(plan)
        retrieved = store.get_plan(plan.id, plan.version)
        assert retrieved is not None
        assert retrieved.id == plan.id


class TestM1FindingQuality:
    """M1-6: Finding quality — specific, not noise."""

    def test_findings_reference_real_tasks(self) -> None:
        plan = make_plan(tasks=[_task("t1", risk_class="critical", blast_radius="high")])
        findings = run_deterministic_gates(plan)
        for f in findings:
            if f.task_id:
                assert f.task_id in [t.id for t in plan.tasks], (
                    f"Finding references unknown task {f.task_id}"
                )

    def test_no_empty_reason_codes(self) -> None:
        plan = make_plan(tasks=[_task("t1", risk_class="low")])
        findings = run_deterministic_gates(plan)
        for f in findings:
            assert cast(str, f.reason_code) != "", "Finding has empty reason_code"


class TestM1FailureShapeClustering:
    """M1-7: Failure shapes are taggable via reason_code."""

    def test_findings_have_reason_codes(self) -> None:
        plan = make_plan(tasks=[_task("t1", risk_class="critical", blast_radius="high")])
        findings = run_deterministic_gates(plan)
        shapes = {f.reason_code for f in findings}
        assert len(shapes) > 0, "No findings to cluster"


class TestM1HTTPMCP:
    """M1-2: HTTP + MCP surface importable."""

    def test_http_server_importable(self) -> None:
        from planner_critic.server.http import PlannerCriticHTTPServer

        assert PlannerCriticHTTPServer is not None

    def test_mcp_server_importable(self) -> None:
        from planner_critic.server.mcp import PlannerCriticMCPServer

        assert PlannerCriticMCPServer is not None


class TestM1CLI:
    """M1-1: CLI parsers exist."""

    def test_cli_parsers_importable(self) -> None:
        from planner_critic.cli.migrate import build_migrate_parser
        from planner_critic.cli.plan import build_plan_parser
        from planner_critic.cli.replay import build_replay_parser

        assert all([build_plan_parser, build_replay_parser, build_migrate_parser])


# ── M2: Loop Efficiency Edge Cases ─────────────────────────────────────────


class TestM2CloserScopeGuard:
    """M2-1: Precondition closer only fires on unverified_precondition."""

    def test_unsafe_ordering_not_auto_closed(self) -> None:
        plan = make_plan(tasks=[_task("A"), _task("B")])
        findings = [_finding("unsafe_ordering", task_id="B")]
        closed, _ = apply_precondition_closer(plan, findings)
        assert closed is None, "closer must NOT fire on unsafe_ordering"


class TestM2OscillationKWindow:
    """M2-2: Oscillation K-window sensitivity."""

    def test_cycle_2_detected_at_k4(self) -> None:
        assert detect_oscillation(["a", "b", "a", "b"], window=4) is True

    def test_cycle_3_detected_at_k5(self) -> None:
        assert detect_oscillation(["a", "b", "c", "a", "b", "c"], window=5) is True

    def test_no_false_positive_converging(self) -> None:
        sigs = ["a", "b", "c", "d"]
        assert detect_oscillation(sigs, window=2) is False
        assert detect_oscillation(sigs, window=4) is False

    def test_k_too_small_for_cycle(self) -> None:
        assert detect_oscillation(["a", "b", "a", "b"], window=2) is False


# ── M3: Extensibility Framework ────────────────────────────────────────────


class TestM3CelGate:
    """M3-1: CEL policy engine without OPA binary."""

    def test_cel_fires_on_violation(self) -> None:
        gate = CelGate(name="must_have_tasks", expression="len(tasks) > 0", severity="blocker")
        plan = make_plan(tasks=[])
        findings = gate.evaluate(plan)
        assert len(findings) == 1
        assert findings[0].severity is Severity.BLOCKER

    def test_cel_passes_on_clean(self) -> None:
        gate = CelGate(name="must_have_tasks", expression="len(tasks) > 0")
        plan = make_plan(tasks=[_task("t1")])
        assert len(gate.evaluate(plan)) == 0

    def test_cel_additive_to_built_in(self) -> None:
        plan = make_plan(tasks=[_task("t1", risk_class="critical", blast_radius="high")])
        built_in = run_deterministic_gates(plan)
        cel = CelGate(name="extra", expression="len(tasks) > 0").evaluate(plan)
        assert len(built_in) > 0
        assert len(cel) == 0


class TestM3PytestPlugin:
    """M3-2: pytest-planner-critic plugin."""

    def test_plugin_imports(self) -> None:
        from planner_critic.pytest_plugin import assert_gate_fails, assert_gate_passes

        assert callable(assert_gate_fails)
        assert callable(assert_gate_passes)

    def test_assert_gate_passes_on_clean(self) -> None:
        from planner_critic.gates import GATES
        from planner_critic.pytest_plugin import assert_gate_passes

        plan = make_plan(tasks=[_task("t1", risk_class="low")])
        ordering_gate = next(g for g in GATES if g.name == "ordering_sane")
        assert_gate_passes(ordering_gate, plan)

    def test_assert_gate_fails_on_flawed(self) -> None:
        from planner_critic.gates import GATES
        from planner_critic.pytest_plugin import assert_gate_fails

        plan = make_plan(tasks=[_task("C"), _task("A")], dependencies=[hard_dep("A", "C")])
        ordering_gate = next(g for g in GATES if g.name == "ordering_sane")
        assert_gate_fails(ordering_gate, plan)


class TestM3ManifestLoading:
    """M3-3: DomainPack manifest loading round-trip."""

    def test_pack_from_dict(self) -> None:
        manifest = {
            "name": "test-pack",
            "gates": [],
            "preconditions": {"db_healthy": "Database is healthy"},
            "critic_prompt": "Audit from test-pack perspective.",
            "config": {"threshold": 5},
        }
        pack = pack_from_dict(manifest)
        assert pack.name == "test-pack"
        assert pack.pack_config == {"threshold": 5}

    def test_find_domain_packs(self) -> None:
        from planner_critic.domains.data_eng import DataEngineeringDomainPack
        from planner_critic.domains.finops import FinOpsDomainPack
        from planner_critic.domains.secops import SecOpsDomainPack
        from planner_critic.domains.supply_chain import SupplyChainDomainPack

        packs = cast(
            "list[DomainPack]",
            [
                SecOpsDomainPack(),
                SupplyChainDomainPack(),
                FinOpsDomainPack(),
                DataEngineeringDomainPack(),
            ],
        )
        names = [p.name for p in packs]
        assert "secops" in names
        assert "supply_chain" in names
        assert "finops" in names
        assert "data_eng" in names


# ── M4: Domain Packs + Rollback ────────────────────────────────────────────


class TestM4RollbackSynth:
    """M4-2: Rollback synthesizer DAG."""

    def test_rollback_reverses_edges(self) -> None:
        plan = make_plan(
            tasks=[_task("a"), _task("b"), _task("c")],
            dependencies=[hard_dep("b", "a"), hard_dep("c", "b")],
        )
        synth = InverseRollbackSynthesizer()
        rollback = synth.build_rollback(plan)
        assert rollback is not None
        assert len(rollback.tasks) == 3
        assert all(t.id.startswith("rollback:") for t in rollback.tasks)

    def test_non_reversible_emits_noop(self) -> None:
        plan = make_plan(tasks=[_task("x", action="custom_op")])
        synth = InverseRollbackSynthesizer()
        synth.build_rollback(plan)
        codes = {f.reason_code for f in synth.trace}
        assert "rollback_non_reversible_step_skipped" in codes

    def test_known_reversible(self) -> None:
        plan = make_plan(tasks=[_task("x", action="create")])
        synth = InverseRollbackSynthesizer()
        rollback = synth.build_rollback(plan)
        rb = next(t for t in rollback.tasks if t.id == "rollback:x")
        assert rb.action != "sys.noop"


class TestM4PartialRollback:
    """M4-3: Partial rollback."""

    def test_partial_rollback_all_steps(self) -> None:
        plan = make_plan(tasks=[_task(f"s{i}") for i in range(5)])
        synth = InverseRollbackSynthesizer()
        rollback = synth.build_rollback(plan)
        assert len(rollback.tasks) == 5


class TestM4SecOpsGates:
    """M4-1: BlastRadiusGate drain ordering (validates #198 fix)."""

    def test_isolation_before_drain_fires(self) -> None:
        plan = make_plan(tasks=[_task("i1", action="isolate"), _task("d1", action="drain")])
        findings = BlastRadiusGate().run(plan)
        assert len(findings) == 1
        assert findings[0].reason_code == "secops_isolation_without_traffic_drain"

    def test_drain_before_isolation_passes(self) -> None:
        plan = make_plan(tasks=[_task("d1", action="drain"), _task("i1", action="isolate")])
        assert len(BlastRadiusGate().run(plan)) == 0

    def test_isolation_without_drain_fires(self) -> None:
        plan = make_plan(tasks=[_task("i1", action="isolate")])
        assert len(BlastRadiusGate().run(plan)) == 1


class TestM4InitTemplate:
    """M4-1: init --template scaffolding."""

    def test_init_parser_exists(self) -> None:
        from planner_critic.cli.init import build_init_parser

        assert build_init_parser() is not None

    def test_templates_list(self) -> None:
        from planner_critic.cli.init import build_init_parser

        parser = build_init_parser()
        args = parser.parse_args(["--list-templates"])
        assert args.list_templates is True


# ── M5: Security Oracle Sub-behaviors ───────────────────────────────────────


class TestM5StandingRules:
    """M5-1: Standing-rule trust tiering + dedup."""

    def test_registry_importable(self) -> None:
        reg = StandingRuleRegistry()
        assert reg is not None

    def test_boundary_cases(self) -> None:
        cases = generate_boundary_cases()
        assert len(cases) >= 2
        for c in cases:
            assert c.case_id
            assert c.plan_a is not None
            assert c.plan_b is not None

    def test_invariant_fires_on_missing_precondition(self) -> None:
        task = Task.model_validate(
            {
                "id": "t1",
                "description": "critical",
                "action": "alter",
                "target": "db",
                "risk_class": "critical",
                "blast_radius": "high",
                "rollback": {"trigger": "fail", "action": "revert", "safety_guard": "backup"},
                "verification": {"what": "check", "how": "manual", "expected": "pass"},
            }
        )
        plan = PlanVersion(id="p1", goal_id="g1", version=1, tasks=[task])
        findings = IrreversibleInvariantGate().run(plan)
        assert len(findings) == 1

    def test_invariant_passes_with_precondition(self) -> None:
        task = Task.model_validate(
            {
                "id": "t1",
                "description": "critical",
                "action": "alter",
                "target": "db",
                "risk_class": "critical",
                "blast_radius": "high",
                "rollback": {"trigger": "fail", "action": "revert", "safety_guard": "backup"},
                "verification": {"what": "check", "how": "manual", "expected": "pass"},
                "preconditions": [
                    {"description": "backup", "fact": "backup", "established_by": "env:backup"}
                ],
            }
        )
        plan = PlanVersion(id="p1", goal_id="g1", version=1, tasks=[task])
        assert len(IrreversibleInvariantGate().run(plan)) == 0


# ── M6: Enterprise Safety ──────────────────────────────────────────────────


class TestM6RedactorModes:
    """M6-4: Redactor hash/skip/custom (validates #184, #185 fixes)."""

    def test_hash_mode_deterministic(self) -> None:
        r = SecretsRedactor(mode=RedactMode.HASH)
        assert r.redact("key=AKIAIOSFODNN7EXAMPLE") == r.redact("key=AKIAIOSFODNN7EXAMPLE")

    def test_skip_mode_no_redact(self) -> None:
        r = SecretsRedactor(mode=RedactMode.SKIP)
        assert r.redact("key=AKIAIOSFODNN7EXAMPLE") == "key=AKIAIOSFODNN7EXAMPLE"

    def test_custom_regex(self) -> None:
        r = SecretsRedactor()
        r.add_custom_pattern("internal_token", r"INT-[a-z0-9]+")
        result = r.redact("token=INT-abc123 here")
        assert "INT-abc123" not in result

    def test_offset_not_corrupted(self) -> None:
        r = SecretsRedactor()
        text = "key1=AKIAIOSFODNN7EXAMPLE key2=AKIAIOSFODNN7EXAMPLE"
        result = r.redact(text)
        assert "AKIA" not in result
        assert result.count("[REDACTED_SECRET]") == 2


class TestM6QuotaPosture:
    """M6-5: Quota-posture 2x2 matrix (validates #193 fix)."""

    def test_strict_quota_blocker(self) -> None:
        config = BlastRadiusQuotaConfig(max_resource_changes=1)
        gate = BlastRadiusQuotaGate(config, posture=RiskTolerance.STRICT)
        plan = make_plan(tasks=[_task("t1"), _task("t2")])
        assert any(f.severity is Severity.BLOCKER for f in gate.run(plan))

    def test_restricted_exact_match_not_substring(self) -> None:
        config = BlastRadiusQuotaConfig(restricted_actions=["deploy"])
        gate = BlastRadiusQuotaGate(config, posture=RiskTolerance.STRICT)
        plan = make_plan(tasks=[_task("t1", action="undeploy")])
        assert not any(f.severity is Severity.BLOCKER for f in gate.run(plan))


class TestM6StateLock:
    """M6-3: StateLock WAIT strategy (validates #195 fix)."""

    def test_wait_times_out(self) -> None:
        lock = StateLock(strategy=LockStrategy.WAIT, wait_deadline=0.1)
        lock.acquire("res-1", "plan-1")
        result = lock.acquire("res-1", "plan-2")
        assert result == "resource_locked_by_concurrent_execution"

    def test_fail_fast(self) -> None:
        lock = StateLock(strategy=LockStrategy.FAIL_FAST)
        lock.acquire("res-1", "plan-1")
        assert lock.acquire("res-1", "plan-2") == "concurrent_resource_conflict"

    def test_escalate(self) -> None:
        lock = StateLock(strategy=LockStrategy.ESCALATE)
        lock.acquire("res-1", "plan-1")
        assert lock.acquire("res-1", "plan-2") == "resource_locked_by_concurrent_execution"


class TestM6GateRationale:
    """M6-1: Gate rationale metadata."""

    def test_builtin_gates_have_metadata_fields(self) -> None:
        from planner_critic.gates import GATES

        for gate in GATES:
            assert hasattr(gate, "name"), "Gate missing name"
            assert hasattr(gate, "author"), f"Gate {gate.name} missing author"
            assert hasattr(gate, "rationale"), f"Gate {gate.name} missing rationale"

    def test_stale_signal_exists(self) -> None:
        from planner_critic.gates.base import BaseGate

        assert hasattr(BaseGate, "_is_stale"), "BaseGate missing _is_stale method"


class TestM6PlanSignature:
    """M6-2: Plan signature persistence."""

    def test_signatures_differ_for_different_plans(self) -> None:
        plan1 = make_plan(tasks=[_task("a"), _task("b")])
        plan2 = make_plan(tasks=[_task("a"), _task("b"), _task("c")])
        sig1 = compute_plan_signature(plan1)
        sig2 = compute_plan_signature(plan2)
        assert sig1 != sig2

    def test_store_persists_signatures(self) -> None:
        from planner_critic.store.sqlite import SQLiteStore

        store = SQLiteStore(":memory:")
        plan = make_plan()
        store.put_plan_version(plan)
        assert store.get_plan(plan.id, plan.version) is not None


class TestM6StateView:
    """M6-3: StateView stale detection."""

    def test_stale_detection(self) -> None:
        from datetime import UTC, datetime

        old = StateSnapshot(
            version="v1", captured_at=datetime(2026, 1, 1, tzinfo=UTC), snapshot={"k": "v"}
        )
        new = StateSnapshot(
            version="v2", captured_at=datetime(2026, 1, 2, tzinfo=UTC), snapshot={"k": "v"}
        )
        view = StateView(old)
        assert view.is_stale(new) is True

    def test_not_stale_same_version(self) -> None:
        from datetime import UTC, datetime

        snap = StateSnapshot(
            version="v1", captured_at=datetime(2026, 1, 1, tzinfo=UTC), snapshot={"k": "v"}
        )
        view = StateView(snap)
        assert view.is_stale(snap) is False


class TestM6ReplanClassifier:
    """M6-6: RunBudget reason codes."""

    def test_run_budget_importable(self) -> None:
        from planner_critic.run_budget import RunBudget

        budget = RunBudget(run_max_budget_usd=1.0, run_max_depth=3, run_max_time=60.0)
        assert budget is not None

    def test_run_budget_under_limit(self) -> None:
        from planner_critic.run_budget import RunBudget

        budget = RunBudget(run_max_budget_usd=100.0, run_max_depth=10, run_max_time=3600.0)
        assert budget.check() is None

    def test_run_budget_exceeded(self) -> None:
        from planner_critic.run_budget import RunBudget

        budget = RunBudget(run_max_budget_usd=0.0, run_max_depth=0, run_max_time=0.0)
        budget._cumulative_spend_usd = 1.0
        assert budget.check() is not None


# ── M7: Developer Surfaces ──────────────────────────────────────────────────


class TestM7Decorators:
    """M7-4/5/6: @re_gate, @escalate decorators (validates #187 fix)."""

    def test_re_gate_calls_func_with_satisfied_ledger(self) -> None:
        called: list[bool] = []

        class FakeLedger:
            def read(self, key: str) -> dict[str, bool]:
                return {"satisfied": True}

        @re_gate(precondition_key="k", ledger=FakeLedger())
        def step() -> str:
            called.append(True)
            return "ok"

        assert step() == "ok"
        assert called == [True]

    def test_re_gate_raises_on_drift_with_ledger(self) -> None:
        class FakeLedger:
            def read(self, key: str) -> dict[str, bool]:
                return {"satisfied": False}

        @re_gate(precondition_key="k", ledger=FakeLedger())
        def step() -> str:
            return "ok"

        with pytest.raises(PreconditionDrift):
            step()

    def test_re_gate_no_ledger_raises(self) -> None:
        @re_gate(precondition_key="db_healthy")
        def step() -> str:
            return "ok"

        with pytest.raises(PreconditionDrift):
            step()

    def test_re_gate_on_drift_callback_no_ledger(self) -> None:
        keys: list[str] = []

        def on_drift(key: str) -> str:
            keys.append(key)
            return "handled"

        @re_gate(precondition_key="auth", on_drift=on_drift)
        def step() -> str:
            return "ok"

        assert step() == "handled"
        assert "auth" in keys

    def test_escalate_passes_through(self) -> None:
        def handler(reason: str) -> str:
            return f"handled: {reason}"

        decorated = escalate(handler)
        assert decorated is handler
        assert decorated("test") == "handled: test"

    def test_escalate_requires_handler(self) -> None:
        with pytest.raises(TypeError):
            escalate()


class TestM7DomainsCLI:
    """M7-1: plancritic domains CLI."""

    def test_domains_parser_exists(self) -> None:
        from planner_critic.cli.domains import build_domains_parser

        assert build_domains_parser() is not None

    def test_domains_list_runs(self) -> None:
        from planner_critic.cli.domains import run_domains

        try:
            run_domains(["list"])
        except SystemExit:
            pass

    def test_domains_show_runs(self) -> None:
        from planner_critic.cli.domains import run_domains

        try:
            run_domains(["show", "secops"])
        except SystemExit:
            pass


class TestM7PolicyCLI:
    """M7-2: plancritic policy CLI."""

    def test_policy_parser_exists(self) -> None:
        from planner_critic.cli.policy import build_policy_parser

        assert build_policy_parser() is not None

    def test_policy_list_runs(self) -> None:
        from planner_critic.cli.policy import run_policy

        try:
            run_policy(["list"])
        except SystemExit:
            pass


class TestM7TemplatesCLI:
    """M7-3: plancritic templates CLI."""

    def test_templates_parser_exists(self) -> None:
        from planner_critic.cli.templates import build_templates_parser

        assert build_templates_parser() is not None

    def test_templates_list_runs(self) -> None:
        from planner_critic.cli.templates import run_templates

        try:
            run_templates(["list"])
        except SystemExit:
            pass

    def test_seed_templates_exist(self) -> None:
        assert len(SEED_TEMPLATES) >= 5, f"Expected >=5 seed templates, got {len(SEED_TEMPLATES)}"


# ── M8: Integration ──────────────────────────────────────────────────────


class TestM8Notifier:
    """M8-3: Notifier dedup + signing_secret (validates #203, #210)."""

    def test_dedup_within_ttl(self) -> None:
        notifier = Notifier()
        event = EscalationEvent(
            escalation_id="e1", plan_id="p1", reason_code="test", question="what?"
        )
        _ = notifier.dispatch(event)
        r2 = notifier.dispatch(event)
        assert r2 == []

    def test_empty_secret_rejects(self) -> None:
        formatter = SlackFormatter("https://hooks.slack.com/test", signing_secret="")
        assert formatter.verify_signature("123", "body", "sig") is False

    def test_valid_secret_verifies(self) -> None:
        import hashlib
        import hmac
        import time

        secret = "test_secret"  # noqa: S105  # synthetic test value, not a credential
        fmt = SlackFormatter("https://hooks.slack.com/test", signing_secret=secret)
        ts = str(int(time.time()))
        body = "test"
        sig = (
            "v0="
            + hmac.new(secret.encode(), f"v0:{ts}:{body}".encode(), hashlib.sha256).hexdigest()
        )
        assert fmt.verify_signature(ts, body, sig) is True


class TestM8Drift:
    """M8-1: Drift metrics (validates #194 fix)."""

    def test_downgrade_rate_excludes_upgrades(self) -> None:
        f1 = _finding("missing_rollback", Severity.WARNING)
        f1 = f1.model_copy(
            update={
                "raw_severity": Severity.BLOCKER,
                "normalized_severity": Severity.WARNING,
                "drift_delta": -1,
            }
        )
        f2 = _finding("missing_rollback", Severity.BLOCKER)
        f2 = f2.model_copy(
            update={
                "raw_severity": Severity.WARNING,
                "normalized_severity": Severity.BLOCKER,
                "drift_delta": 1,
            }
        )
        summary = compute_drift_summary([f1, f2])
        assert summary["downgrade_rate"] == 0.5

    def test_underclaims_excludes_non_downgraded(self) -> None:
        f1 = _finding("missing_rollback", Severity.BLOCKER)
        f1 = f1.model_copy(
            update={
                "raw_severity": Severity.BLOCKER,
                "normalized_severity": Severity.BLOCKER,
                "drift_delta": 0,
            }
        )
        summary = compute_drift_summary([f1])
        assert summary["critical_underclaims"] == 0

    def test_drift_alert_importable(self) -> None:
        from planner_critic.drift import check_drift_alert

        f1 = _finding("missing_rollback", Severity.WARNING)
        f1 = f1.model_copy(
            update={
                "raw_severity": Severity.BLOCKER,
                "normalized_severity": Severity.WARNING,
                "drift_delta": -1,
            }
        )
        result = check_drift_alert([[f1], [f1]], family="missing_steps", z_threshold=2.0)
        assert isinstance(result, dict)
        assert "alert" in result


class TestM8GitLabCI:
    """M8-2: GitLab CI template + GitHub Action exist."""

    def test_gitlab_ci_exists(self) -> None:
        gitlab_ci = Path(__file__).parent.parent.parent / ".gitlab-ci.yml-planner-critic.yml"
        assert gitlab_ci.exists()

    def test_github_action_exists(self) -> None:
        action_yml = Path(__file__).parent.parent.parent / "action.yml"
        assert action_yml.exists()

    def test_gitlab_ci_parses(self) -> None:
        gitlab_ci = Path(__file__).parent.parent.parent / ".gitlab-ci.yml-planner-critic.yml"
        data = yaml.safe_load(gitlab_ci.read_text())
        assert isinstance(data, dict)


class TestM8AutoGenReGate:
    """M8-3: AutoGen adapter re-gate (validates #211 fix)."""

    def test_autogen_importable(self) -> None:
        from planner_critic.adapters.autogen import AutoGenAdapter

        assert AutoGenAdapter is not None

    def test_check_precondition_method_exists(self) -> None:
        from planner_critic.adapters.autogen import AutoGenAdapter

        assert hasattr(AutoGenAdapter, "_check_precondition")


# ── X-1: Docker integration ──────────────────────────────────────────────


class TestDockerIntegration:
    """X-1: Docker compose v0.2.0."""

    def test_docker_compose_exists(self) -> None:
        compose = Path(__file__).parent.parent.parent / "docker-compose.yml"
        assert compose.exists()

    def test_dockerfile_exists(self) -> None:
        dockerfile = Path(__file__).parent.parent.parent / "Dockerfile"
        assert dockerfile.exists()

    def test_docker_compose_parses(self) -> None:
        compose = Path(__file__).parent.parent.parent / "docker-compose.yml"
        data = yaml.safe_load(compose.read_text())
        assert isinstance(data, dict)
        assert "services" in data


# ── P0: Pre-run Assertion Validation ─────────────────────────────────────


class TestP0AssertionValidation:
    """P0: Validate all 170 assertion YAMLs before running LLM tests."""

    def test_all_goals_have_assertions(self) -> None:
        missing = []
        for gfile in sorted(GOALS_DIR.rglob("*.json")):
            astub = gfile.relative_to(GOALS_DIR)
            afile = GOALS_DIR / astub.parent / "assertions" / (astub.stem + ".yaml")
            if not afile.exists():
                missing.append(str(afile))
        assert not missing, f"Missing assertions: {missing}"

    def test_all_assertions_have_invariants(self) -> None:
        for afile in sorted(GOALS_DIR.rglob("assertions/*.yaml")):
            data = yaml.safe_load(afile.read_text())
            assert isinstance(data, dict), f"{afile} not dict"
            assert "invariants" in data, f"{afile} missing invariants"

    def test_no_strict_goal_approve_expected_true(self) -> None:
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

    def test_no_duplicate_ir07(self) -> None:
        ir07 = list(GOALS_DIR.glob("incident-response/ir-07-*"))
        assert len(ir07) == 1, f"Expected 1 ir-07, found {len(ir07)}"
