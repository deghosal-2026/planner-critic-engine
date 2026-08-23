# Release Notes v0.2.0

**Date:** 2026-08-23
**Package:** `planner-critic` v0.2.0 — [PyPI](https://pypi.org/project/planner-critic/)

## What's New

### Deterministic Loop Efficiency (M2)
- **Topological auto-repair (#130)** — re-orders tasks to fix ordering-only violations without LLM revision cost
- **Deterministic precondition closer (#131)** — auto-injects template-matched precondition steps, eliminating unverified_precondition blockers without LLM revision
- **Oscillation detection + auto-converge (#152)** — detects structural cycling and auto-converges non-oscillating tasks

### Domain Pack Framework & Scaffolding (M3–M4)
- **Domain Pack protocol (#139)** — `DomainPack` protocol for domain-specific gates, manifest loader, engine integration
- **4 domain packs (#140–143)** — SecOps, Supply Chain, FinOps, Data Engineering — each with domain-specific deterministic gates
- **Policy-as-Code engine (#129, #156)** — OPA/Rego + CEL policy evaluation; `RegoGate`/`CelGate` integrate with the deterministic gate pipeline
- **`plancritic init --template` (#155)** — scaffold new domain packs from templates
- **Inverse-rollback synthesizer (#160)** — auto-generates rollback steps for planned actions
- **pytest-planner-critic plugin (#156)** — use gate assertions in your test suite

### Security & Trust Oracle (M5)
- **SWE-bench security corpus (#123)** — 7 instances across 7 CWE buckets as ground truth
- **Security oracle harness (#124)** — validate critic against human-labeled ground truth
- **Adversarial injection harness (#125)** — 21 injection trap patterns, per-layer attribution
- **Deterministic-gate security regression (#126)** — 35 flawed variants, 100% blocked
- **Standing-rule promotion (#127)** — label-migration harness for security-policy promotion

### Enterprise-Scale Safety (M6)
- **Dynamic posture resolver (#149)** — resolve `risk_tolerance` per-run from policy context
- **Run budgets (#150)** — hard limits on LLM spend per planning session
- **State locking (#151)** — `StateLock` with WAIT/ESCALATE strategies for concurrent planning
- **Precondition ledger (#158)** — audit trail of preconditions established across plan versions
- **Blast-radius quotas (#132)** — restrict concurrent task scope by action type and cluster
- **Secret/PII redaction (#159)** — regex-based redaction with audit trail, wired into every external-output surface
- **Gate-rationale metadata (#174)** — every gate result includes explanation of why it passed or blocked
- **Plan-signature persistence (#176)** — cryptographic plan signatures for integrity verification

### Developer & Interactive Surfaces (M7)
- **`plancritic check` (#137)** — quality-check a plan against all gates
- **`plancritic diagnose` (#175)** — diagnose why a plan failed gates
- **`plancritic domains` (#162)** — list available domain packs and their gates
- **`plancritic policy` (#178)** — evaluate Rego/CEL policies against a plan
- **`plancritic templates` (#179)** — list and scaffold from domain-pack templates
- **`@guardrail` decorator (#137)** — Python decorator for inline plan guardrails
- **Seed Rego library (#178)** — 4 starter policies (blast-radius, naming, least-privilege, quota)
- **Drift observability (#181)** — `plancritic findings` CLI + drift alert z-score

### Enterprise Integration & Adoption (M8)
- **GitHub Action (#128)** — community action for CI pipeline integration
- **GitLab CI template (#128)** — ready-to-use `.gitlab-ci.yml` template
- **AutoGen adapter (#134)** — integrate PlannerCritic as an AutoGen agent
- **Webhook notifier (#161)** — Slack/Teams/Generic webhook delivery with HMAC + JWT verification

### Scale Validation & Enhancement (M9)
- **5 new enterprise field-test corpora** — IDP, MAO, SRE, SCP, FNG — 14 goal files, 16 new reason codes
- **Auto-repair benchmark (#177)** — ≥30% revision reduction on ordering-violation corpus
- **Rollback credibility field test (#182)** — 21 goals across 8 domains, 3 credibility patterns
- **Family-histogram stasis benchmark (#183)** — ≥20% revision reduction from family-based convergence

### Release-Gate Field Test (M10)
- **170 goals across 40 domains** — 73 approved (balanced), 97 escalated (strict), 8 escalated (adversarial), 0 true failures
- **90 deterministic subsystem tests** — covering all v0.2.0 features
- **3 benchmarks completed** — auto-repair, rollback credibility, family-histogram stasis
- **Security oracle: 7/7 correct plans pass, 35/35 flawed variants blocked, 21 injection traps generated**
- **Release gate: PASS** on all 8 blocking criteria

### Code Quality
- **31 bugs found and fixed** by pre-release code review (#184–#214) — including 6 critical (redaction offset corruption, RegoGate `--data`→`--input`, dead `@re_gate`, MCP critic cache, diagnose `KeyError`, oracle double-count)
- Coverage ≥95%
- Lint clean (ruff + mypy strict)

## Breaking Changes

- **Configuration format** — The `plancritic-fieldtest.toml` v0.1.0 config file is superseded by the new provider registry. Use `plancritic providers add` or write a `plancritic.toml` with `[providers.*]` sections.
- **Domain-pack config** — `pack_config` is now part of the `DomainPack` Protocol, not a module-level global. Existing domain packs must migrate to the protocol.
- **API key handling** — Hardcoded `api_key` values in config files were removed in favor of `${ENV_VAR}` references. Set `OPENROUTER_API_KEY` or equivalent in your environment.

## Upgrade Path

1. **Config migration:** Replace v0.1.0 config files (`plancritic-fieldtest.toml`, `plancritic-asymmetric.toml`, etc.) with the new format. Use `plancritic migrate --path .plancritic/plans.db` to upgrade the plan store schema if needed.
2. **Domain packs:** If you authored custom domain packs in v0.1.0, update them to implement the `DomainPack` protocol (see `docs/design/domain-pack-design.md`).
3. **API references:** Replace `api_key = "sk-..."` with `api_key = "${OPENROUTER_API_KEY}"` in config files.

## Field Test Results

| Metric | Result |
|--------|--------|
| Balanced goals approved | 73/73 (100%) |
| Strict goals escalated | 97/97 (100%) |
| Adversarial goals escalated | 8/8 (100%) |
| True failures | 0 |
| Deterministic gate passes | 170/170 (100%) |
| Security oracle | 7/7 correct, 35/35 flawed, 21 traps |
| Scorecard A (pre-amended) | PASS |
| Scorecard B (pass\* semantics) | 100% |
| Deterministic tests | 90/90 pass |
| Benchmarks | 3/3 complete |

## Known Issues

- **Planner capability gap** — strict tolerance + LLM critic = structurally unable to approve non-trivial plans. Usable with `balanced` tolerance in production; `strict` is for adversarial/security testing.
- **Local model support** — DeepSeek-R1-8B cannot produce valid structured JSON; Qwen3-4B critic is too weak (false-positive approvals on strict goals). Use `openai/gpt-4o-mini` via OpenRouter.
- **TUI / studio / IDE surfaces** — deferred to v0.3.0.
- **Backstage plugin / Slack dashboard** — deferred to v0.3.0.
- **Adaptive revision cap** — not yet implemented.

## Documentation

| Doc | Location |
|-----|----------|
| Field Test Results | `docs/field-test/v0.2.0/field-test-results-0.2.0.md` |
| Field Test Plan | `docs/field-test/README.md` |
| Architecture | `docs/architecture/architecture-v0.1.0.md` |
| API Reference | `docs/reference/api.md` |
| Design Decisions | `docs/design/design-decisions.md` |
| Domain Pack Design | `docs/design/domain-pack-design.md` |
| Policy Engine Design | `docs/design/policy-engine-design.md` |
| Enterprise Safety Design | `docs/design/enterprise-safety-design.md` |
| Developer Surfaces Design | `docs/design/developer-surfaces-design.md` |
| Integration Surfaces Design | `docs/design/integration-surfaces-design.md` |
| Security | `SECURITY.md` |
| Changelog | `CHANGELOG.md` |