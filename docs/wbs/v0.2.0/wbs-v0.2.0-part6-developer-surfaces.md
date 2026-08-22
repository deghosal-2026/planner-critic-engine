# WBS — PlannerCritic Engine v0.2.0 Part 6: Developer & Interactive Surfaces

> **Milestone covered:** M7 (Developer & Interactive Surfaces) — ✅ COMPLETE
> **PRD covering this milestone:** [05-features](../../design/prd/05-features.md) (F-75 viz, F-76 replay, F-80 explain, F-61 CLI, F-62 HTTP) · [04-users-and-cujs](../../design/prd/04-users-and-cujs.md) (developer persona)

---

## Milestone 7: Developer & Interactive Surfaces

**Objective:** The engineer-experience stone — the surfaces a developer or platform engineer reaches for when debugging, adopting, or integrating a plan gate. Root-cause analysis, lightweight offline checking, CLI ergonomics for pack/policy/template management, and Python decorator ergonomics. Everything is deterministic where possible ($0 LLM in the background surfaces).

**PRD coverage:** F-61 CLI, F-79 pack format (diagnose rules). Consumes M6 redaction for `diagnose`/`check` output.
**CUJs covered:** CUJ 5 (escalation explains), CUJ 10 (replay), developer + on-call personas.

### M7.2 `plancritic diagnose` (#153)

- Sentry-style root-cause analyzer for **execution** traces (distinct from F-80's loop `explain`): parses `ExecutionTrace` → failing step, failure category (from `failure_class` + `reason_code`), severity, root cause, suggested fix, trace excerpt.
- Deterministic `DiagnosticRule` engine (10 built-in rules, no LLM narration); `unclassified_failure` when nothing matches; `--format human|json|markdown`; `--export-otel` (F-82).
- Feeds missed-critique (#127) when a planning failure is identified.

### M7.5 `plancritic check` (#162)

- Lightweight, sub-second, **zero-LLM offline** gate evaluation against a plan file: `plancritic check <plan_file> [--domain PACK] [--policies-dir] [--enforcement] [--context] [--fail-on-severity] [--output json|text|yaml]`.
- Loads plan; runs domain-pack deterministic gates + Rego policies; exits 0 (pass / below threshold) / 1 (gate violation ≥ threshold) / 4 (config error).
- **Integrates mid-IR #128 (CI lightweight path).**

### M7.6 `plancritic domains` CLI (#178 — carried from M3)

- `plancritic domains list` — shows installed packs from namespace scanning
- `plancritic domains show <name>` — displays pack details (gates, preconditions, prompt)
- `plancritic domains add <path>` — registers a `domain-pack.yaml`
- `plancritic domains test <name> <plan-file>` — dry-run domain gates against a file

### M7.7 `plancritic policy` CLI + seed Rego library (#179 — carried from M3)

- `plancritic policy list` — shows installed policy gates
- `plancritic policy add <path>` — registers a `policy-pack.yaml` or `.rego` file
- `plancritic policy test <name> <plan-file>` — dry-run a policy against a plan
- Populate `BUILTIN_POLICIES` with Rego equivalents of the built-in deterministic gates

### M7.8 `plancritic templates` CLI (#175 — carried from M2/M3)

- `plancritic templates list` — shows installed precondition templates
- `plancritic templates add <name> --pattern <str> --task-id <id> --description <str>` — register a new template
- `plancritic templates test <name> <plan-file>` — dry-run the closer against a sample plan

### M7.0 Python decorator ergonomics (#137)

- `@planner_critic.guardrail(goal=..., dry_run=True, on_escalate=...)` — one-line function gating
- `@planner_critic.re_gate(precondition_key=..., on_drift=...)` — per-step precondition re-verification
- `@planner_critic.escalate` — escalation handler marker
- `EscalationRequired` / `PreconditionDrift` exception types

### Deferred to v0.3.0

The following items were deferred to the **v0.3.0** release as they are standalone UI/IDE surfaces with no downstream dependencies:

| # | Issue | Reason |
|---|-------|--------|
| 136 | Terminal UI (TUI) — `plancritic plan show --tui` | Standalone viewer; no downstream consumers |
| 154 | `planner-critic studio` — interactive debugger TUI | Builds on the TUI (#136) |
| 157 | IDE Extensions (VS Code + JetBrains) | Separate packaging/distribution; independent of engine |

### M7 Task Checklist

| # | Task | Verify | Issue | Status |
|---|------|--------|-------|--------|
| 1 | `plancritic diagnose` (rules engine + formats + OTel) | root cause + suggested fix on seeded trace; unclassified on unmatched | [#153](https://github.com/deghosal-2026/planner-critic-engine/issues/153) · [x] |
| 2 | `plancritic check` (offline gate eval + exit codes) | sub-second, $0; exit 0/1/4; severity threshold; JSON/YAML | [#162](https://github.com/deghosal-2026/planner-critic-engine/issues/162) · [x] |
| 3 | `plancritic domains` CLI (carried from M3) | list/show/add/test work against a real pack | [#178](https://github.com/deghosal-2026/planner-critic-engine/issues/178) · [x] |
| 4 | `plancritic policy` CLI + seed Rego lib (carried from M3) | list/add/test work; Rego policies fire alongside built-in gates | [#179](https://github.com/deghosal-2026/planner-critic-engine/issues/179) · [x] |
| 5 | `plancritic templates` CLI (carried from M2/M3) | list shows seed templates; add registers one; test dry-runs | [#175](https://github.com/deghosal-2026/planner-critic-engine/issues/175) · [x] |
| 6 | Python decorator ergonomics (#137) | `@guardrail`, `@re_gate`, `@escalate` work | [#137](https://github.com/deghosal-2026/planner-critic-engine/issues/137) · [x] |

### M7 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| Diagnosis quality | deterministic rules; no hallucinated root cause | seeded-trace suite (14 tests) |
| Check latency | <1s, $0 LLM | `plancritic check` bench |
| Coverage | >95% | `--cov-fail-under=95` |
| Lint | 0 ruff + 0 mypy strict | `ruff` + `mypy` |

### M7 Exit Gate

- [x] `plancritic check`, `plancritic diagnose`, `plancritic domains`, `plancritic policy`, `plancritic templates` CLIs implemented
- [x] Python decorator ergonomics shipped (`@guardrail`, `@re_gate`, `@escalate`)
- [x] Seed Rego policy library populated (4 built-in policies)
- [x] Redaction (#159) applied in `diagnose`/`check` output
- [x] **Design doc authored:** D25 (developer surfaces)
- [x] Coverage > 95; lint clean; code review passed
- [ ] TUI (#136), studio (#154), IDE extensions (#157) deferred to v0.3.0

**Dependency:** M1 (+ M6 redaction, M4 domain packs). **Produces for M8+:** the surfaces the CI/Backstage/webhook integrations build on, and the `plancritic check` command M8's GitHub Action consumes.