# WBS — PlannerCritic Engine v0.1.0 Part 4: Demo Corpus + Demo Runner

> **Milestone covered:** M7
> **PRD covering this milestone:** [02-architecture](../../design/prd/02-architecture.md) (§2.9 demo corpus) · [04-users-and-cujs](../../design/prd/04-users-and-cujs.md) (CUJ 14)

---

## Milestone 7: Demo Corpus + Demo Runner — make the value visible

**Objective:** The domain-agnostic sample corpus with seeded flaws (the honest "aha" demo) and the `plannercritic-demo` reference runner that shows plan→approve→re-gate→execute→replan→complete end-to-end with a seeded precondition drift — all against a stub executor (no framework required).

**PRD coverage:** F-65, F-66, F-86
**CUJs covered:** CUJ 14 (watch the full loop run end-to-end)

### M7 Design Documents

- **D11 — Demo scenario** (`docs/design/demo-scenario.md`): walkthrough of `plannercritic-demo`, the seeded drift that triggers re-gate, the replan visible in the trace.

### M7 Key Items (explicitly called out)

- **Sample corpus** (F-65, [§2.9](../../design/prd/02-architecture.md#29-demo-corpus-seeded-flaws)): `examples/goals/` — four goals (migration, rollout, refactor, incident-response), each YAML/JSON with a documented seeded flaw the critic must catch: missing DB-schema verification (missing steps), rollback after 50% step (unsafe sequencing), unbooked outage window (unverified deps), no mitigation-verification (weak rollback). Plus one adversarial goal ([§8](../../design/prd/08-risks.md)).
- **Demo trace** (F-66): the seeded flaw → caught → revised → approved/escalated narrative.
- **`plannercritic-demo` runner** (F-86, [§CUJ14](../../design/prd/04-users-and-cujs.md#cuj-14--watch-the-full-loop-run-end-to-end-the-demo-runner)): `examples/demo-runner/` — stub executor (no framework); seeds a precondition drift mid-run so the re-gate fires and a defined replan is visible; plan→approve→re-gate→execute(drift)→replan→complete. The default `plancritic init` example goal points here.

### M7 Task Checklist

| # | Task | Build (files) | Behavior + edge cases | Feature | Verify | Status |
|---|------|---------------|----------------------|---------|--------|--------|
| 1 | Sample corpus | Create `examples/goals/` (migration.yaml, rollout.yaml, refactor.yaml, incident.yaml, adversarial.yaml) | 4 seeded-flaw goals + 1 adversarial; each valid against Goal schema; each seeded flaw documented in the file as a comment | F-65 | all parse; seeded flaws documented | [#55](https://github.com/deghosal-2026/planner-critic-engine/issues/55) · - [x] |
| 2 | Demo runner | Create `examples/demo-runner/` (main.py or script) | stub executor; plan→approve→re-gate (seeded precondition drift from an EnvProbe) → replan (patch) → complete; prints narrative | F-86 | demo script reproduces full loop; replan visible | [#56](https://github.com/deghosal-2026/planner-critic-engine/issues/56) · - [x] |
| 3 | Demo as init example | Modify `planner_critic/cli/init.py` to reference demo corpus goal | `init` points the example goal at a corpus goal so `plancritic plan` works immediately after `init` | F-85, F-86 | `init` → `plan` → first result without extra config | [#57](https://github.com/deghosal-2026/planner-critic-engine/issues/57) · - [x] |
| 4 | Replay + graph in demo | Demonstration script uses `replay --step` and `--graph` in its output | The demo narrative shows the catch *watchable*, not just reported — replay trace + DAG rendered inline | F-76, F-75 | demo output includes replay steps + Mermaid | [#58](https://github.com/deghosal-2026/planner-critic-engine/issues/58) · - [x] |

### M7 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| Corpus validity | all goals parse against Goal schema | schema validation test |
| Demo end-to-end | `plannercritic-demo` → full loop visible | demo run |
| init + demo | `init` → `plan` → immediate result | CUJ 1 + CUJ 14 combined test |
| Coverage | no regression on existing >95% | CI coverage gate |
| Lint | 0 ruff + 0 mypy strict | `ruff` + `mypy` |

### M7 Exit Gate

- [ ] Code review passed (demo script review now, corpus YAML validation review)
- [ ] Coverage > 95% maintained
- [x] Lint clean (ruff + mypy strict)
- [x] Comments + docstrings in all code (demo script well-documented)
- [x] `plannercritic-demo` runs plan→approve→re-gate→replan→complete end-to-end
- [ ] `init` example goal → `plan` gives immediate first approved plan
- [x] **Design doc authored:** D11 (demo scenario)

**Dependency:** M5 (six adapters — demo re-gate needs re-gate, runner uses adapter) + M6 (CLI init + plan). **Produces for M8/M9/M10:** corpus fixtures, demo runner, init-example linkage.