# WBS — PlannerCritic Engine

Work Breakdown Structure — milestone plans and task breakdowns for all versions.

> **Live status:** v0.1.0 issues are attached to the [**0.1.0 release**](https://github.com/deghosal-2026/planner-critic-engine/milestone/1) GitHub milestone. M1 #1–10 and M2 #11–19 closed; M3 #20–29 code-complete (uncommitted); the rest open. Each WBS task row links its issue; flip the checkbox when closing the issue.

| File | Milestones | Version | GitHub Issues | Status |
|------|-----------|---------|---------------|--------|
| [v0.1.0/wbs-v0.1.0-index.md](v0.1.0/wbs-v0.1.0-index.md) | M1-M10 overview + package layout + design-doc plan + exit-gate standard (Index) | v0.1.0 | #1-84 | Active |
| [v0.1.0/wbs-v0.1.0-part1-engine-core.md](v0.1.0/wbs-v0.1.0-part1-engine-core.md) | M1-M2 (Core Engine + Store/Provider) | v0.1.0 | [#1-19](https://github.com/deghosal-2026/planner-critic-engine/issues/1) | Planned |
| [v0.1.0/wbs-v0.1.0-part2-critique-escalation.md](v0.1.0/wbs-v0.1.0-part2-critique-escalation.md) | M3-M4 (Critique + Escalation/Forensics/Replan) | v0.1.0 | [#20-39](https://github.com/deghosal-2026/planner-critic-engine/issues/20) | Planned |
| [v0.1.0/wbs-v0.1.0-part3-adapters-surfaces.md](v0.1.0/wbs-v0.1.0-part3-adapters-surfaces.md) | M5-M6 (Adapters + CLI/HTTP) | v0.1.0 | [#40-54](https://github.com/deghosal-2026/planner-critic-engine/issues/40) | Planned |
| [v0.1.0/wbs-v0.1.0-part4-demo.md](v0.1.0/wbs-v0.1.0-part4-demo.md) | M7 (Demo Corpus + Demo Runner) | v0.1.0 | [#55-58](https://github.com/deghosal-2026/planner-critic-engine/issues/55) | Planned |
| [v0.1.0/wbs-v0.1.0-part5-docker-integration.md](v0.1.0/wbs-v0.1.0-part5-docker-integration.md) | M8 (Docker Integration Tests — containerized engine + surfaces vs local LLM) | v0.1.0 | [#77-84](https://github.com/deghosal-2026/planner-critic-engine/issues/77) | Planned |
| [v0.1.0/wbs-v0.1.0-part6-field-test.md](v0.1.0/wbs-v0.1.0-part6-field-test.md) | M9 (Field Test — hermetic CI + local-model sweep) | v0.1.0 | [#59-64](https://github.com/deghosal-2026/planner-critic-engine/issues/59), [#74-76](https://github.com/deghosal-2026/planner-critic-engine/issues/74) | Planned |
| [v0.1.0/wbs-v0.1.0-part7-prerelease-release.md](v0.1.0/wbs-v0.1.0-part7-prerelease-release.md) | M10 (Pre-Release + Release — security, docs, packaging, ship) | v0.1.0 | [#65-71](https://github.com/deghosal-2026/planner-critic-engine/issues/65) | Planned |

## Exit Gate Checklist (Every Milestone)

- [ ] Code review passed on all files
- [ ] Every `.py` file has module-level and function-level docstrings with Args/Returns/Raises; inline comments on non-obvious control flow
- [ ] Test coverage >95% (`pytest --cov=planner_critic --cov-fail-under=95`)
- [ ] Ruff clean: `ruff check .` → 0 errors
- [ ] Mypy strict clean: `mypy --strict` → 0 errors

## Design Documents (authored inline with the milestones)

The PRD is a requirements doc, not a design spec. Each milestone authors the design docs for the subsystem it builds — see the index file's [Design Documents to Author](v0.1.0/wbs-v0.1.0-index.md#5-design-documents-to-author) table (D1–D18).