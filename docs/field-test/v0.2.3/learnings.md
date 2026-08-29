# Learnings — v0.2.3

## What We Learned

1. **Measurement infrastructure releases are low-risk but high-ROI.** When you don't touch planning, critique, or gate logic, the field test is a formality — but the gate canary and transit-integrity checks now catch failure classes that would have been invisible in previous releases.

2. **Version must be bumped in 3 places simultaneously:** `pyproject.toml`, `src/planner_critic/__init__.py`, `Dockerfile`. Missing any one causes a mismatch.

3. **Canary fixtures must be inside the package** to travel with the wheel. Fixtures in `tests/` are not included in the Docker build.

4. **The `system_prompt_hash` in DecisionContext** is prone to false positives from the SecretsRedactor. SHA-256 hex digests can match credential regex patterns.

5. **Community feedback drives real value.** All 5 M1 issues came from dev.to comments — Antonio, Artjoms, Peter, Heinrich, and Tae Kim identified gaps the project's own testing missed.

6. **The `gates` CLI subcommand needs explicit registration** in both `cli/__init__.py` and `_cli.py`. Both are easy to miss.