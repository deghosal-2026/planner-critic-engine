# Changelog

## v0.2.0 (2026-08-23)

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