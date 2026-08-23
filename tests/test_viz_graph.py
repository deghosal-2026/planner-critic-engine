"""Plan-graph export tests (F-75): Mermaid + JSON DAG rendering."""

from __future__ import annotations

import json
from typing import cast

from conftest import hard_dep, make_plan, make_task
from planner_critic.viz.graph import to_json, to_mermaid


def test_mermaid_single_task() -> None:
    """A single task renders a minimal Mermaid graph."""
    plan = make_plan(tasks=[make_task("t1")])
    out = to_mermaid(plan)
    assert "graph TD" in out
    assert "t1" in out


def test_mermaid_with_dependency() -> None:
    """A dependency renders as an edge in the Mermaid graph."""
    plan = make_plan(
        tasks=[make_task("t1"), make_task("t2")],
        dependencies=[hard_dep("t1", "t2")],
    )
    out = to_mermaid(plan)
    assert "t1 --> t2" in out
    assert "graph TD" in out


def test_mermaid_includes_task_descriptions() -> None:
    """Task descriptions appear as node labels."""
    plan = make_plan(tasks=[make_task("t1")])
    out = to_mermaid(plan)
    assert "task t1" in out


def test_json_structure() -> None:
    """JSON export has nodes, edges, plan metadata."""
    plan = make_plan(
        plan_id="p1",
        version=2,
        tasks=[make_task("t1"), make_task("t2")],
        dependencies=[hard_dep("t1", "t2")],
    )
    data = to_json(plan)
    assert data["plan_id"] == "p1"
    assert data["version"] == 2
    nodes = cast("list[object]", data["nodes"])
    edges = cast("list[dict[str, object]]", data["edges"])
    assert len(nodes) == 2
    assert edges[0]["from"] == "t1"
    assert edges[0]["to"] == "t2"


def test_json_round_trips() -> None:
    """JSON output is valid JSON."""
    plan = make_plan(tasks=[make_task("t1"), make_task("t2")], dependencies=[hard_dep("t1", "t2")])
    data = to_json(plan)
    text = json.dumps(data)
    assert "t1" in text
