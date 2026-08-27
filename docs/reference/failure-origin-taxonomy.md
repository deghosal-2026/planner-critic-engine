# Failure-Origin Taxonomy — how each defect was first detectable

> Companion to the [failure-mode register](failure-modes.md). Tracks the detection layer
> where each field-test defect or code-review finding was *first detectable*, enabling
> the team to invest in cheaper detection earlier in the pipeline.
>
> **Date:** 2026-08-26 · **Author:** Debashish Ghosal · **Status:** Active (v0.2.2)
>
> **Proposed by:** Russlan Ramdowar (dev.to article 4 comments)

---

## Detection Layers

| Layer | Cost | Detection speed | Description |
|-------|------|----------------|-------------|
| **Code review** | $0 | minutes | Human reviewer reads the diff and spots the defect before any test runs |
| **Harness invariant** | $0 | seconds | A field-test harness invariant (e.g., "0/0 results is an error, not a pass") catches the defect during validation |
| **Deterministic gate** | $0 | milliseconds | A structural gate (precondition closer, ordering, rollback, schema) catches the defect during plan evaluation |
| **Unit test** | $0 | seconds | A pytest test with hand-crafted input catches the defect |
| **Live-model variance** | $0.49 | 60 min | The LLM field test sweep catches the defect — a real LLM produces unexpected output on real goals |
| **Production-like input** | depends | depends | A real-world edge case not in the corpus catches the defect after deployment |

## Defect Classification (v0.1.0 — v0.2.1)

All 51 bugs found across v0.1.0 — v0.2.2, classified by first-detectable layer.

### Code Review (31 bugs)

Defects caught by human code review before any test ran. These are the highest-leverage finds — caught at $0 before the field test even started.

| # | Issue | Title | First detectable in |
|---|-------|-------|-------------------|
| 1 | #184 | redaction.py: offset corruption leaves partial secrets exposed | Code review |
| 2 | #185 | redaction.py: redact_dict loses audit trail for all but the last string | Code review |
| 3 | #186 | policy.py: RegoGate passes input JSON via --data instead of --input | Code review |
| 4 | #187 | guardrail.py: re_gate decorator never calls the wrapped function | Code review |
| 5 | #188 | loop/_controller.py: auto-converge is non-functional (no-op stub) | Code review |
| 6 | #189 | loop/convergence.py: _plan_fingerprint excludes task content | Code review |
| 7 | #190 | loop/autofix.py: precondition closer injects duplicate task IDs | Code review |
| 8 | #191 | server/mcp.py: _build_engine caches critic across different goals | Code review |
| 9 | #192 | eval/oracle.py: security oracle double-counts aligned LLM findings as missed | Code review |
| 10 | #193 | quota.py: restricted_actions/restricted_clusters use substring matching | Code review |
| 11 | #194 | drift.py: downgrade_rate counts upgrades too | Code review |
| 12 | #195 | state.py: StateLock WAIT strategy doesn't actually wait | Code review |
| 13 | #196 | cli/check.py: _gate_verdict ignores INFO severity | Code review |
| 14 | #197 | cli/diagnose.py: unverified_precondition rule causes KeyError | Code review |
| 15 | #198 | domains/secops/gates.py: BlastRadiusGate ignores drain ordering | Code review |
| 16 | #199 | domains/secops/gates.py: LeastPrivilegeGate substring matching causes false positives | Code review |
| 17 | #200 | domains/finops/gates.py: BudgetBoundaryGate parses resource target as dollar amount | Code review |
| 18 | #201 | rollback_synth.py: unknown actions default to restore_snapshot instead of noop | Code review |
| 19 | #202 | domains/base.py: pack_config is module-level | Code review |
| 20 | #203 | notifier.py: dedup set grows unboundedly | Code review |
| 21 | #204 | field-test: 89 strict-goal assertions expect approve_expected:true | Code review |
| 22 | #205 | field-test: duplicate ir-07 slot — adversarial billing duplicates adv-01 | Code review |
| 23 | #206 | eval/label_migration.py: IrreversibleInvariantGate allows verification to substitute for precondition | Code review |
| 24 | #207 | escalation.py: patch_and_recritique rejects LLM blockers | Code review |
| 25 | #208 | field-test: M9 domain assertions reference generic reason codes | Code review |
| 26 | #209 | field-test: 14 M9 domain goals absent from plan, run scripts, and results report | Code review |
| 27 | #210 | notifier.py: SlackFormatter verify_signature silently accepts all callbacks | Code review |
| 28 | #211 | adapters/autogen.py: _check_precondition always returns True | Code review |
| 29 | #212 | field_test_harness.py: PlannerCriticPlan test passes PlanVersion instead of Engine | Code review |
| 30 | #213 | cli/templates.py: test subcommand passes empty findings | Code review |
| 31 | #214 | field_test_harness.py: run_budget creates disconnected SpendState | Code review |

