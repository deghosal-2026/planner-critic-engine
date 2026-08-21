# CLI Surface — Field-Test Evidence (0.1.0, C5/C20/C22/C23)

> Dimension: **cli-surface** · Milestone: M1 (#85, 0.2.0) · Hermetic (no LLM) · Date: 2026-08-21

This directory records the field-test closure evidence for the CLI surface
dimension of the v0.1.0 field test. The 0.1.0 report previously listed
`cli-surface` / `cli-demo` / `cli-quickstart` / `cli-migrate` as
**"not run — Deferred to M10"**. This artifact documents the hermetic
verification that closes those gaps (live-provider happy paths remain
scoped to human/CI runs against a real endpoint).

## Capability-by-capability evidence

| Capability | Requirement (§ plan) | Hermetic verification | Result |
|------------|----------------------|-----------------------|--------|
| C5 CLI core | All subcommands dispatch through the CLI as faithful wrappers | `tests/test_cli_dispatch.py` — 11 subcommands registered + dispatched via `_cli.main` | ✅ PASS |
| C5 structural fidelity | CLI `plan` output structurally matches programmatic engine output | `tests/test_cli_plan.py` — `_CLIPlanner` output re-validates as `PlanVersion`; high-risk tasks carry rollback+verification; deps reference real tasks; gates pass | ✅ PASS |
| C20 demo run | `plancritic demo --format json` → machine-readable, exit 0 | `tests/test_cli_demo.py` — JSON payload (goal, draft+findings, approved, re_gate, replan, graph); `--no-graph` drops graph | ✅ PASS |
| C21 quickstart | Scaffold + run against a live provider; `plans.db` with ≥1 plan | Scaffold + fail-closed verified; happy path needs live provider | pass\* |
| C22 replay | Walk all revisions with per-revision findings; mermaid/json | `tests/test_cli_replay.py` — top-level CLI replay walks v1→v2 with findings (fixed via `PlanStore.get_findings`); json/mermaid formats | ✅ PASS |
| C23 migrate | Migrate to `SCHEMA_VERSION`; plan write succeeds; lossless revert | `tests/test_cli_migrate.py` — CLI migrate, plan write on migrated store, revert/reapply, `--revert` flag | ✅ PASS |

## Commits landing this closure

- `6da2ba4` — `feat(cli): add demo --format json (C20)`
- `fa91d08` — `test(cli): add top-level dispatch coverage for C5 field-test #85`
- (pending) — `fix(store): add get_findings protocol method + replay reads via it (C22/C15)`
- (pending) — `test(cli): add C23 migrate + C5 structural-fidelity + C22 full-walk coverage`

## Verified commands (sample transcript)

```
$ plancritic demo --format json --no-graph     # exit 0, parseable JSON payload
$ plancritic replay --store plan.db plan-b --format json   # exit 0, walks v1..v2 with findings
$ plancritic migrate --path plans.db           # exit 0, "schema at v3"
$ plancritic migrate --path plans.db --revert --to 1       # exit 0, "reverted to schema v1"
```

## Remaining (non-hermetic) scope for #85

- **C21 happy path** — `plancritic quickstart` against a live provider producing
  `.plancritic/plans.db` with ≥1 stored plan. Needs an OpenAI-compatible
  endpoint; covered by the CLI unit tests only in fail-closed form.
- **C5 CLI-vs-engine equality on a live plan** — structural-match of CLI `plan`
  output vs programmatic `engine.plan()` on a real LLM-generated plan. The
  hermetic `_CLIPlanner` fidelity test is the offline proxy.

These two items are flagged in the field-test report as `pass*` / documented
caveats rather than run hermetically.