# D14 — API Reference

> **Authored in:** M6 (CLI + HTTP Service + Explain + Init) — updated for v0.2.0 · **WBS:** D14 ·
> **Refs:** [PRD §5.9 CLI + HTTP tables](../design/prd/05-features.md)

## CLI — `plancritic`

### Core Planning

| Command | Description | Added |
|---------|-------------|-------|
| `plancritic --version` | Print version | M1 |
| `plancritic plan <goal-json> [--dry-run] [--store] [--config]` | Plan a goal | M6 |
| `plancritic critique <plan-json> [--store]` | Run deterministic gates on a plan | M6 |
| `plancritic check --plan <plan.json> [--config]` | Quality-check a plan against all gates | M7 |
| `plancritic diagnose <plan-id> [--store]` | Diagnose why a plan failed gates | M7 |
| `plancritic plans list` | List stored plans | M6 |
| `plancritic plans show <plan-id> [--version]` | Show plan details | M6 |
| `plancritic plans diff <plan-id> <v1> <v2> [--graph]` | Diff two plan revisions | M6 |
| `plancritic replay <plan-id> [--step] [--format] [--store]` | Walk plan version history | M4 |
| `plancritic explain <plan-id> [--store]` | Explain loop decisions | M6 |

### Domain Packs & Policy

| Command | Description | Added |
|---------|-------------|-------|
| `plancritic domains list` | List available domain packs with gate descriptions | M7 |
| `plancritic domains describe <name>` | Describe a specific domain pack | M7 |
| `plancritic policy check <plan.json>` | Evaluate Rego/CEL policies against a plan | M7 |
| `plancritic templates list` | List scaffold templates for domain packs | M7 |
| `plancritic templates create <name> [--dir]` | Create a new domain pack from template | M7 |
| `plancritic init [--dir] [--force] [--template <name>]` | Scaffold config + store + optional domain pack | M6/M7 |

### Escalation & Findings

| Command | Description | Added |
|---------|-------------|-------|
| `plancritic escalate list [--status] [--store]` | List escalations | M4 |
| `plancritic escalate approve <id> [--patch] [--note] [--store]` | Approve an escalation | M4 |
| `plancritic escalate deny <id> [--note] [--store]` | Deny an escalation | M4 |
| `plancritic findings list [--plan-id] [--store]` | List plan findings with drift analysis | M7 |
| `plancritic lessons` | List learned lesson codes from past critiques | M7 |

### Evaluation & Testing

| Command | Description | Added |
|---------|-------------|-------|
| `plancritic eval --regression` | Run deterministic-gate security regression | M5 |
| `plancritic eval --adversarial` | Run adversarial injection harness | M5 |
| `plancritic field-test run --goals <dir> [--all] [--domain]` | Run field test sweep | M1 |
| `plancritic corpus list` | List field-test corpora | M5 |

### Configuration & Administration

| Command | Description | Added |
|---------|-------------|-------|
| `plancritic providers add <name>` | Add an LLM provider | M2 |
| `plancritic providers list` | List configured providers | M2 |
| `plancritic providers rm <name>` | Remove an LLM provider | M2 |
| `plancritic migrate [--path] [--revert]` | Manage store schema migrations | M2 |
| `plancritic quota show [--plan-id]` | Show blast-radius quota usage | M7 |

### Demo & Quickstart

| Command | Description | Added |
|---------|-------------|-------|
| `plancritic demo` | Run the bundled demo scenario | M1 |
| `plancritic quickstart` | Create and run a sample goal | M1 |

### Server

| Command | Description | Added |
|---------|-------------|-------|
| `plancritic serve [--host] [--port] [--store]` | Start HTTP server | M6 |

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
from planner_critic.domains import list_domain_packs, get_domain_pack
from planner_critic.policy import PolicyEngine, RegoGate, CelGate
from planner_critic.pytest_plugin import planner_critic_check
from planner_critic.redaction import RedactionConfig, redact_plan
from planner_critic.posture import PostureResolver
from planner_critic.run_budget import RunBudget
from planner_critic.state import StateLock
from planner_critic.ledger import PreconditionLedger
from planner_critic.quota import BlastRadiusQuota
from planner_critic.drift import FindingDrift
from planner_critic.probe import ProbeConfig, run_probes
from planner_critic.guardrail import re_gate, plan_guardrail
```