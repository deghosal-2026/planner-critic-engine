# Field Test Execution Guide

## Prerequisites

```bash
pip install -e .
export OPENROUTER_API_KEY="sk-or-..."
```

## Quick Reference

| Phase | Command | LLM? | Cost | Time |
|-------|---------|------|------|------|
| P0 validation | `python3 docs/field-test/v0.2.0/scripts/pre_run_validation.py` | No | $0 | 5 min |
| P2 deterministic | `pytest tests/field_test_v0_2_0/ -v --no-cov` | No | $0 | 45 min |
| P3 LLM tests | `pytest tests/field_test_v0_2_0/ -v --run-llm --no-cov` | Yes | ~$0.10 | 1-2 hr |
| P4 benchmarks | `python3 docs/field-test/v0.2.0/scripts/bench_*.py > results/` | No | $0 | 30 min |
| P1 new goals | `python3 docs/field-test/scripts/run.py --domain idp,mao,sre,scp,fng,adversarial-policy` | Yes | ~$0.05 | 2-4 hr |
| P5 full sweep | `python3 docs/field-test/scripts/run.py --all` | Yes | ~$0.35 | 8-12 hr |
| **Total** | | | **~$0.45** | **~10-15 hr** |

## Running Goals

Single runner — no batch files needed:

```bash
# Run all 170 goals (P5 full regression sweep)
python3 docs/field-test/scripts/run.py --all

# Run specific domains (P1 new goals)
python3 docs/field-test/scripts/run.py --domain idp,mao,sre,scp,fng

# Run specific goals by ID
python3 docs/field-test/scripts/run.py --goals db-01,k8s-01,adv-01

# Dry run — list what would run without executing
python3 docs/field-test/scripts/run.py --all --dry-run

# Resume after interruption — skip existing traces
python3 docs/field-test/scripts/run.py --all --skip-existing

# Use MLX local model instead of cloud
python3 docs/field-test/scripts/run.py --all --provider mlx
```

## Execution Phases

### Phase 0 — Pre-run Validation (5 min, $0)

```bash
python3 docs/field-test/v0.2.0/scripts/pre_run_validation.py
```

### Phase 2 — Deterministic Tests (45 min, $0)

```bash
pytest tests/field_test_v0_2_0/test_wbs_coverage.py -v --no-cov
```

### Phase 3 — LLM Subsystem Tests (1-2 hr, ~$0.10)

```bash
pytest tests/field_test_v0_2_0/test_wbs_coverage.py -v --run-llm --no-cov
```

### Phase 4 — Benchmarks (30 min, $0)

```bash
python3 docs/field-test/v0.2.0/scripts/bench_auto_repair.py > docs/field-test/v0.2.0/results/bench_auto_repair.json
python3 docs/field-test/v0.2.0/scripts/bench_rollback.py > docs/field-test/v0.2.0/results/bench_rollback.json
python3 docs/field-test/v0.2.0/scripts/bench_stasis.py > docs/field-test/v0.2.0/results/bench_stasis.json
```

### Phase 1 + Phase 5 — All 170 Goals (8-12 hr, ~$0.35)

```bash
python3 docs/field-test/scripts/run.py --all
```

## Output

| Run | Output directory |
|-----|-----------------|
| `--all` | `docs/field-test/v0.2.0/reports/sweep/<goal-id>/core-api/<goal-id>/trace.json` |
| `--domain idp` | `docs/field-test/v0.2.0/reports/sweep/idp-01/...` |
| `--goals db-01` | `docs/field-test/v0.2.0/reports/sweep/db-01/...` |
| Results JSON | `docs/field-test/v0.2.0/reports/sweep/results.json` |

## API Key

The runner reads `OPENROUTER_API_KEY` from the environment. No config files with credentials are tracked in git.