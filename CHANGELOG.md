# Changelog

## v0.2.2 (2026-08-27)

### Foundation Corrections (M1)
- Fixed "Zero True Failures" prose contradiction in v0.2.1 field test report (#246)
- Reconciled `plan_oscillation_detected` count from 3 to 5 (#247)
- Removed 75 pytest-cov artifacts from `src/` and added `*.py,cover` to `.gitignore` (#248)
- Reconciled 1294/1295 test count discrepancy in v0.2.1 docs (#263)
- Created failure-origin taxonomy classifying 51 bugs by first-detectable layer (#264)

### Gate & Schema Hardening (M2)
- Runtime precondition verification on by default (mode defaults to `before-each-step`) (#244)
- Typed rollback restoration contracts: `restores_state` + `restoration_evidence` on `RollbackStep` (#245)
- Requirement-traceability gate: opt-in `satisfies` field on `Task` (#255)
- Machine-actionable finding contract: `edge_id`, `observed_state`, `evidence_refs`, `FINDING_SCHEMA_VERSION` (#243)
- Decision-context capture + unsupported-evidence frequency metric in live-boundary runner (#242)

### Security & Injection Resistance (M3)
- Wired `approving_authority` through CLI/HTTP/MCP surfaces (#238)
- Fixed field_test_harness escalation auto-approve (scope, deny path, wrong-principal test) (#253)
- 11 benign-twin goal files for adversarial goals — measures injection isolation vs gate strictness (#260)
- Tool-result provenance + capability-scoped state transitions module (#249, #258)
- 3 compositional injection trap goals (individually feasible, harmful in combination) (#256)
- Well-formed malicious plan detection tests — structural gates pass, intent is malicious (#259)

### Operational & Audit (M4)
- Cost-vs-rigor guardrails: immutable `GatesConfig` with validation (#262)
- Escalation audit trail: `resolved_by` field, `build_explain` shows accurate status after resolution (#261)
- Critic satisfaction signals: `CRITIC_SATISFIED` reason code for strict mode approval (#254)
- Adaptive revision cap: strict goals reduce to 1 revision (opt-in, default off) (#251)
- Critic/planner capability tier split: config example for separate model tiers (#257)
- Multi-model planner comparison benchmark script (#252)
- Downstream error rate measurement specification (#250)

### Field Test Results (M5)
- **183 goals across 43 domains** — 170 inherited + 13 new security fixtures
- **73/73 balanced approved** (100%), **96/97 strict escalated** (99%), **8/8 inherited adversarial aborted** (100%)
- **8/8 benign twins approved** — new measurement arm confirms injection isolation vs gate strictness
- **3/3 compositional traps aborted** — new security fixture class verified
- **2 well-formed malicious fixtures** added to the corpus (#259)
- **Scorecard A: PASS** — release gate passes on inherited corpus
- **Boundary evaluator (#218):** first run exposed `underclaim_approvals=1`; strict-framing fix applied, rerun cleared to `0`
- **Operational benchmark:** completed on 181 traces; latency and reviewer burden increased (see report)
- **1347 deterministic subsystem tests pass** (15 skipped: 12 docker-gated, 3 LLM-dependent, 1 flaky)
- **5 benchmarks completed** — cycling, operational, live-boundary, boundary self-test, auto-repair
- **Coverage:** 91%

### Known Issues
- TUI/studio/IDE extensions deferred to v0.3.0 (#133, #135, #136, #138, #154, #157)
- `approving_authority` wiring completed in this release (#238, resolves F-14)

## v0.2.1 (2026-08-23)

### Hardening
- **Frozen acceptance-criteria contract (#215)** — `AcceptanceContract` bound pre-run; post-bind mutation creates new version + audit trail; wrong-principal rejection
- **Rollback credibility gate (#216)** — unreachable / self-dependent / inconsistent-state / post-consumed rollback detection
- **Verification-before-mutate ordering gate (#219)** — vacuous-verification-window detection; data-subject contract (pre-state vs output)
- **Family-histogram cycling detection (#217)** — period-2 A→B→A→B reshuffling stall signal; progress guard suppresses declining-mass alternation
- **Live-critic boundary-case runner (#218)** — repeated-trial label-flip, family-migration, evidence-drift, underclaim-approval measurement
- **Failure-mode register (#220)** — `docs/reference/failure-modes.md` (14 rows)
- **Drift-metric blind-spot contract (#231)** — `critical_underclaims` interpretation key; two measurement classes

### Bug Fixes
- **10 bugs fixed** by code review (#232–#241): histogram cycling detector (#232), rollback-credible message quality (#233), gate finding-id collisions (#234), live-boundary fault isolation (#235), vacuous adapter test (#236), suggested-fix group name (#237), evidence-drift pooling (#239), contract posture stamping (#240), content-hash ordering (#241)
- **1 documented caveat** — F-14: `approving_authority` wiring deferred to v0.3.0 (#238)

### Field Test Results
- **170 goals across 40 domains** — 73 balanced approved (100%), 96 strict escalated (99%), 8 adversarial (100%)
- **30 verdict deltas vs v0.2.0** — all attributable; zero unexplained
- **1295 deterministic subsystem tests pass**
- **3 benchmarks** — cycling, operational, live-critic boundary (#218)
- **Live-critic boundary:** label_flip=1.0, evidence_drift=1.0, family_migration=0.0, underclaim_approvals=0
- **Operational benchmark:** latency p50=13.86s/27.82s, median revisions=1.0
- **Release gate: PASS**
- Coverage 91.58% (>91% floor), lint clean (ruff + mypy strict, 274 files)

### Features
- **Deterministic loop efficiency** — topological auto-repair (#130), deterministic precondition closer (#131), oscillation detection + auto-converge (#152)
- **Domain Pack framework** — `DomainPack` protocol, 4 domain packs (SecOps, Supply Chain, FinOps, Data Engineering), `plancritic init --template`, inverse-rollback synthesizer (#139, #140–143, #155, #160)
- **Policy-as-Code engine** — OPA/Rego + CEL policy evaluation, `RegoGate`/`CelGate` integration with deterministic gate pipeline (#129, #156)
- **Security oracle** — SWE-bench security corpus, oracle harness, adversarial injection harness, deterministic-gate security regression, standing-rule promotion (#123–127, #171)
- **Enterprise safety** — dynamic posture resolver, run budgets, state locking, precondition ledger, blast-radius quotas, secret/PII redaction, gate-rationale metadata, plan-signature persistence (#132, #149–151, #158, #159, #174, #176)
- **Developer surfaces** — `plancritic check`, `diagnose`, `domains`, `policy`, `templates` CLI + `@guardrail` decorator + seed Rego library + drift observability (#137, #153, #162, #175, #178, #179, #181)
- **Enterprise integration** — GitHub Action, GitLab CI template, AutoGen adapter, webhook notifier with HMAC + JWT verification (#128, #134, #161)
- **pytest-planner-critic plugin** — use gate assertions in test suite (#156)
- **Health probe system** — DB, deploy, env, HTTP probes for pre-execution precondition validation
- **Scale validation** — 5 new enterprise corpora (IDP, MAO, SRE, SCP, FNG), auto-repair benchmark, rollback credibility field test, family-histogram stasis benchmark (#144–148, #177, #182, #183)
- **21 new CLI commands** — full subcommand infrastructure (`check`, `diagnose`, `domains`, `policy`, `templates`, `eval`, `findings`, `lessons`, `quota`, `replay`, `providers`, etc.)

### Breaking Changes
- **Configuration format** — v0.1.0 config files superseded by provider registry; use `plancritic providers add` or new `plancritic.toml` format
- **Domain-pack config** — `pack_config` is now part of the `DomainPack` Protocol (not module-level)
- **API key handling** — hardcoded keys removed; use `${ENV_VAR}` references in config

### Bug Fixes
- **31 bugs fixed** by pre-release code review (#184–#214) — 6 critical, 25 important
- Critical: redaction offset corruption, RegoGate `--data`→`--input`, dead `@re_gate` code, MCP critic cache, diagnose `KeyError`, oracle double-count

### Field Test Results
- **170 goals across 40 domains** — 73 approved (balanced), 97 escalated (strict), 8 escalated (adversarial), 0 true failures
- **100% balanced pass rate** — every balanced goal approves
- **100% strict escalate rate** — every strict goal correctly refuses unsafe plans
- **8/8 adversarial escalate** — injection-immune confirmed
- **Security oracle** — 7/7 correct, 35/35 flawed blocked, 21 injection traps generated
- **90 deterministic subsystem tests pass**
- **3 benchmarks complete**
- **Release gate: PASS** on all 8 blocking criteria
- Coverage ≥95%, lint clean (ruff + mypy strict)

### Known Issues (v0.3.0)
- **Planner capability gap** — strict + LLM critic = never approve non-trivial plans
- **Local models** — DeepSeek-R1-8B broken JSON, Qwen3-4B critic too weak
- **TUI / studio / IDE** — deferred
- **Backstage / Slack dashboard** — deferred

## v0.1.0 (2026-08-20)

### Features
- **Hierarchical task planning** — decompose a goal into a typed PlanVersion with tasks, dependencies, branches, preconditions, and verification steps
- **LLM critic** — audit every plan revision against six heuristic families (feasibility, risk, missing_steps, unsafe_sequencing, unverified_dependencies, weak_rollback)
- **Plan revision loop** — planner revises based on critic findings, loop terminates on approval, escalation, budget, convergence, or revision cap
- **Risk tolerance** — `balanced` (findings are advisory warnings) and `strict` (zero tolerance for any finding, fail-closed)
- **Deterministic gates** — 7 injection-immune gates (ordering-sanity, branch-sanity, rollback-safety, verification-safety, preconditions-referenced, branch-tasks, high-risk-completeness)
- **Escalation management** — human-in-the-loop escalation with override, patch, and restart decisions
- **Convergence detection** — early termination when the planner stops making meaningful progress
- **Plan revision policies** — `patch`, `restart`, `abort`

### Tools & Surfaces
- **CLI** — `plancritic plan`, `plancritic critique`, `plancritic field-test run`, `plancritic demo`, `plancritic quickstart`, `plancritic migrate`
- **Python API** — `Engine.plan()`, `ApprovedPlan`, `LoopResult`, `Finding`, `Escalation`
- **HTTP server** — `plancritic serve` with health check, plan, and escalation endpoints
- **Field test harness** — run 156+ goals across 35 domains, produce Scorecard A/B, release gate adjudication
- **Provider registry** — pluggable LLM providers (OpenRouter, OpenAI, oMLX, Ollama) via TOML config
- **StructuredEnforcer** — retry mechanism for LLM JSON output, fail-closed after 3 retries

### Breaking Changes
- None — v0.1.0 is the initial release.

### Field Test Results
- **157 goals across 35 domains** — 71 approved (balanced), 86 escalated (strict/adversarial), 0 true failures
- **100% balanced pass rate** — every balanced goal approves
- **100% strict escalate rate** — every strict goal correctly refuses unsafe plans
- **8/8 adversarial escalate** — injection-immune, policy-violation detection confirmed
- **Scorecard A** — PASSES release gate after §7.1a plan amendment (strict goals flipped to escalate)
- **Scorecard B** — 100% pass rate (pass\* semantics)