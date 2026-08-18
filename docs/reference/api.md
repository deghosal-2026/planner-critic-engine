# D14 — API Reference

> **Authored in:** M6 (CLI + HTTP Service + Explain + Init) · **Status:** Current baseline · **WBS:** D14 ·
> **Refs:** [PRD §5.9 CLI + HTTP tables](../design/prd/05-features.md)

## CLI — `plancritic`

| Command | Description | Added |
|---------|-------------|-------|
| `plancritic --version` | Print version | M1 |
| `plancritic init [--dir] [--force]` | Scaffold config + store | M6 |
| `plancritic providers add/list/rm` | Manage LLM provider config | M2 |
| `plancritic plan <goal-json> [--dry-run] [--store] [--config]` | Plan a goal | M6 |
| `plancritic critique <plan-json> [--store]` | Run deterministic gates on a plan | M6 |
| `plancritic plans list` | List stored plans | M6 |
| `plancritic plans show <plan-id> [--version]` | Show plan details | M6 |
| `plancritic plans diff <plan-id> <v1> <v2> [--graph]` | Diff two plan revisions | M6 |
| `plancritic escalate list [--status] [--store]` | List escalations | M4 |
| `plancritic escalate approve <id> [--patch] [--note] [--store]` | Approve an escalation | M4 |
| `plancritic escalate deny <id> [--note] [--store]` | Deny an escalation | M4 |
| `plancritic replay <plan-id> [--step] [--format] [--store]` | Walk plan version history | M4 |
| `plancritic explain <plan-id> [--store]` | Explain loop decisions | M6 |
| `plancritic migrate [--path] [--revert]` | Manage store schema migrations | M2 |

## HTTP Service — `POST / GET`

| Method | Path | Description | Added |
|--------|------|-------------|-------|
| `POST` | `/plan` | Plan a goal (accepts Goal JSON) | M6 |
| `POST` | `/critique` | Run deterministic gates (accepts PlanVersion JSON) | M6 |
| `GET` | `/plans` | List stored plans | M6 |
| `GET` | `/plans/{id}` | Show plan details | M6 |
| `GET` | `/plans/{id}/diff?v2=N` | Diff two versions | M6 |
| `GET` | `/plans/{id}/graph` | Mermaid DAG | M6 |
| `GET` | `/plans/{id}/explain` | Explain loop decisions | M6 |
| `GET` | `/escalations` | List escalations | M6 |
| `POST` | `/escalations/{id}/approve` | Approve an escalation | M6 |
| `POST` | `/escalations/{id}/deny` | Deny an escalation | M6 |

## MCP Server — 6 Tools

| Tool | Description | Added |
|------|-------------|-------|
| `plan` | Plan a goal (accepts Goal JSON) | M5 |
| `critique` | Run deterministic gates (accepts PlanVersion JSON) | M5 |
| `explain` | Explain loop decisions for a plan id | M5 |
| `escalate_list` | List escalations | M5 |
| `escalate_approve` | Approve an escalation | M5 |
| `escalate_deny` | Deny an escalation | M5 |

## Plan Store — SQLite

Default path: `.plancritic/plans.db` (configurable via `--store` or `--path`).

### Tables

| Table | Key | Content |
|-------|-----|---------|
| `plan_versions` | `(plan_id, version)` | Canonical PlanVersion JSON |
| `findings` | `(plan_id, version)` | Critique findings JSON |
| `escalations` | `plan_id` | Single escalation per plan |
| `execution_traces` | `plan_id, seq` | Ordered execution steps |
| `links` | `(plan_id, version, trace_id)` | Approved-plan ↔ trace links |
| `replan_links` | `(plan_id, version)` | Replan lineage records |
| `missed_critiques` | `plan_id` | Forensics records |
| `schema_migrations` | `version` | Migration ledger |

## Python API

```python
from planner_critic import Engine
from planner_critic.schema.goal import Goal
from planner_critic.schema.plan import PlanVersion, Task
from planner_critic.roles import CriticRole, PlannerRole
from planner_critic.loop import LoopConfig, LoopResult, run_loop
from planner_critic.escalation import EscalationManager
from planner_critic.execution import ExecutionRecorder
from planner_critic.forensics import MissedCritique, analyze_failure
from planner_critic.replan import replan, ReplanAbort
from planner_critic.regate import ReGateConfig, ReGateResult, check_preconditions
from planner_critic.explain import explain, ExplainResult
from planner_critic.viz.graph import to_mermaid, to_json
from planner_critic.viz.replay import replay
from planner_critic.store.base import InMemoryStore, PlanStore
from planner_critic.store.sqlite import SQLiteStore
from planner_critic.adapters.python import plan as raw_plan, PlannerCriticPlan
from planner_critic.adapters._audit import AuditTrail, AuditEvent
from planner_critic.server.mcp import PlannerCriticMCPServer
from planner_critic.server.http import PlannerCriticHTTPServer
```