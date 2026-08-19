"""M7 sample-corpus tests (F-65): every corpus goal is valid and self-describing.

The corpus lives in ``examples/goals/`` and is the input to the demo runner.
Each goal must parse against the :class:`Goal` schema, declare exactly one
documented ``_seeded_flaw``, and carry a plain-English ``_doc``. Unknown
fields are tolerated by the schema (D11/DD-M7-07), so the extra keys never
break validation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from planner_critic.schema.goal import Goal

CORPUS_DIR = Path(__file__).parents[1] / "examples" / "goals"

CORPUS_FILES = [
    "migration.json",
    "rollout.json",
    "refactor.json",
    "incident.json",
    "adversarial.json",
]

EXPECTED_IDS = [
    "demo-migration",
    "demo-rollout",
    "demo-refactor",
    "demo-incident",
    "demo-adversarial",
]

VALID_FAMILIES = {
    "feasibility",
    "risk",
    "missing_steps",
    "unsafe_sequencing",
    "unverified_dependencies",
    "weak_rollback",
}


@pytest.fixture(scope="module")
def corpus() -> dict[str, dict]:
    """Load every corpus file in stable order."""
    return {name: json.loads((CORPUS_DIR / name).read_text()) for name in CORPUS_FILES}


def test_corpus_directory_and_files_exist() -> None:
    """The corpus directory exists with all five goal files."""
    assert CORPUS_DIR.is_dir()
    for name in CORPUS_FILES:
        assert (CORPUS_DIR / name).is_file(), f"missing corpus goal: {name}"


def test_every_goal_parses_against_the_schema(corpus: dict[str, dict]) -> None:
    """Each corpus goal validates as a typed Goal (F-65)."""
    for name, data in corpus.items():
        goal = Goal.model_validate(data)
        assert goal.id.startswith("demo-"), name


def test_every_goal_has_exactly_one_seeded_flaw(corpus: dict[str, dict]) -> None:
    """Each corpus goal documents exactly one seeded flaw (D11/DD-M7-07)."""
    for name, data in corpus.items():
        flaw = data.get("_seeded_flaw")
        assert isinstance(flaw, dict), f"{name}: missing _seeded_flaw"
        assert flaw.get("family") in VALID_FAMILIES, f"{name}: unknown family"
        assert flaw.get("severity") in {"warning", "blocker"}, f"{name}: bad severity"
        assert flaw.get("description"), f"{name}: flaw has no description"


def test_every_goal_carries_a_doc(corpus: dict[str, dict]) -> None:
    """Each corpus goal has a plain-English ``_doc`` (self-describing)."""
    for name, data in corpus.items():
        assert data.get("_doc"), f"{name}: missing _doc"


def test_goal_ids_are_unique_and_stable(corpus: dict[str, dict]) -> None:
    """Corpus ids are unique and pinned so demo output is stable."""
    ids = [data["id"] for data in corpus.values()]
    assert len(ids) == len(set(ids)) == len(CORPUS_FILES)
    assert ids == EXPECTED_IDS
