# Architecture

System architecture, specification, and data model for PlannerCritic Engine.

- [`architecture-v0.1.0.md`](architecture-v0.1.0.md) — High-level architecture (D1 seed, authored in M1; finalized in M9)
- `spec-v0.1.0.md` — Technical specification
- [`db-schema-sketch.md`](db-schema-sketch.md) — Plan store / versioning schema sketch (D4, authored in M2)

## M1 subsystem design docs

Authored with the milestone that built each subsystem (indexed in `../design/README.md`):

- `../design/design-seed.md` — M1 design seed (scope, tenets, exit criteria)
- `../design/plan-schema-design.md` — Goal / PlanVersion / Task schema (D2)
- `../design/loop-controller-design.md` — revise-until-approved loop controller (D3)
- `../design/design-decisions.md` — Design decision log (D13, DD-01..06)

## M2 subsystem design docs

- `../design/provider-layer-design.md` — config-driven provider registry + transport (D5)