# Field Test Execution Guide

> **How to run the v0.2.0 field test.** Follow the phases in order.

## Prerequisites

```bash
# 1. Install the package
pip install -e .

# 2. Set up OpenRouter API key
export OPENROUTER_API_KEY="sk-or-..."

# 3. Verify the field-test config exists
cat plancritic-fieldtest.toml
```

## Directory Structure

```
docs/field-test/
├── README.md                  ← this file
├── goals/                     ← 170 goal JSON + assertion YAML files
├── scripts/                   ← batch runners (shared)
│   ├── README.md
│   ├── batch-01.py .. batch-13.py   ← v0.1.0 batches (65 goals)
│   ├── run_remaining.py        ← v0.1.0 catch-all (62 goals)
│   └── v0.2.0/                 ← v0.2.0-specific scripts
│       ├── pre_run_validation.py   ← P0 assertion validation
│       ├── bench_auto_repair.py    ← #177 auto-repair benchmark
│       ├── bench_rollback.py       ← #182 rollback credibility
│       └── bench_stasis.py         ← #183 family-histogram stasis
├── v0.1.0/                    ← v0.1.0 plan, results, traces
├── v0.2.0/                    ← v0.2.0 plan, results, traces
│   ├── field-test-plan.md
│   ├── reports/               ← per-goal traces (populated on run)
│   └── results/               ← benchmark JSON output
└── corpus/                    ← SWE-bench security oracle
```

## Execution Phases

### Phase 0 — Pre-run Validation (5 min, $0)

Validates all 170 assertion YAMLs before spending any LLM tokens.

```bash
python3 docs/field-test/v0.2.0/scripts/pre_run_validation.py
```

**Pass criteria:** `✅ All 170 goals validated successfully.`

### Phase 1 — New Domain Goals (17 goals, ~2-4 hours, ~$0.05)

Run the 17 new v0.2.0 goals (IDP, MAO, SRE, SCP, FNG, adversarial-policy) through the existing harness. These need a new batch script:

```bash
# Create and run the v0.2.0 new-goals batch
python3 -c "
import json, time, sys
from pathlib import Path
from planner_critic.field_test_harness import run_core_api
from planner_critic.llm.registry import ProviderRegistry
from planner_critic.loop import LoopConfig
from planner_critic.schema.goal import Goal

GOALS_ROOT = Path('docs/field-test/goals')
OUTPUT_ROOT = Path('docs/field-test/v0.2.0/reports/p1-new-goals')
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

SCENARIOS = [
    ('idp', 'idp-01-rbac-boundary'),
    ('idp', 'idp-02-naming-tagging'),
    ('idp', 'idp-03-quota-multi-tenant'),
    ('mao', 'mao-01-cyclic-handoff'),
    ('mao', 'mao-02-state-sync-precondition'),
    ('mao', 'mao-03-distributed-rollback'),
    ('sre', 'sre-01-blast-radius-guardrail'),
    ('sre', 'sre-02-telemetry-precondition'),
    ('sre', 'sre-03-destructive-hitl'),
    ('scp', 'scp-01-topological-propagation'),
    ('scp', 'scp-02-ci-pipeline-precheck'),
    ('scp', 'scp-03-canary-internal-dep'),
    ('fng', 'fng-01-cost-impact-threshold'),
    ('fng', 'fng-02-contractual-commitment'),
    ('adversarial-policy', 'adv-06-policy-violation'),
    ('adversarial-policy', 'adv-07-prompt-injection'),
    ('adversarial-policy', 'adv-08-disguised-exfiltration'),
]
print(f'Running {len(SCENARIOS)} new v0.2.0 goals...')
# See batch-01.py for the full run_core_api pattern
" 2>&1 | tee docs/field-test/v0.2.0/reports/p1-new-goals.log
```

Alternatively, use `run_remaining.py` with a domain filter:

```bash
python3 docs/field-test/scripts/run_remaining.py --domain idp,mao,sre,scp,fng,adversarial-policy
```

### Phase 2 — Deterministic Subsystem Tests (45 min, $0)

These are pytest tests — hermetic, no LLM, no network. Validates all v0.2.0 subsystems:

```bash
pytest tests/field_test_v0_2_0/test_wbs_coverage.py -v --no-cov
```

**What it covers (50 tests):**
- M1: positive control with all 4 domain packs
- M2: closer scope guard + oscillation K-window
- M3: CEL gate, pytest plugin, manifest loading
- M4: rollback synthesizer, partial rollback, SecOps gate ordering
- M5: standing rules, boundary cases, invariant gate
- M6: redactor modes, quota-posture, state lock WAIT
- M7: @re_gate / @escalate decorators
- M8: notifier dedup/signing, drift metrics
- P0: assertion validation

### Phase 3 — LLM-Required Subsystem Tests (1-2 hours, ~$0.10)

Tests that require a live LLM to validate (CLI dispatch, HTTP/MCP, adapters, critique modes, decorators, drift observability). Run with `--run-llm` flag:

```bash
pytest tests/field_test_v0_2_0/test_wbs_coverage.py -v --run-llm --no-cov
```

> Note: LLM tests require `OPENROUTER_API_KEY` and `plancritic-fieldtest.toml`.

### Phase 4 — Benchmarks (30 min, $0)

Retrospective analysis over existing traces — no new LLM calls:

```bash
# Auto-repair benchmark (#177) — ≥30% revision reduction target
python3 docs/field-test/v0.2.0/scripts/bench_auto_repair.py

# Rollback credibility field test (#182) — <5% false-negative target
python3 docs/field-test/v0.2.0/scripts/bench_rollback.py

# Family-histogram stasis benchmark (#183) — ≥20% savings at ≤5% FPR
python3 docs/field-test/v0.2.0/scripts/bench_stasis.py
```

