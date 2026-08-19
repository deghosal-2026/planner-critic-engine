# Design Doc D11 — Demo Corpus + Demo Runner (M7)

> **Milestone:** M7 — Demo Corpus + Demo Runner
> **Features:** F-65 (sample corpus), F-66 (demo trace), F-86 (`plancritic demo` runner)
> **CUJ:** CUJ 14 (watch the full loop run end-to-end)
> **Author:** Debashish Ghosal · **Date:** 2026-08-18 · **Status:** Approved
> **PRDs:** [02-architecture §2.9](../../design/prd/02-architecture.md) · [04-users-and-cujs CUJ 14](../../design/prd/04-users-and-cujs.md)
> **WBS:** [part4-demo](../../wbs/v0.1.0/wbs-v0.1.0-part4-demo.md)

---

## 1. Objective

Make the value of the engine *visible*: a domain-agnostic sample corpus with
documented seeded flaws (the honest "aha" demo) and a `plancritic demo`
runner that shows **plan → approve → execute → re-gate → replan → complete**
end-to-end — hermetic, fully offline, deterministic, $0 LLM spend.

## 2. Design Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| DD-M7-01 | Demo surfaces as a `plancritic demo` **subcommand**, not a separate `plannercritic-demo` script | WBS names `plannercritic-demo`, but the repo ships a single `plancritic` entry point (`pyproject.toml`); a subcommand reuses existing CLI/store/test plumbing and keeps packaging simple. |
| DD-M7-02 | Demo runner is **hermetic** — scripted planner/critic roles, no LLM | Project contract: *cheap by default, $0 LLM in CI*. The runner drives the real loop, re-gate, and replan code deterministically everywhere. Real-model sweeps belong to M9 field test. |
| DD-M7-03 | Corpus goals are **JSON** | `plancritic plan` reads JSON natively (`json.loads`); PyYAML is dev-only. Zero new runtime dependency. |
| DD-M7-04 | Drift is an **EnvVarProbe + env-var flip** | M4 already ships `probe/env_var.py`; no new probe code. Namespace-scoped var name avoids colliding with user env. |
| DD-M7-05 | Demo covers the **full loop incl. replan** — stops only on policy `abort` | Faithful to the WBS narrative; the abort path is shown as an honest fail-closed terminal state. |
| DD-M7-06 | Demo runner lives in `src/planner_critic/demo/`; `examples/` ships only the corpus | Hatch wheel ships `src/planner_critic`; a CLI coupling into `examples/` would be unpackageable. `examples/demo-runner/` holds a thin usage example only. |
| DD-M7-07 | Corpus JSON carries `_seeded_flaw` + `_doc` fields | Self-describing corpus; tests assert exactly one documented flaw per goal. Unknown fields are tolerated (Model extra is ignored) so these do not break `Goal` validation. |

