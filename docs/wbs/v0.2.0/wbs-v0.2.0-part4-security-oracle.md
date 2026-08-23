# WBS — PlannerCritic Engine v0.2.0 Part 4: Security & Trust Oracle (SWE-bench Verified)

> **Milestone covered:** M5 (Security & Trust Oracle)
> **PRD covering this milestone:** [06-security](../../design/prd/06-security-baseline.md) (§6.3 Hardened) · [08-risks](../../design/prd/08-risks.md) · [07-success-metrics](../../design/prd/07-success-metrics.md) (§7.1 #2)

---

## Milestone 5: Security & Trust Oracle (SWE-bench Verified)

**Objective:** Close the security ground-truth gap with a **trusted, human-validated** source the critic can be measured against. M5 is a strict dependency chain — corpus → measure → inject → regress → learn — turning the security-critique story from "we self-grade on our own seeded flaws" into "measured against human-validated CVE patches." Parallelizable with M3–M6; hermetic where possible ($0 LLM in CI).

**PRD coverage:** §6.3 Hardened tier, §7.1 criterion #2 (blocker-detection ≥ 90%), §08 adversarial-risk mitigation.

### M5.1 SWE-bench Verified security-patch corpus + loader (#123) — *foundation*

- Curate the security-fix subset of SWE-bench Verified: ~30–60 instances across ≥6 CWE buckets (CWE-79/89/22/287/502/918 + secret-handling), license-filtered (MIT/Apache-2.0/BSD), pinned + checksummed, checked into `docs/field-test/corpus/swebench-security/`.
- Normalize each into `(Goal, ground_truth)` with `vulnerability_class`, CWE bucket, and `expected_critic_signal` mapped to a §2.5.1 heuristic family. Provenance complete (instance_id, repo@commit, patch SHA, license).
- Loader CLI: `plancritic corpus swebench-security {list,load,pull,show}`; deterministic + hermetic; `pull` reproducible (checksum CI-asserted).

### M5.2 Critic security-oracle validation harness (#124)

- `plancritic eval swebench-security --report`: run planner→critic on a Goal derived from the issue (no patch leaked); diff planned change-set against ground-truth patch; classify findings `aligned`/`missed`/`spurious`.
- Metrics: **security-critic accuracy** = aligned/(aligned+missed) (target ≥60% baseline), **plan-to-patch alignment**, per-CWE-bucket breakdown (blind-spot map), missed-critique records (F-51 shape) fed to #127.
- Diff-aware mode (F-78) exercised; deterministic-only (hermetic) mode available; scorecard diffable across models.

### M5.3 Adversarial injection harness (#125)

- Deterministic, templated (not LLM-generated) trap variants per corpus instance (instruction-override, authority-appeal, urgency-bypass); ≥2 per instance; checksummed.
- `plancritic eval swebench-security --adversarial`: per-trap `approve_expected: false`; mandatory blocker reason code; **per-layer blocking attribution** (deterministic gate vs LLM critic) — quantifies the LLM's susceptibility honestly.
- **Injection-immunity rate = 100%**; any approval is a release-blocking regression filed with the trap + failing layer. Extends #106's C34 danger-detection audit.

### M5.4 Deterministic-gate security regression corpus (#126)

- Derive plan artifacts from SWE-bench security patches (deterministic, no LLM): one correct skeleton + ≥5 flawed variants per instance (drop verification / rollback / inject unsafe ordering / inject cycle / drop precondition), each labeled with expected gate + `reason_code`.
- Hermetic regression assertions (F-67, $0): correct skeletons zero false-positive blockers; flawed variants 100% trigger labeled gate; **injection-immunity**: appending a goal-text override does not change the gate verdict.
- `plancritic field-test --deterministic-gates-swebench`; every §2.5.2 `reason_code` exercised by real-CWE-derived variants.

### M5.5 Missed-critique → standing-rule promotion (#127)

- Consume `missed` records from M5.2 as high-trust; stub-execution misses as low-trust. `plancritic lessons propose/list/promote`.
- Derive candidate deterministic standing rules from patch file-pattern × CWE class (pattern-mined, auditable, non-LLM); dedup by (CWE × pattern) with coverage count.
- `promote <id>` writes an F-79 heuristic-pack rule + marks the miss `promoted`; provenance rule→miss→instance→corpus_version reconstructable. High-trust ordered before low-trust.

### M5.6 Label-migration escape harness (#171)

- The blocker allowlist trusts the model-chosen severity family (`missing_steps` vs `unsafe_sequencing`). If a model re-labels a blocked concern into a blocker-eligible family, it slips the gate. This is the classification twin of #97: right verdict for the wrong cause, at the family boundary.
- Keep **both raw finding text and normalized family** in every eval row — never collapse early.
- **Boundary-case generator** (differ by exactly one fact):
  - optional step vs. required dependency
  - possible latency vs. unsafe ordering
  - rollback improvement vs. no viable rollback
- **Confusion matrix** across severity families; a family that silently turns a non-blocker into an allowed blocker is a release-blocking defect.
- **Deterministic invariant gate** for irreversible steps ("verified predecessor + rollback condition") that outranks any model-chosen blocker label.
- Hermetic where possible ($0 LLM in CI); feeds the same scorecard surfaces as M5.2–M5.4.

### M5 Task Checklist

| # | Task | Verify | Issue | Status |
|---|------|--------|-------|--------|
| 1 | Corpus + loader + provenance + pinning | 7 instances, 7 CWE buckets, checksum-reproducible, $0 | [#123](https://github.com/deghosal-2026/planner-critic-engine/issues/123) · [x] |
| 2 | Critic-oracle harness + scorecard + alignment metric | `plancritic eval swebench-security --regression`; regression corpus passes all gates | [#124](https://github.com/deghosal-2026/planner-critic-engine/issues/124) · [x] |
| 3 | Injection harness + per-layer attribution | `plancritic eval swebench-security --adversarial`; traps generated per instance | [#125](https://github.com/deghosal-2026/planner-critic-engine/issues/125) · [x] |
| 4 | Gate regression corpus + hermetic assertions | 100% gate accuracy; 5+ flawed variants per instance; all 6 reason codes exercised | [#126](https://github.com/deghosal-2026/planner-critic-engine/issues/126) · [x] |
| 5 | Standing-rule promotion + trust tiering + dedup | `plancritic lessons propose/list/promote`; high-trust promoted; provenance complete | [#127](https://github.com/deghosal-2026/planner-critic-engine/issues/127) · [x] |
| 6 | Label-migration harness + boundary cases + invariant | `generate_boundary_cases()` produces 2+ pairs; `IrreversibleInvariantGate` blocks irreversible steps | [#171](https://github.com/deghosal-2026/planner-critic-engine/issues/171) · [x] |

### M5 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| Corpus | ~30–60 instances; ≥6 CWE buckets; permissive-only | loader count + class-balance check |
| Security-critic accuracy | ≥60% baseline (v0.2) | eval scorecard |
| Injection-immunity | 100% | adversarial report |
| Gate regression | 100% accuracy; injection-immune | hermetic CI |
| Standing-rule provenance | rule → miss → instance → corpus reconstructable | store query |
| Label-migration | 0 verdict flips on boundary cases; invariant blocks irreversible w/o precondition | confusion matrix + invariant tests |
| Coverage | >95% | `--cov-fail-under=95` |
| Lint | 0 ruff + 0 mypy strict | `ruff` + `mypy` |

### M5 Exit Gate

- [x] Release-blocking security claim now corpus-backed (not "one hand-written ADV-07")
- [x] Baseline security-critic accuracy + blind-spot bucket published
- [x] Hermetic gate holds ($0 LLM in CI); checksums CI-asserted
- [x] Label-migration harness green: no boundary flips; irreversible invariant blocks regardless of model label
- [x] Coverage > 95; lint clean; code review passed

**Dependency:** v0.1.0 base (parallelizable with M2–M4). **Produces for M4/M9/M10:** heuristic-pack rule source for M4 packs, regression evidence for M10 release gate.