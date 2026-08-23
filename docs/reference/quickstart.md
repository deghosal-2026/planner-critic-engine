# User Guide — v0.2.0

## Install

```bash
pip install planner-critic
```

Verify:

```bash
plancritic --help
```

You should see the CLI help with available commands: `plan`, `critique`, `field-test`, `demo`, `quickstart`, `migrate`, `serve`.

## Configure an LLM Provider

The engine needs an LLM for both the planner and critic roles. Create a TOML config file:

```toml
# ~/.plancritic.toml
[roles]
planner = "local"
critic = "local"

[providers.local]
transport = "openai-compatible"
base_url = "https://openrouter.ai/api/v1"
model = "openai/gpt-4o-mini"
api_key = "${OPENROUTER_API_KEY}"
max_tokens = 16384
timeout_s = 300.0
```

Supported providers: OpenRouter, OpenAI, oMLX (local), Ollama (local).

## Run the Demo

```bash
plancritic demo --config ~/.plancritic.toml
```

This runs the bundled demo scenario: a PostgreSQL schema migration. The engine will:
1. Decompose the goal into a plan with tasks, dependencies, and ordering
2. Audit the plan with the critic
3. Revise if needed
4. Either approve or escalate

## Plan Your Own Goal

Create a goal JSON file:

```json
{
  "id": "my-migration",
  "description": "Add a NOT NULL column to a production PostgreSQL table. The table has 50M rows. Must backfill before applying the constraint. Tools: pgAdmin, psql.",
  "constraints": {
    "environment": "production",
    "tools": ["pgAdmin", "psql"]
  },
  "risk_tolerance": "balanced",
  "replan_policy": "patch"
}
```

Run:

```bash
plancritic plan my-migration.json --config ~/.plancritic.toml
```

## Understanding the Output

### Approved Plan

When the loop converges, you get an `ApprovedPlan` with:
- A list of tasks in execution order
- Dependencies between tasks
- Verification steps for high-risk tasks
- Rollback steps for each task
- Acknowledged warnings from the critic

### Escalation

When the loop cannot converge, you get an `Escalation` with:
- The plan revision that triggered the escalation
- The blocker finding that prevented approval
- A question for the human: "Approve, deny, or patch?"

## Risk Tolerance

### Balanced (recommended for normal operations)

Findings from the LLM critic are treated as advisory warnings. The deterministic gates are the hard floor. The plan approves even with warnings present.

### Strict (adversarial testing)

Zero tolerance for any finding — blockers OR warnings. The plan will escalate if the critic finds anything. Use this for safety-critical scenarios or adversarial testing.

## CLI Reference

| Command | Description |
|---------|-------------|
| `plancritic plan <goal>` | Plan a goal |
| `plancritic critique <plan>` | Critique a plan |
| `plancritic field-test run` | Run field test |
| `plancritic demo` | Run demo scenario |
| `plancritic quickstart` | Create and run sample goal |
| `plancritic migrate <old> <new>` | Migrate config |
| `plancritic serve` | Start HTTP server |

## Field Test

Run the full 157-goal field test suite:

```bash
plancritic field-test run --goals docs/field-test/goals/ --output ./results --config ~/.plancritic.toml
```

This produces a JSON report, per-goal traces, and LLM logs.

## Next Steps

- Read the [Architecture](docs/architecture/architecture-v0.1.0.md) doc
- Review the [API Reference](docs/reference/api.md)
- See the [Demo Scenario](docs/design/demo-scenario.md) walkthrough
- Check the [Field Test Results](docs/field-test/field-test-results-0.1.0.md)