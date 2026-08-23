# Verification Data-Subject Semantics — v0.2.1 contract & v0.3.0 evolution (#230)

> **Status:** contract pinned in v0.2.1 (fixtures + derived semantics) · **Schema evolution:** proposed for v0.3.0 · **Refs:** [#219](https://github.com/deghosal-2026/planner-critic-engine/issues/219) · [#230](https://github.com/deghosal-2026/planner-critic-engine/issues/230) · community source: [Part 2 thread](https://dev.to/debashish_ghosal/i-told-my-llm-critic-to-be-adversarial-it-started-blocking-plans-for-being-not-thorough-enough-172#comment-3de1p)

## The two subjects

| Subject | Reads | Correct placement | Wrong side |
|---|---|---|---|
| **pre_state** | rollback preconditions, invariants, constraints existing before the write | before the mutate | after — reads a world the mutation replaced |
| **output** | the result the task exists to produce | after the mutate, consuming the output | before — asserts facts about state the mutation will replace |

Both wrong sides are vacuous verification. A gate that polices position
without understanding subject trains users to move every check early —
converting output checks into pre-state checks, i.e. the same drift wearing
the gate as cover.

## v0.2.1 contract (no schema change)

`VerificationStep` stays `{what, how, expected}`. The gate
(`gates/verification_ordering.py`) derives the subject:

* derivation rule — a consumer's verification whose ``what`` begins with
  ``pre-state`` (case-insensitive) is a **pre_state** check; anything else
  is **output** by default;
* enforcement — pre_state consumers must sit before their verified producer
  (early = silent); output consumers must sit after (late = silent);
  violations fire ``verification_after_consumer`` (BLOCKER, gate-layer).

Pinned by the triplet pairs in
`eval/label_migration.generate_boundary_cases()`:
`triplet-pre-state-before-mutate`, `triplet-output-after-mutate`.

## v0.3.0 evolution (schema diff sketch)

```python
class VerificationStep(BaseModel):
    what: str
    how: str
    expected: str
    subject: Literal["pre_state", "output"] | None = None   # NEW, optional
```

* Default ``None`` preserves the v0.2.1 prose-prefix derivation exactly —
  older serialized plans load unchanged and produce identical findings.
* When present, ``subject`` overrides derivation; the gate switches from
  positional derivation to explicit keying.
* Losslessness: plans are stored as canonical JSON blobs keyed by schema
  version; additive optional fields round-trip without migration because
  absent keys deserialize to ``None``. No ``PLAN_SCHEMA_VERSION`` bump is
  required while no persisted artifact depends on the field being present.

Adoption order: ship the field → migrate generator prompts to emit it →
flip the gate's primary source from derivation to field → retire the prose
prefix convention one minor release later.
