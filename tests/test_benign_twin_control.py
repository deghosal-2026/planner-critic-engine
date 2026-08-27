"""Benign-twin control for adversarial goals (#260).

For each adversarial goal, a benign twin with the injected text stripped
is run through the same pipeline. This isolates injection isolation from
gate strictness — answering: did the gates block the injection, or did
they just block a structurally unsafe plan?

The hermetic tests validate that benign twins exist and load correctly.
The real LLM comparison is run as part of the field test sweep (M5).
"""

from __future__ import annotations

import json
from pathlib import Path

from planner_critic.schema.goal import Goal

ADVERSARIAL_DIR = Path(__file__).parents[1] / "docs" / "field-test" / "goals" / "adversarial"
ADVERSARIAL_POLICY_DIR = (
    Path(__file__).parents[1] / "docs" / "field-test" / "goals" / "adversarial-policy"
)
BENIGN_DIR = Path(__file__).parents[1] / "docs" / "field-test" / "goals" / "adversarial-benign"


# Map adversarial ids to their benign twin file stems
ADV_TO_BENIGN: dict[str, str] = {
    "adv-01-billing-no-safety": "adv-01-billing-schema-migration",
    "adv-02-friday-deploy": "adv-02-auth-service-deploy",
    "adv-03-rm-rf-root": "adv-03-disk-cleanup",
    "adv-04-mass-cert-rotation": "adv-04-cert-rotation",
    "adv-05-public-db-migration": "adv-05-db-migration",
    "adv-06-policy-violation": "adv-06-mfa-audit",
    "adv-07-prompt-injection": "adv-07-schema-deploy",
    "adv-08-disguised-exfiltration": "adv-08-analytics-migration",
}


class TestBenignTwinExists:
    """Every adversarial goal must have a benign twin."""

    def test_all_adversarial_goals_have_benign_twins(self) -> None:
        """Check that all 11 adversarial goals have benign twins."""
        adv_files = sorted(ADVERSARIAL_DIR.glob("adv-*.json"))
        adv_policy_files = sorted(ADVERSARIAL_POLICY_DIR.glob("adv-*.json"))
        all_adv = adv_files + adv_policy_files

        benign_files = {p.stem for p in BENIGN_DIR.glob("*.json")}
        for adv_file in all_adv:
            goal = Goal.model_validate(json.loads(adv_file.read_text()))
            benign_id = ADV_TO_BENIGN.get(goal.id)
            assert benign_id is not None, f"no benign twin mapping for {goal.id} ({adv_file})"
            assert benign_id in benign_files, (
                f"benign twin file {benign_id}.json not found for {goal.id}"
            )

    def test_all_benign_twins_have_different_ids(self) -> None:
        """Benign twins must have different ids from their adversarial counterparts."""
        for adv_id, benign_id in ADV_TO_BENIGN.items():
            assert adv_id != benign_id

    def test_all_benign_twins_load_correctly(self) -> None:
        """Every benign twin loads as a valid Goal."""
        for p in sorted(BENIGN_DIR.glob("*.json")):
            goal = Goal.model_validate(json.loads(p.read_text()))
            assert goal.id == p.stem
            assert goal.risk_tolerance.value in ("balanced", "strict")

    def test_benign_twins_have_lower_risk_tolerance(self) -> None:
        """Benign twins should use balanced tolerance (adversarial uses strict)."""
        for _adv_id, benign_id in ADV_TO_BENIGN.items():
            benign_file = BENIGN_DIR / f"{benign_id}.json"
            if not benign_file.exists():
                continue
            benign_goal = Goal.model_validate(json.loads(benign_file.read_text()))
            # Adversarial goals are always strict; benign should be balanced
            assert benign_goal.risk_tolerance.value == "balanced", (
                f"benign twin {benign_id} should use balanced tolerance, "
                f"got {benign_goal.risk_tolerance.value}"
            )

    def test_benign_twins_use_patch_replan_policy(self) -> None:
        """Benign twins should use patch replan policy (adversarial uses abort)."""
        for _adv_id, benign_id in ADV_TO_BENIGN.items():
            benign_file = BENIGN_DIR / f"{benign_id}.json"
            if not benign_file.exists():
                continue
            benign_goal = Goal.model_validate(json.loads(benign_file.read_text()))
            assert benign_goal.replan_policy.value == "patch", (
                f"benign twin {benign_id} should use patch policy, "
                f"got {benign_goal.replan_policy.value}"
            )
