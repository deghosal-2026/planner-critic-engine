"""Thin `plannercritic-demo` usage example (F-86, D11 §6).

The WBS's "demo runner" is discoverable here as a script that calls the
packaged runner directly — no coupling to the package's CLI namespace.
"""

from __future__ import annotations

from planner_critic.demo.runner import run_demo
from planner_critic.store.base import InMemoryStore

if __name__ == "__main__":  # pragma: no cover - example script
    raise SystemExit(run_demo("examples/goals/migration.json", InMemoryStore()))
