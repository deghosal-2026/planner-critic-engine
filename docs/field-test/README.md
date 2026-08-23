# Field Test

Field test plans, reports, and validation matrices for all versions.

## Directory Structure

```
docs/field-test/
├── README.md
├── v0.1.0/          # v0.1.0 field test (156 goals, 8 adversarial)
│   ├── README.md
│   ├── field-test-plan.md
│   ├── field-test-results-0.1.0.md
│   ├── omlx-critique-modes-field-test.md
│   └── reports/     # per-goal traces and report artifacts
├── v0.2.0/          # v0.2.0 field test (176 goals, 11 adversarial)
│   ├── field-test-plan.md
│   └── README.md
├── goals/           # shared goal corpus (domain JSON + assertion YAML)
├── scripts/         # batch runners (shared across versions)
├── corpus/          # SWE-bench security oracle corpus
└── docker-integration.md
```

## Version History

| Version | Goals | Adversarial | Status | Report |
|---------|-------|-------------|--------|--------|
| v0.1.0 | 156 | 8 | ✅ Complete | `v0.1.0/field-test-results-0.1.0.md` |
| v0.2.0 | 176 | 11 | ⬜ Planned | `v0.2.0/field-test-plan.md` |