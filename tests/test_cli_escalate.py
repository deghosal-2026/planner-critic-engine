"""``plancritic escalate`` CLI tests (F-31, F-34): human resolution + patching.

The escalate subcommand drives the :class:`EscalationManager` over a SQLite
store: list open/pending escalations, approve/deny them, and — for approve —
patch the plan first (a reviewer-supplied PlanVersion JSON) which is stored as
the next revision and re-submitted to the critic (deterministic gates in the
hermetic CLI path).
"""

from __future__ import annotations

import json

import pytest

from conftest import make_plan, make_task
from planner_critic._cli import main
from planner_critic.schema.plan import PlanVersion
from planner_critic.store.sqlite import SQLiteStore
from planner_critic.types import Escalation


@pytest.fixture
def db(tmp_path) -> str:
    """A fresh SQLite store path per test."""
    return str(tmp_path / "plans.db")


def _open_escalation(plan: PlanVersion, question: str = "proceed with this plan?") -> Escalation:
    """Build an open escalation for a stored plan revision."""
    return Escalation(
        id=f"esc:{plan.id}:{plan.version}",
        plan_id=plan.id,
        version=plan.version,
        question=question,
    )


def test_escalate_list_shows_open(db: str, capsys: pytest.CaptureFixture) -> None:
    """``escalate list`` prints open escalations with their question."""
    store = SQLiteStore(db)
    store.put_plan_version(make_plan(plan_id="plan-1", version=1))
    store.put_escalation(_open_escalation(make_plan(plan_id="plan-1", version=1)))
    store.close()

    assert main(["escalate", "--store", db, "list"]) == 0
    out = capsys.readouterr().out
    assert "plan-1" in out
    assert "proceed with this plan?" in out


def test_escalate_list_empty(db: str, capsys: pytest.CaptureFixture) -> None:
    """An empty store reports no escalations."""
    assert main(["escalate", "--store", db, "list"]) == 0
    assert "no escalations" in capsys.readouterr().out.lower()


def test_escalate_approve_resolves(db: str, capsys: pytest.CaptureFixture) -> None:
    """Approve records the decision against the escalation."""
    store = SQLiteStore(db)
    plan = make_plan(plan_id="plan-1", version=1)
    store.put_plan_version(plan)
    store.put_escalation(_open_escalation(plan))
    store.close()

    assert main(["escalate", "--store", db, "approve", "esc:plan-1:1", "--note", "go"]) == 0
    out = capsys.readouterr().out
    assert "approved" in out

    reopened = SQLiteStore(db)
    assert reopened.get_escalation("plan-1") is not None
    assert reopened.get_escalation("plan-1").status == "approved"
    assert reopened.get_escalation("plan-1").resolution == "go"
    reopened.close()


def test_escalate_deny(db: str, capsys: pytest.CaptureFixture) -> None:
    """Deny records a denied decision."""
    store = SQLiteStore(db)
    plan = make_plan(plan_id="plan-1", version=1)
    store.put_plan_version(plan)
    store.put_escalation(_open_escalation(plan))
    store.close()

    assert main(["escalate", "--store", db, "deny", "esc:plan-1:1", "--note", "no"]) == 0
    reopened = SQLiteStore(db)
    assert reopened.get_escalation("plan-1").status == "denied"
    reopened.close()


def test_escalate_patch_revises_and_recritiques(
    db: str, tmp_path, capsys: pytest.CaptureFixture
) -> None:
    """``approve --patch <json>`` stores revision N+1 and re-critiques it."""
    store = SQLiteStore(db)
    plan = make_plan(plan_id="plan-1", version=1)
    store.put_plan_version(plan)
    store.put_escalation(_open_escalation(plan))
    store.close()

    patch = make_plan(
        plan_id="plan-1",
        version=2,
        parent="plan-1",
        tasks=[make_task("t1", verification={"what": "w", "how": "h", "expected": "e"})],
    )
    patch_file = tmp_path / "patch.json"
    patch_file.write_text(json.dumps(patch.to_dict()))

    assert (
        main(
            [
                "escalate",
                "--store",
                db,
                "approve",
                "esc:plan-1:1",
                "--patch",
                str(patch_file),
                "--note",
                "patched",
            ]
        )
        == 0
    )

    reopened = SQLiteStore(db)
    latest = reopened.get_plan("plan-1")
    assert latest is not None
    assert latest.version == 2
    assert latest.parent_version == "plan-1"
    assert reopened.get_escalation("plan-1").status == "approved"
    reopened.close()


def test_escalate_unknown_id_fails(db: str, capsys: pytest.CaptureFixture) -> None:
    """Resolving a never-created escalation fails the command."""
    assert main(["escalate", "--store", db, "approve", "esc:ghost"]) != 0
    assert "failed" in capsys.readouterr().out


def test_escalate_patch_missing_file_fails(
    db: str, tmp_path, capsys: pytest.CaptureFixture
) -> None:
    """A missing patch file fails the command cleanly."""
    store = SQLiteStore(db)
    plan = make_plan(plan_id="plan-1", version=1)
    store.put_plan_version(plan)
    store.put_escalation(_open_escalation(plan))
    store.close()

    assert (
        main(
            [
                "escalate",
                "--store",
                db,
                "approve",
                "esc:plan-1:1",
                "--patch",
                str(tmp_path / "missing.json"),
            ]
        )
        != 0
    )