> With the exception of DD-M7-06 (a refinement of the earlier "Approach A —
> scripted roles" proposal to keep the CLI deps packageable), these decisions
> implement the approved design verbatim.

## 3. Corpus — `examples/goals/*.json`

Five goals, each valid against the `Goal` schema (`id`, `description`,
`constraints`, `risk_tolerance`, `replan_policy`, `approval_ttl`, `metadata`),
each declaring exactly one documented `_seeded_flaw`:

| File | id | Seeded flaw | Heuristic family |
|------|----|-------------|------------------|
| `migration.json` | `demo-migration` | DB-schema backup/verify step missing before cutover | missing_steps |
| `rollout.json` | `demo-rollout` | rollback window opens only after 50% of steps | unsafe_sequencing |
| `refactor.json` | `demo-refactor` | booked window assumed but never probe-verified | unverified_dependencies |
| `incident.json` | `demo-incident` | no mitigation-verification for irreversible write | weak_rollback |
| `adversarial.json` | `demo-adversarial` | deterministic-gate blocker (M9 adversarial goal) | feasibility/structural |

Each file adds a `"_doc"` string (plain-English description of the scenario)
and a `"_seeded_flaw"` object:

```json
{
  "id": "demo-migration",
  "description": "...",
  "constraints": { "environment": "...", "tools": ["..."] },
  "risk_tolerance": "balanced",
  "replan_policy": "patch",
  "_seeded_flaw": {
    "family": "missing_steps",
    "severity": "warning",
    "description": "no step backs up the schema or verifies compatibility before cutover"
  },
  "_doc": "Migration scenario used by `plancritic demo`."
}
```

## 4. Scripted roles — `src/planner_critic/demo/roles.py`

Two deterministic implementations of the M3 role protocols (no LLM):

- **`ScriptedPlanner(PlannerRole)`**
  - `decompose(goal)` → builds the canned **v1** `PlanVersion` for the given
    corpus goal, containing the seeded flaw (e.g. migration cutover task with
    no backup/verify step).
  - `revise(plan, findings)` → returns **v2** with the flaw fixed (adds the
    missing verification step / reorders the offending tasks), so revision 2
    passes the critic.
- **`ScriptedCritic(CriticRole)`**
  - `audit(plan, findings)` → for revision 1 returns the seeded `Finding`
    (blocker/warning per the flaw, correct `heuristic_family` + `reason_code`,
    `task_id` pointing at the flawed task); for later revisions returns `[]`
    (approval path). A per-plan revision counter makes this deterministic.

These are the only "new logic" in M7; everything downstream is the real
engine (loop → approval), the real re-gate, and the real replan.

## 5. Demo flow — `src/planner_critic/demo/runner.py`

`run_demo(goal_path, store, *, no_graph=False) -> int` returns a process exit
code and prints the narrative. `narrative(...) -> list[str]` is a pure,
testable function that returns the ordered lines.

1. **Load + validate** the corpus goal via `Goal.model_validate`; on failure
   print `demo failed: <goal_path> is not a valid Goal` and return 1.
2. **Seed the precondition** — set the env var `PC_DEMO_MAINTENANCE_WINDOW`
   (namespace-scoped, per goal's probe `expected`) so the precondition passes
   at plan time.
3. **Plan** — `Engine(ScriptedPlanner, ScriptedCritic).plan(goal)`; the loop
   runs the deterministic gates, the critic flags revision 1, the planner
   revises, revision 2 is approved. Persist v1, v2, findings to the store.
4. **Execute + drift** — record execution (`ExecutionRecorder`), then **flip
   the env var** to the drifted value and call
   `check_preconditions(approved, drifted_task_id, store,
   ReGateConfig(mode="before-each-step"))` → `status == "stale"`, with the
   stale precondition reported.
5. **Replan** — call `planner.revise` again → `replan(goal, current, revised)`
   stamps the bumped version + parent link (real F-16 code, patch policy);
   persist the revised plan. If the goal policy were `abort`, `ReplanAbort`
   surfaces and the narrative stops there (fail-closed demonstration).
6. **Narrative + visuals** — print the five-stage narrative (findings →
   approval → re-gate staleness → replan → complete), then `replay --step`
   text and the Mermaid DAG (reusing `cli/replay.py` and the existing
   `viz` graph export) unless `--no-graph`.

**Store fallback:** if the SQLite store is unavailable, warn and continue with
`InMemoryStore` (the plan-store side-channel contract, store/base.py).

## 6. `plancritic demo` subcommand — `src/planner_critic/cli/demo.py`

Follows the existing subcommand pattern (`build_demo_parser` +
`run_demo`), wired into `cli/__init__.py` and `_cli.py`.

```
plancritic demo [--goal examples/goals/migration.json] [--store .plancritic/plans.db] [--no-graph]
```

- `--goal` defaults to the packaged `examples/goals/migration.json` (the
  "aha" migration scenario).
- `--store` defaults to `.plancritic/plans.db`.
- `--no-graph` skips the Mermaid/step rendering (plain text narrative only).
- Returns 0 on a completed narrative; 1 on a goal-validation failure.

`examples/demo-runner/` ships only a thin usage example (`main.py`) that calls
`planner_critic.demo.runner.run_demo` so the WBS's "runner" is still
discoverable — no package coupling.

## 7. `init` change (M7 task 3)

`cli/init.py` additionally writes `.plancritic/goal.json` (a copy of the
corpus `examples/goals/migration.json`) and prints:

```
Run: plancritic plan .plancritic/goal.json
```

so `plancritic init` → `plancritic plan` works immediately with no extra
config, satisfying F-85/F-86 without coupling `init` to corpus packaging.

## 8. Error handling

- Invalid corpus goal → `demo failed: ... not a valid Goal`, exit 1.
- Store unavailable → warn + continue in-memory.
- Replan policy `abort` → `ReplanAbort` surfaces; narrative stops at the
  abort (honest fail-closed path).
- Unexpected provider/engine failure → `PlanningError` surfaces as
  `planning_unavailable` per role; exit 1.

## 9. Testing

- `tests/test_corpus.py` — every corpus goal parses via `Goal.model_validate`;
  exactly one `_seeded_flaw` each; ids unique + stable.
- `tests/test_demo.py` — hermetic full run: reaches approval at v2, drift
  flips re-gate to `stale`, replan bumps version with a parent link, narrative
  contains all five stages, no network/LLM. Also covers the `InMemoryStore`
  fallback path.
- `tests/test_cli_demo.py` — subcommand wiring (parser + exit codes).
- Full suite green: `pytest` (+ coverage > 95%), `ruff check .`,
  `mypy --strict` — per the WBS M7 exit gate.

## 10. Success metrics (from the WBS M7 gate)

- Corpus validity: all goals parse against the Goal schema — `test_corpus`.
- Demo end-to-end: `plancritic demo` → full five-stage loop visible.
- init + demo: `init` → `plan` → immediate first approved plan.
- Coverage > 95%, lint clean (ruff + mypy strict), hermetic $0 LLM.

## 11. Non-goals / deferrals

- Real-model demo sweeps → M9 field test (`plancritic field-test`, OMLX/Ollama).
- Web UI, Postgres store, etc. → v0.2.0 (PRD 09 §9.2).
- No new runtime dependency, no new console entry point.