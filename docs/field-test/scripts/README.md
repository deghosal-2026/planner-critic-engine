# Field Test Scripts

> **This directory has been consolidated. See [../README.md](../README.md) for the full execution guide.**

## What's here

| File | Description |
|------|-------------|
| `run.py` | **Single runner** for all 170 goals across 40 domains (replaces batch-01.py through batch-39.py and run_remaining.py) |
| `v0.2.0/pre_run_validation.py` | P0: assertion YAML validation |
| `v0.2.0/bench_auto_repair.py` | P4: auto-repair benchmark (#177) |
| `v0.2.0/bench_rollback.py` | P4: rollback credibility field test (#182) |
| `v0.2.0/bench_stasis.py` | P4: family-histogram stasis benchmark (#183) |

## Quick start

```bash
# All 170 goals (cloud LLM)
export OPENROUTER_API_KEY="sk-or-..."
python3 run.py --all

# Specific domains (local MLX)
python3 run.py --domain idp,mao,sre --provider mlx

# Preview
python3 run.py --all --dry-run
```

See [field-test README](../README.md) for full documentation.