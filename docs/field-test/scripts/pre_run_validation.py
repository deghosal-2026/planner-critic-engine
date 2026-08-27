"""P0: Pre-run assertion validation for v0.2.0 field test.

Validates that every goal JSON on disk has a matching assertion YAML
with the correct `invariants:` top-level key and `approve_expected` set.
Run before any LLM calls to catch format issues early (v0.1.0 learning #2).
"""

import json
import sys
from pathlib import Path

import yaml

GOALS_DIR = Path(__file__).parent.parent.parent.parent / "docs" / "field-test" / "goals"


def validate_all() -> int:
    errors: list[str] = []
    goals = sorted(GOALS_DIR.rglob("*.json"))
    print(f"Validating {len(goals)} goal files...")

    for gfile in goals:
        astub = gfile.relative_to(GOALS_DIR)
        adir = GOALS_DIR / astub.parent / "assertions"
        afile = adir / (astub.stem + ".yaml")

        if not afile.exists():
            errors.append(f"MISSING ASSERTION: {afile}")
            continue

        try:
            data = yaml.safe_load(afile.read_text())
        except Exception as e:
            errors.append(f"YAML PARSE ERROR: {afile}: {e}")
            continue

        if not isinstance(data, dict):
            errors.append(f"WRONG FORMAT (not dict): {afile}")
            continue

        inv = data.get("invariants")
        if not isinstance(inv, dict):
            errors.append(f"MISSING invariants: key: {afile}")
            continue

        if "approve_expected" not in inv:
            errors.append(f"MISSING approve_expected: {afile}")
            continue

        goal = json.loads(gfile.read_text())
        rt = goal.get("risk_tolerance", "")
        ae = inv["approve_expected"]
        if rt == "strict" and ae is True:
            errors.append(f"STRICT GOAL WITH approve_expected=true: {afile}")

    if errors:
        print(f"\n❌ {len(errors)} validation errors:")
        for e in errors:
            print(f"  {e}")
        return 1

    print(f"✅ All {len(goals)} goals validated successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(validate_all())
