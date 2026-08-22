# Domain Pack Design (D20)

> **Authored:** M3 (#139) — 2026-08-22  
> **Status:** As-built

## Overview

Domain Packs bundle domain-specific gate evaluators, precondition catalogs, and optional critic prompt templates into one installable unit. They are **additive** to the built-in six deterministic gates — never replacing them. The domain prompt template is **prepended** to the critic's system prompt, never replacing it either.

## Protocol

A domain pack is any object satisfying the `DomainPack` protocol (`src/planner_critic/domains/base.py`):

```python
class DomainPack(Protocol):
    name: str
    gate_evaluators: list[BaseGate]
    precondition_catalog: dict[str, str]
    critic_prompt_template: str | None
    pack_config: dict
```

A `@runtime_checkable` protocol, so `isinstance(pack, DomainPack)` works at runtime.

## Manifest Format (`domain-pack.yaml`)

```yaml
name: secops
version: 0.1.0
description: "Security operations domain pack"
gates:
  - module: planner_critic.domains.secops.gates
    class: BlastRadiusGate
preconditions:
  traffic_drained: "Traffic has been drained from the target"
  snapshot_created: "A recent snapshot of the resource exists"
critic_prompt: "Audit this plan from a security-engineering perspective.\n"
config:
  allowed_clusters: ["prod-us", "prod-eu"]
```

## Loading

- `pack_from_dict(manifest: dict)` — builds a protocol-compliant pack from a Python dict.
- `load_domain_pack_from_manifest(path: str | Path)` — loads from a YAML file.
- `find_domain_packs(namespace="planner_critic.domains")` — scans a namespace for installed packs.

## Engine Integration

The `Engine` facade accepts an optional `domain_pack=` parameter:

```python
engine = Engine(planner, critic, domain_pack=my_pack)
```

- `engine.domain_gates` — list of `BaseGate` instances from the pack.
- `engine.domain_critic_prompt` — the pack's prompt template (or `None`).
- `engine.run_domain_gates(plan)` — runs built-in six + domain gates.
- `engine.plan(goal)` — threads `domain_gates` as `extra_gates` through `run_loop`.

## Gate Additivity

The `run_deterministic_gates(plan, extra_gates=None)` function accepts optional domain gates. The loop controller's `_run` function passes `extra_gates` through every `run_deterministic_gates` call, including the re-gate checks after auto-fix passes (M2). Domain gates never replace built-in gates — they are appended.

## Deferred

- `plancritic domains add/list/show/test` CLI (#175, moved to M3 checklist)