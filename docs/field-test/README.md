# v0.2.0 Field Test

Single runner for all 170 goals across 40 domains.

```bash
python3 docs/field-test/scripts/run.py --help
```

## Prerequisites

```bash
pip install -e .
```

### API Key

**Cloud provider (default):** requires OpenRouter API key:

```bash
export OPENROUTER_API_KEY="sk-or-..."
```

**Local provider (OMLX):** no API key needed (defaults to `omlx-test`). Requires an OMLX server running:

```bash
# Start OMLX server (separate terminal)
omlx serve mlx-community/Qwen3-4B-Instruct-2507-4bit --port 8000
```

## Run Script

All 170 goals are discovered automatically from `docs/field-test/goals/`. No batch files needed.

### Run All Goals

```bash
# Full regression sweep (8-12 hours, ~$0.35)
python3 docs/field-test/scripts/run.py --all

# Resume after interruption
python3 docs/field-test/scripts/run.py --all --skip-existing

# Preview only (no LLM calls)
python3 docs/field-test/scripts/run.py --all --dry-run
```

### Run Subsets

```bash
# By domain (P1: new v0.2.0 domains)
python3 docs/field-test/scripts/run.py --domain idp,mao,sre,scp,fng,adversarial-policy

# By goal ID prefix (substring match)
python3 docs/field-test/scripts/run.py --goals db-01,ir-07,k8s-05

# Combined
python3 docs/field-test/scripts/run.py --domain database,kubernetes --skip-existing
```

### Select LLM Provider

```bash
# Cloud (default) — requires OPENROUTER_API_KEY
python3 docs/field-test/scripts/run.py --all
python3 docs/field-test/scripts/run.py --all --provider openai

# Local MLX — requires mlx_lm.server on port 8080
python3 docs/field-test/scripts/run.py --all --provider mlx
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--all` | False | Run all 170 goals |
| `--domain` | None | Comma-separated domains (e.g. `idp,mao`) |
| `--goals` | None | Comma-separated goal ID prefixes (e.g. `db-01`) |
| `--provider` | `openai` | LLM provider: `openai` (cloud) or `mlx` (local) |
| `--revision-cap` | 4 | Max revisions per goal |
| `--output` | `results/0.2.0/<model>/` | Output directory (auto-derived from provider) |
| `--skip-existing` | False | Skip goals with existing traces |
| `--dry-run` | False | List goals without executing |

## Providers

| Provider | Flag | Model | Endpoint | Key needed | Cost |
|----------|------|-------|----------|------------|------|
| OpenRouter (cloud) | `--provider openai` | `gpt-4o-mini` | `api.openrouter.ai` | `OPENROUTER_API_KEY` | ~$0.35/sweep |
| OMLX (local) | `--provider omlx` | `Qwen3-4B-Instruct-2507-4bit` | `127.0.0.1:8000` | None (defaults to `omlx-test`) | Free |

**Cloud vs local notes:**
- v0.1.0 field test proved local models (<14B) cannot produce structured JSON consistently
- Cloud (`gpt-4o-mini`) is the recommended default — results are comparable across runs
- MLX is for development iteration / quick checks when offline
- All 50 deterministic tests in `tests/field_test_v0_2_0/` run with $0, no LLM needed

## Execution Phases

### Phase 0 — Pre-run Validation (5 min, $0)

```bash
python3 docs/field-test/scripts/pre_run_validation.py
```

