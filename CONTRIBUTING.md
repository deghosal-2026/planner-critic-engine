# Contributing

## Setup

```bash
git clone https://github.com/deghosal-2026/planner-critic-engine.git
cd planner-critic-engine
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=planner_critic

# Specific test file
pytest tests/test_llm.py
```

## Code Quality

```bash
# Lint
ruff check src/ tests/

# Type check
mypy src/ tests/

# Format
ruff format src/ tests/
```

All three gates run in CI on every PR. The CI pipeline includes:
- `ruff check` — lint
- `ruff format --check` — formatting
- `mypy` — strict type checking
- `pytest` — unit tests
- `pytest --cov` — coverage report

## Commit Conventions

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`.
Scopes: `m9`, `m8`, `gates`, `critique`, `llm`, `cli`, `field-test`, `docs`, `meta`, etc.

Examples:
```
feat(gates): add precondition-closure gate
fix(critique): downgrade advisory families to warning
docs(m9): update field test results
```

## PR Template

```markdown
## What

[Brief description of the change]

## Why

[Motivation — bug, feature, design gap]

## How

[Technical approach]

## Testing

- [ ] Unit tests pass
- [ ] Lint passes
- [ ] Type check passes
- [ ] Manual testing (if applicable)
```

## Release Process

1. Update `CHANGELOG.md`
2. Tag version: `git tag v0.1.0`
3. Push tag: `git push --tags`
4. GitHub Actions builds and publishes to PyPI

## Code of Conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/).