# Field Test Scripts

## run_remaining.py

Runs the 61 remaining field-test scenarios (§3.11–§3.22 + expanded goals in existing domains) one at a time into `docs/field-test/reports/0.1.0-08.20.2026/remain-scenario/`.

### Prerequisites

- Active OpenRouter API key in `plancritic-fieldtest.toml` (project root)
- Python environment with `planner_critic` installed (`pip install -e .`)

### Usage

```bash
# Run all 61 scenarios
python3 docs/field-test/scripts/run_remaining.py

# Run first 5 only
python3 docs/field-test/scripts/run_remaining.py --max 5

# Skip goals that already have a trace.json (resume after interruption)
python3 docs/field-test/scripts/run_remaining.py --skip-existing
```

### Output

- Per-goal traces: `docs/field-test/reports/0.1.0-08.20.2026/remain-scenario/<goal-id>/core-api/<goal-id>/trace.json`
- LLM logs: `docs/field-test/reports/0.1.0-08.20.2026/remain-scenario/<goal-id>/core-api/<goal-id>/llm-logs/`
- Results registry: `docs/field-test/reports/0.1.0-08.20.2026/remain-scenario/results.json`

### Config

- Model: `openai/gpt-4o-mini` (OpenRouter), both planner and critic
- Loop: `deterministic-first`, `revision_cap=4`
- Config file: `plancritic-fieldtest.toml` (project root)
