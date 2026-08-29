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