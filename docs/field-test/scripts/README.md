# Field Test Scripts

Shared batch runners for field-test execution across versions.

## Structure

```
docs/field-test/scripts/
├── README.md
├── run_remaining.py     # Runs remaining field-test scenarios (v0.1.0 / batch runners)
├── batch-01.py          # Batch 1:  5 scenarios
├── batch-02.py          # Batch 2:  5 scenarios
├── ...                  # (batch-03 through batch-13)
└── v0.2.0/             # v0.2.0-specific benchmark scripts
    ├── bench_auto_repair.py    # Auto-repair benchmark (#177)
    ├── bench_rollback.py       # Rollback credibility field test (#182)
    └── bench_stasis.py         # Family-histogram stasis benchmark (#183)
```

## run_remaining.py

Runs field-test scenarios one at a time. Output goes to version-specific report directories.

### Prerequisites

- Active OpenRouter API key in `plancritic-fieldtest.toml` (project root)
- Python environment with `planner_critic` installed (`pip install -e .`)

### Usage

```bash
# Run all scenarios
python3 docs/field-test/scripts/run_remaining.py

# Run first 5 only
python3 docs/field-test/scripts/run_remaining.py --max 5

# Skip goals that already have a trace.json (resume after interruption)
python3 docs/field-test/scripts/run_remaining.py --skip-existing
```

### Output

- Per-goal traces: `docs/field-test/v0.1.0/reports/...` or `docs/field-test/v0.2.0/reports/...`

### Config

- Model: `openai/gpt-4o-mini` (OpenRouter), both planner and critic
- Loop: `deterministic-first`, `revision_cap=4`
- Config file: `plancritic-fieldtest.toml` (project root)