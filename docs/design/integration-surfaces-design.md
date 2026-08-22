# Design D26 — Enterprise Integration & Adoption Surfaces

> **As-built design for M8 (v0.2.0)** · Covers GitHub Action, GitLab CI, Backstage plugin, AutoGen adapter, Slack escalation, webhook notifier, and fleet dashboard.

---

## 1. CI Integration

### GitHub Action (`action.yml`)

A composite action that runs `plancritic check` on PR changes. Features:

- **Goal auto-derivation**: if no explicit goal is given, derives one from changed files.
- **Shadow mode**: `mode: shadow` never fails the check (observe before enforce).
- **PR status check**: `planner-critic / plan` — `success` on pass, `failure` on violation, `neutral` on config error.
- **PR comment**: posts a summary table of findings as a PR comment.
- **Artifact**: uploads the full JSON report.

### GitLab CI Template (`.gitlab-ci.yml-planner-critic.yml`)

A CI include template with the same behavior. `allow_failure` is `true` in shadow mode, `false` in enforce mode. Generates a `plancritic-report.json` artifact.

---

## 2. AutoGen Adapter

Module: `adapters/autogen.py`

```python
adapter = AutoGenAdapter(engine)
result = adapter.gate_plan(goal)
if result.is_approved:
    adapter.execute_step(step_id, agent_turn)
```

- **Pre-execution gate**: `gate_plan()` runs the planner-critique loop. Raises `PlanNotApprovedError` on escalation.
- **Per-step re-gate**: `execute_step()` re-verifies preconditions before each step. Raises `PreconditionDriftError` on drift.
- **Escalation surface**: `escalation_message()` returns the human-readable question for posting to AutoGen's Human-in-the-loop message.
- **Audit trail**: records `plan_requested`, `plan_approved`, `re_gate_check` events.

---

## 3. Webhook Event Bridge (`notifier.py`)

### Architecture

```
Engine → EscalationEvent → Notifier → SlackFormatter → Slack Webhook
                                   → TeamsFormatter → Teams Webhook
                                   → WebhookFormatter → Generic Webhook
```

### EscalationEvent

```python
@dataclass
class EscalationEvent:
    escalation_id: str
    plan_id: str
    reason_code: str
    question: str
    severity: str
    environment: str
    service: str
    summary: str
    backstage_url: str | None
```

### Surface Formatters

| Formatter | Platform | Message Format | Interactive Callbacks |
|-----------|----------|---------------|----------------------|
| `SlackFormatter` | Slack | Block Kit with approve/deny/review buttons | HMAC-SHA256 signature verification |
| `TeamsFormatter` | MS Teams | Adaptive Card v1.4 with Action.Http | JWT bearer token verification |
| `WebhookFormatter` | Generic | Plain JSON event payload | None |

### Notifier

- **At-least-once delivery**: 3 retries with exponential backoff.
- **Dedup**: 5-minute window per `(escalation_id, plan_id)`.
- **Registration**: `notifier.register("slack", SlackFormatter(url, secret))`.

---

## 4. Slack Escalation Surface

The Slack bot delivers escalation questions as messages with interactive buttons:

- **Approve**: calls `POST /escalations/{id}/approve`, records resolver.
- **Deny**: calls `POST /escalations/{id}/deny`, records resolver.
- **Patch**: opens a modal for inline plan editing.
- **Routing**: severity → channel mapping (`#ops-escalations` for blockers).
- **Auth**: Slack workspace token → PlannerCritic API auth.

---

## 5. Backstage Plugin

`@planner-critic/backstage-plugin` provides:

- **Plan Health Card** (service page tab): latest plan verdicts.
- **Risk Posture Widget** (service overview): current posture + resolving rule.
- **Escalation Queue** (global page): all pending escalations with approve/deny.
- **Plan Trace Viewer** (deep link): Mermaid DAG + critique trail inline.

Backend proxy to the FastAPI service; no direct DB access. Backstage identity → API auth.

---

## 6. Fleet Dashboard

`plancritic dashboard` provides:

- **Escalation Rate**: escalations / total plans, over time, per service/env.
- **Average Loop Iterations**: mean revisions-to-approval + histogram.
- **Top Blocker Categories**: bar chart of most common reason codes.
- **Missed-Critique Rate**: critic-approve-but-execution-fail trend.
- **Plan-Execution Failure Split**: planning vs execution failure ratio.

Grafana panel pack JSON also available for orgs with existing Grafana.

---

## 7. Design Decisions

1. **CI is `plancritic check`-based**: the same zero-LLM command powers the GitHub Action, GitLab CI, and IDE extension — one shared backend.
2. **Notifier is stateless**: no database, no persistence — just format + deliver + retry. State lives in the plan store.
3. **HMAC verification for Slack callbacks**: prevents forged approve/deny actions. Replay protection via timestamp check.
4. **AutoGen adapter follows the existing adapter pattern**: same `AuditTrail`, same `PlanNotApprovedError` pattern as LangGraph adapter.
5. **Backstage plugin is a separate npm package**: decoupled from the Python engine; communicates via the HTTP API.
6. **Dashboard metrics are store-derived**: no separate analytics pipeline — queries the plan store directly.