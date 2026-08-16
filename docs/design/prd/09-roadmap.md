# 09 — Roadmap (Milestone Sketch)

> Sub-document of the [Design overview](../README.md). The v0.1.0 release is deliberately feature-rich (see [05-features.md](05-features.md)).

## 9.1 v0.1.0 (P0) — the feature-rich first release

**Engine & critique:** core engine (F-01–F-13, F-74); provider registry + OpenAI-compatible transport (F-20–F-24); both critique modes; six heuristic families + deterministic gates; diff-aware critique (F-78).

**Adapters & execution:** six adapters *with* execution-time re-gate (F-40–F-46).

**Forensics:** plan–execution link + failure tagging (F-50); missed-critique record (F-51); suggested deterministic check (F-52).

**Delivery surfaces:** PyPI package (F-60); CLI with providers/plan/critique/escalate/plans/diff/replay/field-test (F-61); FastAPI HTTP service (F-62); SQLite store (F-63); MCP server (F-45).

**Viz & observability:** plan graph export (F-75); trace replay (F-76); reason-code catalog (F-77).

**Demo & field test:** domain-agnostic sample corpus (F-65); seeded-flaw demo trace (F-66); hermetic CI gate (F-67); local-model release field sweep (F-68).

**Reliability:** fail-closed modes (F-70, F-71, F-73).

**Security:** OWASP ASI01/02/05/08/09/10; OpenSSF Passing; PlannerCritic Essential.

**Shipped when CUJs 1–11 (P0) pass and the field-test matrix is green across all six frameworks against a local model.**

## 9.2 v0.2.0 (P1)

- AIDE-style web UI (F-33) — goal + plan + blocker + critique trail + revision history + inline editing
- Postgres store (F-64)
- Anthropic + Gemini transports (F-25)
- Critique heuristic packs (F-79) — community-extensible heuristic families
- `plancritic baseline check` + OpenSSF Silver + property-based fuzzing
- Automated missed-critique → standing-rule promotion interface (feeds LessonExtractor)
- **Security:** PlannerCritic Hardened; OpenSSF Silver.

## 9.3 v0.3.0 (P2)

- Multi-planner variants (deliberate, on user request)
- Planning-quality eval suite via EvalForge
- Fleet escalation analytics
- Plan-shape recommendation
- Tamper-evident plan store
- **Security:** PlannerCritic Certified (aspirational); external security review.

## 9.4 v0.4.0 (P3)

- SwarmOS coordination integration
- Community packs of critique heuristics (marketplace)
- Escalation-approval-rate dashboards
- OpenSSF Gold (aspirational).

## 9.5 WBS

The detailed work breakdown (milestones M1–M8 with issue ranges, exit gates, and dependency graph) lives in `docs/wbs/v0.1.0/` — authored next, after this PRD is approved.