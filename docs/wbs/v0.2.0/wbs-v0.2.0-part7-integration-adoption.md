# WBS — PlannerCritic Engine v0.2.0 Part 7: Enterprise Integration & Adoption

> **Milestone covered:** M8 (Enterprise Integration & Adoption)
> **PRD covering this milestone:** [05-features](../../design/prd/05-features.md) (F-14 shadow, F-30 escalation, F-33 web UI, F-62 HTTP, F-45 MCP, F-82 OTel) · [03-landscape](../../design/prd/03-landscape.md) (adjacent frameworks) · [04-users-and-cujs](../../design/prd/04-users-and-cujs.md)

---

## Milestone 8: Enterprise Integration & Adoption

**Objective:** The distribution-and-adoption stone — put `plancritic` where the platform team, on-call, and fleet lead already operate: PR checks, the IDP (Backstage), a multi-agent framework (AutoGen), chat (Slack + webhook notifier), and a fleet dashboard. This is the "every infra PR gets a gate" + "escalation where the human lives" story. Parallelizable with M7; consumes M7's `plancritic check` and the M6 safety/quota layer.

**PRD coverage:** F-14 shadow mode (productized as CI observe→enforce), F-30 escalation surfaces, F-62 HTTP, F-45 MCP, F-82 OTel.
**CUJs covered:** CUJ 1/15 (install + platform lead), on-call persona, platform-engineer persona.

### M8.1 GitHub Action / GitLab CI runner (#128)

- First-party `action.yml` + GitLab template running `plancritic plan --dry-run` (or enforce) on PR-scoped changes; emits a PR status check (`planner-critic / plan`) — **blocker→fail, escalation→neutral, approve→success** — plus inline annotations on flagged files and a trace artifact.
- `goal_template` auto-derivation from changed files (covers infra PRs with no manual goal). Shadow mode never fails the check (observe before enforce). Uses `plancritic check` (#162) for the deterministic-only fast path.

### M8.2 Backstage developer portal plugin (#133)

- `@planner-critic/backstage-plugin`: Plan Health Card (service page tab), Risk Posture Widget (from #132), Escalation Queue (global page, approve/deny from Backstage via F-62 HTTP), Plan Trace Viewer (F-75 Mermaid + F-76 replay inline).
- Backend proxy to the FastAPI service; no direct DB access; Backstage identity → API auth (approve/deny attributed); `app-config.yaml` service mappings.

### M8.3 AutoGen adapter (#134)

- `AutoGenAdapter` — the missing seventh framework matching F-40–F-44: pre-execution gate + per-step re-gate (F-46) + escalation-via-Human-message + plan-artifact parsing to typed `PlanVersion`. Registers via `plancritic adapters add autogen`. Bounds AutoGen's unbounded group-chat reviewer conversation.

### M8.4 Slack escalation surface (#135)

- `planner-critic-slack` bot: posts the F-30 minimal precise question + plan summary (Slack blocks) with **Approve / Deny / Patch** buttons; actions call F-62 (`/escalations/{id}/approve|deny`), Patch opens a modal; resolution recorded (F-34) + confirmation posted. Routing severity → channel/DM; on-call rotation (PagerDuty/Opsgenie) optional; Slack user = resolver in audit trail.

### M8.5 Webhook Event Bridge — notifier (#161)

- `planner-critic-notifier`: stateless CloudEvents v1.0 listener (`POST /v1/events/escalation`) → per-platform formatters (Slack Block Kit, Teams Adaptive Card v1.4, generic webhook) → **HMAC-verified interactive callbacks** (Slack `X-Slack-Signature` + replay protection; Teams JWT) proxying decisions to the Backstage API (`/v1/escalations/{id}/decision`), resolver = platform user.
- At-least-once delivery (3 retries, exp backoff, `escalation_id` dedup 5min); `notifier.yaml` config; `/health`. Extends #135 from Slack-only to multi-surface.

### M8.6 Fleet convergence & risk dashboard (#138)

- `plancritic dashboard` (standalone FastAPI+React/Vue served alongside F-62) + Grafana panel-pack JSON: **Escalation Rate, Avg Loop Iterations, Top Blocker Categories, Missed-Critique Rate, Plan-Execution Failure Split** sourced from plan store (F-09) + OTel (F-82). Slicing by service/env/model/time-window. Alerting hook (`--threshold` → webhook/Slack). Revision-iteration distribution shows the tail (histogram).

### M8 Task Checklist

| # | Task | Verify | Issue | Status |
|---|------|--------|-------|--------|
| 1 | GitHub Action + GitLab template + goal_template + artifact | PR status mapping correct; shadow never fails; check #162 integrated | [#128](https://github.com/deghosal-2026/planner-critic-engine/issues/128) · [ ] |
| 2 | Backstage plugin (cards, queue, trace viewer) | approve/deny works; posture widget reads #132; proxy no-DB | [#133](https://github.com/deghosal-2026/planner-critic-engine/issues/133) · [ ] |
| 3 | AutoGen adapter | pre-gate + re-gate + Human escalation; same pattern as F-41–44 | [#134](https://github.com/deghosal-2026/planner-critic-engine/issues/134) · [ ] |
| 4 | Slack escalation surface | approve/deny/patch from chat; resolver recorded; routing | [#135](https://github.com/deghosal-2026/planner-critic-engine/issues/135) · [ ] |
| 5 | CloudEvents notifier (Slack/Teams/webhook + HMAC) | multi-surface delivery; HMAC/JWT verified callbacks; at-least-once | [#161](https://github.com/deghosal-2026/planner-critic-engine/issues/161) · [ ] |
| 6 | Fleet dashboard + Grafana pack + alerting | 5 metrics from real store data; slicing + tail histogram | [#138](https://github.com/deghosal-2026/planner-critic-engine/issues/138) · [ ] |

### M8 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| CI gate | every infra PR gets a `planner-critic/plan` check | action/e2e on a real PR |
| Escalation latency | resolve from chat / portal, no terminal/context switch | Slack + Backstage e2e |
| Callback security | HMAC/JWT verified; stale callbacks rejected | notifier tests |
| Multi-surface | Slack + Teams + generic webhook | notifier e2e |
| Dashboard | 5 metrics from real plan-store data, not synthetic | dashboard test |
| Coverage | >95% | `--cov-fail-under=95` |
| Lint | 0 ruff + 0 mypy strict | `ruff` + `mypy` |

### M8 Exit Gate

- [ ] CI runner, Backstage, AutoGen, Slack + notifier, and dashboard all exercised
- [ ] Escalation decision callbacks cryptographically verified (no impersonation)
- [ ] Coverage > 95; lint clean; code review passed
- [ ] **Design doc authored:** D26 (integration surfaces)

**Dependency:** M1 (+ M6 safety, M7 `plancritic check`, M4 packs). **Produces for M9–M10:** the distribution channel and dashboard that M9's fleet field-tests and M10's release gate validate.