# Field Test Execution Guide

> **How to run the v0.2.0 field test.** Follow the phases in order.

## Prerequisites

```bash
pip install -e .
export OPENROUTER_API_KEY="sk-or-..."
cat plancritic-fieldtest.toml  # verify config exists
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

Run all 39 batches in sequence:

```bash
for i in $(seq 1 39); do
    batch=$(printf "docs/field-test/scripts/batch-%02d.py" $i)
    echo "=== Running batch-$i ==="
    python3 $batch
done
```

Or run individual batches:

```bash
python3 docs/field-test/scripts/batch-01.py   # 5 goals: database, kubernetes
python3 docs/field-test/scripts/batch-14.py   # 5 goals: accessibility, adversarial
python3 docs/field-test/scripts/batch-26.py   # 5 goals: idp, incident-response
# ... etc
```

## Batch Coverage Table

All 170 goals across 40 domains are covered by batches 1-39. Each batch runs 5 goals (batch-13 and batch-39 have fewer).

| Batch | Goals | Domains |
|-------|-------|---------|
| 01 | 5 | database (4), kubernetes (1) |
| 02 | 5 | kubernetes (2), cicd (3) |
| 03 | 5 | incident-response (4), infrastructure (1) |
| 04 | 5 | infrastructure (2), observability (3) |
| 05 | 5 | architecture (2), data (2), platform (1) |
| 06 | 5 | platform (2), greenfield (3) |
| 07 | 5 | decommissioning (2), disaster-recovery (3) |
| 08 | 5 | compliance (3), identity-access (2) |
| 09 | 5 | serverless (2), adversarial-policy (3) |
| 10 | 5 | networking (3), finops (2) |
| 11 | 5 | finops (1), ai-genai (4) |
| 12 | 5 | messaging (3), mechanism-targeted (2) |
| 13 | 2 | mechanism-targeted (2) |
| 14 | 5 | accessibility (2), adversarial (3) |
| 15 | 5 | adversarial (2), adversarial-policy (3) |
| 16 | 5 | ai-genai (4), architecture (1) |
| 17 | 5 | architecture (4), blockchain (1) |
| 18 | 5 | blockchain (1), cicd (4) |
| 19 | 5 | cicd (4), data (1) |
| 20 | 5 | data (4), database (1) |
| 21 | 5 | database (5) |
| 22 | 5 | database (2), database-migration (3) |
| 23 | 5 | disaster-recovery (3), erp (2) |
| 24 | 5 | erp (1), fleet-config (2), fng (2) |
| 25 | 5 | i18n (2), identity-access (2), idp (1) |
| 26 | 5 | idp (2), incident-response (3) |
| 27 | 5 | incident-response (5) |
| 28 | 5 | incident-response (2), infrastructure (3) |
| 29 | 5 | infrastructure (4), job-scheduling (1) |
| 30 | 5 | job-scheduling (1), kubernetes (4) |
| 31 | 5 | kubernetes (4), mao (1) |
| 32 | 5 | mao (2), mechanism-targeted (3) |
| 33 | 5 | mechanism-targeted (1), mobile (2), multi-cloud (2) |
| 34 | 5 | observability (5) |
| 35 | 5 | observability (1), payment (3), platform (1) |
| 36 | 5 | platform (5) |
| 37 | 5 | scp (3), search (2) |
| 38 | 5 | sre (3), telecom (2) |
| 39 | 3 | windows (3) |
| **Total** | **170** | **40 domains** |

## Quick Reference

| What | Command | LLM? | Cost | Time |
|------|---------|------|------|------|
| P0 validation | `python3 docs/field-test/v0.2.0/scripts/pre_run_validation.py` | No | $0 | 5 min |
| P2 deterministic | `pytest tests/field_test_v0_2_0/ -v --no-cov` | No | $0 | 45 min |
| P3 LLM tests | `pytest tests/field-test_v0_2_0/ -v --run-llm --no-cov` | Yes | ~$0.10 | 1-2 hr |
| P4 benchmarks | `python3 docs/field-test/v0.2.0/scripts/bench_*.py` | No | $0 | 30 min |
| P1+P5 all goals | `for i in $(seq 1 39); do python3 docs/field-test/scripts/batch-$(printf %02d $i).py; done` | Yes | ~$0.35 | 8-12 hr |
| **Total** | | | **~$0.45** | **~10-15 hr** |