### Code Review (v0.2.1 — 10 more bugs)

| # | Issue | Title | First detectable in |
|---|-------|-------|-------------------|
| 32 | #232 | Histogram cycling detector unreachable under default revision_cap=3 | Code review |
| 33 | #233 | rollback_credible gate emits bare task id as message | Code review |
| 34 | #234 | Finding ids collide — distinct defects merge silently | Code review |
| 35 | #235 | Live-critic runner loses entire run on mid-trial exception | Code review |
| 36 | #236 | test_all_adapters_importable gutted to pass (vacuous) | Code review |
| 37 | #237 | Suggested-fix prints task id where group name belongs | Code review |
| 38 | #238 | approving_authority not wired to any shipped surface | Code review |
| 39 | #239 | Evidence-drift metric pools explanations across trials | Code review |
| 40 | #240 | ApprovalGate stamps ambient goal posture, not contract | Code review |
| 41 | #241 | Content hash preserves criteria insertion order | Code review |

### Harness Invariant (1 bug)

| # | Issue | Title | First detectable in |
|---|-------|-------|-------------------|
| 42 | v0.1.0 field test | 57 of 65 assertion files in wrong format — harness silently produced 0/0 | Harness invariant |

### Live-Model Variance (9 bugs)

| # | Issue | Title | First detectable in |
|---|-------|-------|-------------------|
| 43 | v0.1.0 field test | Planner prompt didn't explain branches schema — LLM responded with wrong format | Live-model variance |
| 44 | v0.1.0 field test | Preconditions gate too strict — established_by expected task ID, LLM wrote fact names | Live-model variance |
| 45 | v0.1.0 field test | Critic severity contract wrong — blocking on completeness instead of concrete defects | Live-model variance |
| 46 | v0.1.0 field test | Dimension dispatch signature mismatch — run_budget() takes 4 args, dispatch passed 5 | Live-model variance |
| 47 | v0.1.0 field test | Cross-dimension state lost — in-memory SQLite store reset between runs | Live-model variance |
| 48 | v0.1.0 field test | Results parser read wrong JSON path — trace.get("status") instead of trace["result"]["status"] | Live-model variance |
| 49 | v0.1.0 field test | Local models (Qwen3.5-4B, Qwen3.5-9B) couldn't produce structured JSON | Live-model variance |
| 50 | v0.1.0 field test | LLM critic is non-deterministic — strict goals re-run with different blockers each time | Live-model variance |
| 51 | v0.1.0 field test | Stronger model (gpt-4o) produced same defect patterns as gpt-4o-mini | Live-model variance |

## Heatmap

| Detection layer | Bugs found | % of total | Cost per bug | Cumulative % |
|----------------|-----------|-----------|-------------|-------------|
| Code review | 41 | 80% | $0 | 80% |
| Harness invariant | 1 | 2% | $0 | 82% |
| Deterministic gate | 0 | 0% | $0 | 82% |
| Unit test | 0 | 0% | $0 | 82% |
| Live-model variance | 9 | 18% | ~$0.005 | 100% |
| Production-like input | 0 | 0% | depends | 100% |

## Migration Path

The heatmap shows that **80% of all defects were first detectable by code review** — a $0 activity. The remaining 18% required live-model variance (the LLM field test). This suggests:

1. **Code review is the highest-leverage detection layer.** Invest in code review checklists and peer review discipline.
2. **Live-model variance catches what code review cannot.** The 9 bugs found only by running real LLM data (prompt format issues, gate strictness mismatches, non-determinism) are invisible to static analysis.
3. **No defects were first detectable by unit tests alone.** All unit-test-found defects were also detectable by code review. This does not mean unit tests are useless — they provide regression coverage — but they should not be the primary detection layer.
4. **Goal for v0.3.0:** Move more defect classes from "live-model variance" to "deterministic gate" by adding structural checks that catch the 9 LLM-specific patterns.

## Maintenance

- Append new rows as new defects are found
- Recompute the heatmap at each release
- Update the migration path recommendations as the detection layer distribution changes