# Field Test Scripts

This directory contains hermetic (deterministic) and LLM-dependent field test scripts.

## Test files

| File | Type | What it tests |
|------|------|---------------|
| `test_wbs_coverage.py` | Hermetic | WBS coverage — verifies that field test results match documented expectations across all 183 goals |
| `test_live_boundary_run.py` | LLM-dependent | Runs the live-critic boundary evaluator against real models |

## Run all hermetic tests ($0, no LLM)

```bash
pytest tests/field_test/ -v --no-cov
```

These tests use stored results and stub critics. No LLM calls, no network required. Must pass before any LLM-dependent run.

## Run LLM-dependent tests

```bash
pytest tests/field_test/ -v --run-llm --no-cov
```

Requires `OPENROUTER_API_KEY` or a local provider configured in `plancritic.toml`.

## Run LLM field test sweep in parallel (4 batches)

The 183-goal corpus across 43 domains can be run in 4 parallel terminals
for faster iteration. Each batch is ~45-46 goals. Run in separate terminals:

```bash
# Terminal 1 — Batch A (11 domains, ~46 goals)
python3 docs/field-test/scripts/run-field.py --subsystem --all --run-llm --domain accessibility,adversarial,adversarial-benign,adversarial-policy,ai-genai,architecture,blockchain,cicd,compliance,compositional-injection,data

# Terminal 2 — Batch B (11 domains, ~46 goals)
python3 docs/field-test/scripts/run-field.py --subsystem --all --run-llm --domain database,database-migration,decommissioning,disaster-recovery,erp,finops,fleet-config,fng,greenfield,i18n,identity-access

# Terminal 3 — Batch C (11 domains, ~46 goals)
python3 docs/field-test/scripts/run-field.py --subsystem --all --run-llm --domain idp,incident-response,infrastructure,job-scheduling,kubernetes,mao,mechanism-targeted,messaging,mobile,multi-cloud,networking

# Terminal 4 — Batch D (10 domains, ~45 goals)
python3 docs/field-test/scripts/run-field.py --subsystem --all --run-llm --domain observability,payment,platform,scp,search,serverless,sre,telecom,well-formed-malicious,windows
```

After all 4 batches complete, run the hermetic tests to verify results:

```bash
pytest tests/field_test/ -v --no-cov
```

## Run gate canary (in-container)

```bash
plancritic gates canary --check
```

Runs all 10 gate canary fixtures. All 10 must pass before releasing.

## Run Docker integration tests

```bash
docker compose up -d
PC_INTEGRATION=1 pytest tests/docker/ -v --no-cov
```

Requires Docker compose services to be healthy. Tests CLI, HTTP, MCP, and healthz endpoints inside the container.

## Run full CI gate

```bash
pytest tests/field_test/ -v --no-cov && plancritic gates canary --check
```