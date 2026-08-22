# WBS — PlannerCritic Engine v0.2.0 Part 6: Developer & Interactive Surfaces

> **Milestone covered:** M7 (Developer & Interactive Surfaces)
> **PRD covering this milestone:** [05-features](../../design/prd/05-features.md) (F-75 viz, F-76 replay, F-80 explain, F-61 CLI, F-62 HTTP) · [04-users-and-cujs](../../design/prd/04-users-and-cujs.md) (developer persona)

---

## Milestone 7: Developer & Interactive Surfaces

**Objective:** The engineer-experience stone — the surfaces a developer or platform engineer reaches for when debugging, adopting, or integrating a plan gate. In-terminal visualization, root-cause analysis, a live debugger, IDE integration, and the lightweight offline check those surfaces call. Everything is deterministic where possible ($0 LLM in the background surfaces).

**PRD coverage:** F-75/F-76 viz+replay, F-80 explain, F-61 CLI, F-79 pack format (diagnose rules). Consumes M6 redaction for `diagnose`/`studio` output.
**CUJs covered:** CUJ 5 (escalation explains), CUJ 10 (replay), developer + on-call personas.

### M7.1 Terminal UI (TUI) (#136)

- `plancritic plan show <id> --tui` / `replay --tui` using `textual` or `rich`: color-coded navigable DAG (red missing preconditions, orange blockers, green verified/rollback), per-revision critique-trail pane, revision-history tab, revision diff (F-78), replay step-through (F-76), Mermaid export.
- SSH-friendly; verified on iTerm2, gnome-terminal, Windows Terminal.

### M7.2 `plancritic diagnose` (#153)

- Sentry-style root-cause analyzer for **execution** traces (distinct from F-80's loop `explain`): parses `ExecutionTrace` → failing step, failure category (from `failure_class` + `reason_code`), severity, root cause, suggested fix, trace excerpt.
- Deterministic `DiagnosticRule` engine (no LLM narration); `unclassified_failure` when nothing matches; `--format human|json|markdown`; `--export-otel` (F-82); `plancritic diagnose rules add/list` (pack-extensible). Feeds missed-critique (#127) when a planning failure is identified.

### M7.3 `planner-critic studio` (#154)

- Interactive Textual TUI for live-debugging plan traces: time-travel step forward/back through revisions; live breakpoints (pause before a node's re-gate, edit `AgentState`, resume); synthetic plan editing (add/remove nodes + re-run gates in real-time, $0); node replay; `[D]` runs `diagnose`.
- Export `--format json|md|otel`; split-pane DAG + critique trail + controls. Builds on #136's TUI.

### M7.4 IDE Extensions (#157)

- VS Code (`planner-critic-code`) + JetBrains (`planner-critic-jetbrains`): inline plan simulation (right-click → critic check, deterministic $0), YAML/Rego schema autocompletion, Mermaid DAG WebView preview, and Debug Adapter Protocol integration launching `studio` as a native debug session.
- Spawns `plannercritic` as an LSP/stdin-stdout backend; never sends code to a cloud API; config via `planner-critic.*` settings.

### M7.5 `plancritic check` (#162)

- Lightweight, sub-second, **zero-LLM offline** gate evaluation against a plan file: `plancritic check <plan_file> [--domain PACK] [--policies-dir] [--enforcement] [--context] [--fail-on-severity] [--output json|text|yaml]`.
- Loads plan into a `SyntheticPlan`; runs domain-pack deterministic gates + Rego policies; exits 0 (pass / below threshold) / 1 (gate violation ≥ threshold) / 4 (config error). Reads `planner-critic.yaml`. **Integrates #157 (IDE backend) and #128 (CI lightweight path).**

### M7.6 `plancritic domains` CLI (#178 — carried from M3)

- `plancritic domains list` — shows installed packs from namespace scanning
- `plancritic domains show <name>` — displays pack details (gates, preconditions, prompt)
- `plancritic domains add <path>` — registers a `domain-pack.yaml`
- `plancritic domains test <name> <plan-file>` — dry-run domain gates against a file

### M7.7 `plancritic policy` CLI + seed Rego library (#179 — carried from M3)

- `plancritic policy list` — shows installed policy gates
- `plancritic policy add <path>` — registers a `policy-pack.yaml` or `.rego` file
- `plancritic policy test <name> <plan-file>` — dry-run a policy against a plan
- Populate `BUILTIN_POLICIES` with Rego equivalents of the six built-in gates

### M7.8 `plancritic templates` CLI (#175 — carried from M2/M3)

- `plancritic templates list` — shows installed precondition templates
- `plancritic templates add <name> --pattern <str> --task-id <id> --description <str>` — register a new template
- `plancritic templates test <name> <plan-file>` — dry-run the closer against a sample plan

### M7 Task Checklist

| # | Task | Verify | Issue | Status |
|---|------|--------|-------|--------|
| 1 | TUI (DAG + critique trail + history + replay + export) | navigable/colored; SSH-friendly; Mermaid export | [#136](https://github.com/deghosal-2026/planner-critic-engine/issues/136) · [ ] |
| 2 | `plancritic diagnose` (rules engine + formats + OTel) | root cause + suggested fix on seeded trace; unclassified on unmatched | [#153](https://github.com/deghosal-2026/planner-critic-engine/issues/153) · [ ] |
| 3 | `studio` (time-travel + breakpoints + synthetic edit + replay) | step-forward/back; pause+edit+resume; real-time gate update | [#154](https://github.com/deghosal-2026/planner-critic-engine/issues/154) · [ ] |
| 4 | IDE extensions (VS Code + JetBrains) | inline sim $0; schema autocomplete; DAG preview; DAP → studio | [#157](https://github.com/deghosal-2026/planner-critic-engine/issues/157) · [ ] |
| 5 | `plancritic check` (offline gate eval + exit codes) | sub-second, $0; exit 0/1/4; severity threshold; JSON/YAML | [#162](https://github.com/deghosal-2026/planner-critic-engine/issues/162) · [ ] |
| 6 | `plancritic domains` CLI (carried from M3) | list/show/add/test work against a real pack | [#178](https://github.com/deghosal-2026/planner-critic-engine/issues/178) · [ ] |
| 7 | `plancritic policy` CLI + seed Rego lib (carried from M3) | list/add/test work; Rego policies fire alongside built-in gates | [#179](https://github.com/deghosal-2026/planner-critic-engine/issues/179) · [ ] |
| 8 | `plancritic templates` CLI (carried from M2/M3) | list shows seed templates; add registers one; test dry-runs | [#175](https://github.com/deghosal-2026/planner-critic-engine/issues/175) · [ ] |

### M7 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| Diagnosis quality | deterministic rules; no hallucinated root cause | seeded-trace suite |
| Studio interactivity | time-travel + edit + replay work against a saved trace | studio test |
| Check latency | <1s, $0 LLM | `plancritic check` bench |
| IDE offline | 0 cloud API calls on simulation | extension smoke test |
| Coverage | >95% | `--cov-fail-under=95` |
| Lint | 0 ruff + 0 mypy strict | `ruff` + `mypy` |

### M7 Exit Gate

- [ ] All five surfaces run; `plancritic check` is the shared offline backend for IDE + CI
- [ ] Redaction (#159) applied in `diagnose`/`studio`/`check` output
- [ ] Coverage > 95; lint clean; code review passed
- [ ] **Design doc authored:** D25 (developer surfaces)

**Dependency:** M1 (+ M6 redaction, M4 domain packs). **Produces for M8+:** the surfaces the CI/Backstage/webhook integrations build on, and the `plancritic check` command M8's GitHub Action consumes.