Results are written to stdout (JSON). Redirect to files:

```bash
python3 docs/field-test/v0.2.0/scripts/bench_auto_repair.py > docs/field-test/v0.2.0/results/bench_auto_repair.json
python3 docs/field-test/v0.2.0/scripts/bench_rollback.py > docs/field-test/v0.2.0/results/bench_rollback.json
python3 docs/field-test/v0.2.0/scripts/bench_stasis.py > docs/field-test/v0.2.0/results/bench_stasis.json
```

### Phase 5 — Full Regression Sweep (6-8 hours, ~$0.30)

Re-run all 170 goals to confirm no regressions from v0.1.0. Uses the existing batch scripts + `run_remaining.py`.

#### v0.1.0 Inherited Goals (153 goals across 13 batches + run_remaining)

```bash
# Batches 1-13 (65 goals) — each batch runs 5 goals (batch-13 runs 2)
python3 docs/field-test/scripts/batch-01.py
python3 docs/field-test/scripts/batch-02.py
python3 docs/field-test/scripts/batch-03.py
python3 docs/field-test/scripts/batch-04.py
python3 docs/field-test/scripts/batch-05.py
python3 docs/field-test/scripts/batch-06.py
python3 docs/field-test/scripts/batch-07.py
python3 docs/field-test/scripts/batch-08.py
python3 docs/field-test/scripts/batch-09.py
python3 docs/field-test/scripts/batch-10.py
python3 docs/field-test/scripts/batch-11.py
python3 docs/field-test/scripts/batch-12.py
python3 docs/field-test/scripts/batch-13.py

# Remaining goals (62 goals not in batches 1-13)
python3 docs/field-test/scripts/run_remaining.py
```

#### v0.2.0 New Goals (17 goals — already run in P1)

Skip if P1 traces exist. Otherwise re-run:

```bash
python3 docs/field-test/scripts/run_remaining.py --domain idp,mao,sre,scp,fng,adversarial-policy
```

## Batch Summary Table

| Batch | Script | Goals | Domains |
|-------|--------|-------|---------|
| 01 | `batch-01.py` | 5 | database (4), kubernetes (1) |
| 02 | `batch-02.py` | 5 | kubernetes (2), cicd (3) |
| 03 | `batch-03.py` | 5 | incident-response (4), infrastructure (1) |
| 04 | `batch-04.py` | 5 | infrastructure (2), observability (3) |
| 05 | `batch-05.py` | 5 | architecture (2), data (2), platform (1) |
| 06 | `batch-06.py` | 5 | platform (2), greenfield (3) |
| 07 | `batch-07.py` | 5 | decommissioning (2), disaster-recovery (3) |
| 08 | `batch-08.py` | 5 | compliance (3), identity-access (2) |
| 09 | `batch-09.py` | 5 | serverless (2), adversarial-policy (3) |
| 10 | `batch-10.py` | 5 | networking (3), finops (2) |
| 11 | `batch-11.py` | 5 | finops (1), ai-genai (4) |
| 12 | `batch-12.py` | 5 | messaging (3), mechanism-targeted (2) |
| 13 | `batch-13.py` | 2 | mechanism-targeted (2) |
| remaining | `run_remaining.py` | ~62 | all domains not in batches 1-13 |
| new-v0.2.0 | (see P1 above) | 17 | idp (3), mao (3), sre (3), scp (3), fng (2), adversarial-policy (3) |
| **Total** | | **~170** | **40 domains** |

## Quick Reference

| What | Command | LLM? | Cost | Time |
|------|---------|------|------|------|
| P0 validation | `python3 docs/field-test/v0.2.0/scripts/pre_run_validation.py` | No | $0 | 5 min |
| P2 deterministic tests | `pytest tests/field_test_v0_2_0/ -v --no-cov` | No | $0 | 45 min |
| P3 LLM tests | `pytest tests/field_test_v0_2_0/ -v --run-llm --no-cov` | Yes | ~$0.10 | 1-2 hr |
| P4 benchmarks | `python3 docs/field-test/v0.2.0/scripts/bench_*.py` | No | $0 | 30 min |
| P1 new goals | `python3 docs/field-test/scripts/run_remaining.py --domain idp,mao,sre,scp,fng,adversarial-policy` | Yes | ~$0.05 | 2-4 hr |
| P5 full sweep | `python3 docs/field-test/scripts/batch-01.py` ... `batch-13.py` + `run_remaining.py` | Yes | ~$0.30 | 6-8 hr |
| **Total** | | | **~$0.45** | **~10-14 hr** |

## Output Locations

| Phase | Output directory |
|-------|-----------------|
| P1 traces | `docs/field-test/v0.2.0/reports/p1-new-goals/<goal-id>/core-api/<goal-id>/trace.json` |
| P2/P3 results | pytest stdout |
| P4 benchmarks | `docs/field-test/v0.2.0/results/bench_*.json` |
| P5 traces | `docs/field-test/v0.2.0/reports/p5-sweep/<goal-id>/core-api/<goal-id>/trace.json` |

## Troubleshooting

- **No LLM output:** Check `OPENROUTER_API_KEY` and `plancritic-fieldtest.toml`
- **0/0 results:** Re-run P0 validation (v0.1.0 learning #2)
- **Missing traces:** Check that `OUTPUT_ROOT` in batch scripts points to v0.2.0
- **Local model fails:** v0.1.0 proved local models insufficient — use cloud LLM