Validates all 170 assertion YAMLs have correct `invariants:` format before spending
LLM tokens. Catches assertion file issues early (v0.1.0 learning #2).

### Phase 1 — New Domain Goals (2-4 hr, ~$0.05)

```bash
python3 docs/field-test/scripts/run.py --domain idp,mao,sre,scp,fng,adversarial-policy
```

17 new v0.2.0 goals across 6 new domain groupings.

### Phase 2 — Deterministic Subsystem Tests (45 min, $0)

```bash
pytest tests/field_test_v0_2_0/test_wbs_coverage.py -v --no-cov
```

50 hermetic tests covering all v0.2.0 subsystems. No LLM, no network.

### Phase 3 — LLM Subsystem Tests (1-2 hr, ~$0.10)

```bash
pytest tests/field_test_v0_2_0/test_wbs_coverage.py -v --run-llm --no-cov
```

Tests that require a live LLM (CLI dispatch, HTTP/MCP, decorators, drift).

### Phase 4 — Benchmarks (30 min, $0)

```bash
python3 docs/field-test/scripts/bench_auto_repair.py > docs/field-test/v0.2.0/results/bench_auto_repair.json
python3 docs/field-test/scripts/bench_rollback.py > docs/field-test/v0.2.0/results/bench_rollback.json
python3 docs/field-test/scripts/bench_stasis.py > docs/field-test/v0.2.0/results/bench_stasis.json
```

Retrospective analysis over existing traces. No new LLM calls.

### Phase 5 — Full Regression Sweep (8-12 hr, ~$0.35)

```bash
python3 docs/field-test/scripts/run.py --all
```

Re-run all 170 goals to confirm no regressions from v0.1.0.

## Output

Results are stored in `results/<version>/<provider-model>/` by default:

| Provider | Command | Output directory |
|----------|---------|-----------------|
| OpenRouter (cloud) | `run.py --all` | `results/0.2.0/openai-gpt-4o-mini/` |
| OMLX (local) | `run.py --all --provider omlx` | `results/0.2.0/omlx-mlx-community-Qwen3-4B-Instruct-2507-4bit/` |
| Custom | `run.py --all --output ./my-results` | `./my-results/` |

Inside each output directory:

```
results/0.2.0/openai-gpt-4o-mini/
├── results.json           # Top-level pass/fail per goal
├── <goal-id>/             # e.g. idp-01-rbac-boundary/
│   └── core-api/
│       └── <goal-id>/
│           ├── trace.json # Full plan-critique trace
│           └── llm-logs/  # Raw LLM request/response
└── ...
```

Results are version-separated (`0.2.0`) and model-separated (`openai-gpt-4o-mini` vs `omlx-mlx-community-Qwen3-4B-Instruct-2507-4bit`), so you can compare cloud vs local results side by side.

## Coverage

| | Count |
|---|-------|
| Goal files on disk | **170** |
| Domains | **40** |
| Discovered by `--all` | 170 ✅ |
| v0.1.0 inherited goals | ~153 ✅ |
| New v0.2.0 goals (IDP/MAO/SRE/SCP/FNG/ADV) | 17 ✅ |
| Filterable by `--domain` | Yes ✅ |
| Filterable by `--goals` (substring) | Yes ✅ |

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `OPENROUTER_API_KEY not set` | Missing API key | `export OPENROUTER_API_KEY="sk-or-..."` |
| `Connection refused` on OMLX | OMLX server not running | `omlx serve mlx-community/Qwen3-4B-Instruct-2507-4bit --port 8000` |
| `0/0 results` | Assertion files malformed | Run P0 validation |
| LLM produces garbled output | Local model too small | Use `--provider openai` (cloud) |
| All strict goals escalate | Expected behavior | v0.1.0 proved strict+LLM critic = never approve |
| Traces missing | Wrong output directory | Check `--output` path |

## Quick Reference

| Phase | Command | LLM? | Cost | Time |
|-------|---------|------|------|------|
| P0 assertion validation | `python3 docs/field-test/scripts/pre_run_validation.py` | No | $0 | 5 min |
| P1 new domain goals | `python3 docs/field-test/scripts/run.py --domain idp,mao,sre,scp,fng,adversarial-policy` | Yes | ~$0.05 | 2-4 hr |
| P2 deterministic tests | `pytest tests/field_test_v0_2_0/ -v --no-cov` | No | $0 | 45 min |
| P3 LLM tests | `pytest tests/field_test_v0_2_0/ -v --run-llm --no-cov` | Yes | ~$0.10 | 1-2 hr |
| P4 benchmarks | `python3 docs/field-test/scripts/bench_*.py > results/` | No | $0 | 30 min |
| P5 full sweep | `python3 docs/field-test/scripts/run.py --all` | Yes | ~$0.35 | 8-12 hr |
| **Total** | | | **~$0.45** | **~10-15 hr** |

## Directory Structure

```
docs/field-test/
├── README.md                       ← this file
├── run.py                          ← single goal runner (170 goals)
├── goals/                          ← 170 goal JSON + YAML assertion files (40 domains)
├── v0.1.0/                         ← v0.1.0 field test (archived)
│   ├── field-test-plan.md
│   ├── field-test-results-0.1.0.md
│   └── reports/
├── v0.2.0/                         ← v0.2.0 field test
│   ├── field-test-plan.md
│   ├── README.md
│   ├── reports/                    ← populated by run.py
│   ├── results/                    ← benchmark JSON output
│   └── scripts/                    ← benchmark + validation scripts
├── corpus/                         ← SWE-bench security oracle
└── docker-integration.md
```