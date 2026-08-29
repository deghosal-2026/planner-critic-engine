# Frozen-Claim Release Protocol — Extended

> **v0.2.3 additions.** Identified by Heinrich Neb, Artjoms Stukans, and Tae Kim (dev.to, Aug 27).
> Implements [#279](https://github.com/deghosal-2026/planner-critic-engine/issues/279).

## The Problem

The v0.2.2 frozen-claim protocol caught prose-versus-artifact discrepancies (e.g., "zero true failures" vs Scorecard B True Fail = 1). But three readers identified a deeper class:

- **Heinrich Neb**: "artifact-versus-reality — internally consistent all the way down. A claim 'measured across three machines over 24 hours' would pass a frozen-claim audit even when one machine had been failing to deliver for 45 hours."
- **Artjoms Stukans**: "My dashboards were green for six months while systemd restart counter showed the node had crash looped 17643 times. The claim measured the wrong metric."
- **Tae Kim**: "With LLM evaluation, 'the system blocks adversarial goals' can pass Monday and fail Thursday with zero code changes. Need model version and timestamp attached to every eval run."

## Protocol Additions

### 1. Denominator Completeness Requirement

For every claim about a measured set, answer: **"what was the denominator, and what evidence exists that it was complete?"**

Implementation: each frozen claim includes a `denominator` and `denominator_proof` field. The claim is verified only when both the value and the denominator come from the artifact chain.

### 2. Artifact Selection Freeze

Not just "what do you claim" but **"which artifact is allowed to prove it."**

Implementation: for each frozen claim, pre-commit to which specific artifact type proves it. If the claim passes the wrong artifact type, it is flagged as a category mismatch — even if the prose matches the wrong artifact perfectly.

### 3. Determinism Boundary Documentation

For every claim involving an LLM (critic behavior, blockage rate, convergence score):

- Attach exact model version, API request hash, and evaluation timestamp.
- Include a "determinism risk" annotation: *"This claim was verified at datetime X with model Y. A future run with a different model version may produce a different result."*
- Non-deterministic claims get a separate section with an explicit expiry.

## Strict Mode

`plancritic release verify --strict` validates all three additions:

- Rejects claims missing denominator evidence
- Rejects claims using the wrong artifact type
- Rejects LLM-dependent claims missing determinism boundary annotations