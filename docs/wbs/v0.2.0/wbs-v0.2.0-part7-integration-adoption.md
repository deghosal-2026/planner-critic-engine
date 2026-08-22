# WBS — PlannerCritic Engine v0.2.0 Part 7: Enterprise Integration & Adoption

> **Milestone covered:** M8 (Enterprise Integration & Adoption)
> **PRD coverage:** [05-features](../../design/prd/05-features.md) (F-14 shadow, F-30 escalation, F-33 web UI, F-62 HTTP, F-45 MCP, F-82 OTel) · [03-landscape](../../design/prd/03-landscape.md) (adjacent frameworks) · [04-users-and-cujs](../../design/prd/04-users-and-cujs.md)

---

## Milestone 8: Enterprise Integration & Adoption

**Objective:** The distribution-and-adoption stone — put `plancritic` where the platform team, on-call, and fleet lead already operate: PR checks, a multi-agent framework (AutoGen), and a webhook event bridge. Consumes M7's `plancritic check` and the M6 safety/quota layer.

**PRD coverage:** F-14 shadow mode (productized as CI observe→enforce), F-30 escalation surfaces, F-62 HTTP, F-45 MCP, F-82 OTel.
**CUJs covered:** CUJ 1/15 (install + platform lead), on-call persona, platform-engineer persona.

### M8.1 GitHub Action / GitLab CI runner (#128)

- First-party `action.yml` + GitLab CI template running `plancritic check` on PR-scoped changes; emits a PR status check (`planner-critic / plan`) — **blocker→fail, escalation→neutral, approve→success** — plus inline annotations on flagged files and a trace artifact.
- `goal_template` auto-derivation from changed files (covers infra PRs with no manual goal). Shadow mode never fails the check (observe before enforce). Uses `plancritic check` (#162) for the deterministic-only fast path.

### M8.3 AutoGen adapter (#134)

- `AutoGenAdapter` — the missing seventh framework matching F-40–F-44: pre-execution gate + per-step re-gate (F-46) + escalation-via-Human-message + plan-artifact parsing to typed `PlanVersion`. Bounds AutoGen's unbounded group-chat reviewer conversation.

### M8.5 Webhook Event Bridge — notifier (#161)

- `planner-critic-notifier`: stateless CloudEvents-capable notifier with per-platform formatters (Slack Block Kit, Teams Adaptive Card v1.4, generic webhook) → **HMAC-verified interactive callbacks** (Slack `X-Slack-Signature` + replay protection; Teams JWT) proxying decisions to the escalation API.
- At-least-once delivery (3 retries, exp backoff, `escalation_id` dedup 5min).

### M8.6 Finding drift observability (#181)

- Dual severity storage on every Finding (raw_severity + normalized_severity + drift_delta) so label-migration drift surfaces as data, not a surprise audit.
- Escalation payload enrichment (drift summary + per-finding dual-severity card in Slack, Teams, webhook events).
- Fleet dashboard drift panel: time-series downgrade rate, family breakout, critical_underclaim_watch for the under-claim direction.
- CLI `plancritic findings --include-raw` flag.
- Nightly z-score drift check with dashboard badge on 2-sigma breach.

### Deferred to v0.3.0

| # | Issue | Reason |
|---|-------|--------|
| 133 | Backstage developer portal plugin | Separate npm package; no engine dependencies |
| 135 | Slack escalation bot | Standalone service; builds on notifier (#161, done) |
| 138 | Fleet convergence & risk dashboard | Standalone web UI; M9 field-tests run independently |

### M8 Task Checklist

| # | Task | Verify | Issue | Status |
|---|------|--------|-------|--------|
| 1 | GitHub Action + GitLab template + goal_template + artifact | PR status mapping correct; shadow never fails; check #162 integrated | [#128](https://github.com/deghosal-2026/planner-critic-engine/issues/128) · [x] |
| 2 | AutoGen adapter | pre-gate + re-gate + Human escalation; same pattern as F-41–44 | [#134](https://github.com/deghosal-2026/planner-critic-engine/issues/134) · [x] |
| 3 | CloudEvents notifier (Slack/Teams/webhook + HMAC) | multi-surface delivery; HMAC/JWT verified callbacks; at-least-once | [#161](https://github.com/deghosal-2026/planner-critic-engine/issues/161) · [x] |
| 4 | Finding drift observability | dual severity storage + escalation enrichment + dashboard drift panel + CLI --include-raw | [#181](https://github.com/deghosal-2026/planner-critic-engine/issues/181) · [ ] |

### M8 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| CI gate | every infra PR gets a `planner-critic/plan` check | action.yml + GitLab template |
| Callback security | HMAC/JWT verified; stale callbacks rejected | notifier tests |
| Multi-surface | Slack + Teams + generic webhook formatters | notifier tests |
| Coverage | >95% | `--cov-fail-under=95` |
| Lint | 0 ruff + 0 mypy strict | `ruff` + `mypy` |

### M8 Exit Gate

- [x] CI runner (GitHub Action + GitLab template) shipped
- [x] AutoGen adapter shipped (pre-gate + re-gate + escalation)
- [x] Webhook event bridge shipped (Slack/Teams/webhook formatters + HMAC verification)
- [x] **Design doc authored:** D26 (integration surfaces)
- [x] Coverage > 95; lint clean; code review passed
- [ ] Drift observability: dual severity storage, escalation enrichment, dashboard drift panel, CLI --include-raw (#181)
- [ ] Backstage plugin (#133), Slack bot (#135), fleet dashboard (#138) deferred to v0.3.0

**Dependency:** M1 (+ M6 safety, M7 `plancritic check`, M4 packs). **Produces for M9–M10:** the CI distribution channel and notifier infrastructure that M9's fleet field-tests and M10's release gate validate.