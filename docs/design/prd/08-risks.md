# 08 — Risks & Open Questions

> Sub-document of the [PlannerCritic Engine PRD](../PRD.md).

- **Critic shares the planner's blind spots** (both are LLMs) — mitigated by separate roles, recommended different model family, bounded loop, regression guard, and the missed-critique feedback loop.
- **Critic can be net-negative** (research: a critic re-reading the same context with the same model family can disrupt more than it recovers — a 26-pp collapse case exists) — mitigated by typed rubric + deterministic gates + per-goal thresholds; validate on the field corpus before deployment.
- **Converging too easily or too rarely** — the convergence detector + regression guard bound both; thresholds tuneable.
- **Designing escalations that are genuinely minimal, not nagging** — the single-question + full-context panel is the design; audited for precision in tests.
- **Scope of v0.1 is large** (engine + provider registry + two critique modes + six adapters *with* re-gate + forensics + viz + replay + diff-aware critique + reason codes + security baseline + field test) — sequenced inside the WBS so the engine is testable before the breadth lands; risk is schedule, not architecture.
- **Planner and critic as separate model families at v0.1** — technically cheap (config), but the *default* demo should pick a free/local pairing that demonstrates cross-family critique.
- **Fairness of the demo corpus** — the seeded-flaw goals must be genuinely hard (blade-length ordering, unverified deps) so the critic's catch is credible, not staged.
- **Adversarial goals / prompt injection** — the LLM critic reads the goal text and is therefore injectable; a goal crafted to corrupt the plan cannot weaken the deterministic gates (they're code), but *can* bias the LLM critic. Mitigation: deterministic gates always run and cannot be skipped; a blocker from the deterministic layer cannot be overridden by the LLM; the field-test matrix includes an adversarial goal that attempts to suppress a blocker.
- **Diff-aware critique could miss context-only issues** — re-auditing only changed tasks + dependents is a cost optimization, not a correctness guarantee; a changed task can affect a *non-dependent* task semantically. Mitigation: `critic.mode=llm-every-revision` is the escape hatch for audit-critical goals; the default mode documents the trade-off.
- **Re-gate cost on long plans** — `before-each-step` re-verification adds an LLM call per step; mitigation: `re-gate: off` for cheap goals, and the deterministic gates cover structural preconditions for free.