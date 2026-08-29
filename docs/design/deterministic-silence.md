# Deterministic Silence — Why Trusted Layers Need Adversarial Assertions

> **F-20 design note.** Identified by Antonio Lopes Correia ([dev.to](https://dev.to/tonal/comment/3dmlo)).
> Shipped in v0.2.3 via transit-integrity check ([#296](https://github.com/deghosal-2026/planner-critic-engine/issues/296)).

## The Failure Class

A non-deterministic critic advertises its own unreliability. When `label_flip_rate = 1.000`, every trial disagrees — the variance signal is self-evident. A deterministic gate that silently corrupts a number (e.g. redaction mangling `0.033` into `0.[REDACTED_SECRET]`) fails identically on every trial. Repeated runs agree. The agreement reads as confidence. The variance signal vanishes exactly where the safety contract lives.

| Failure type | Variance signal | Misreads as confidence? |
|---|---|---|
| Non-deterministic critic (label_flip=1.0) | High — every trial disagrees | No |
| Deterministic gate corrupting a number | Zero — same failure every run | **Yes** |

## Mitigation

Every deterministic layer in the critical path needs its own adversarial assertion, separate from critic-variance metrics. The transit-integrity check (`src/planner_critic/redaction.py:verify_transit_integrity`) verifies numeric/boolean fields survive redaction unchanged. String changes are allowed only when they contain a known redaction placeholder. The Gate Canary (#278) provides the same guarantee for blocker classes.

## Design Rule

Trusted layers do not advertise their own failures. If you move safety into deterministic code, you must also add a health check that runs independently of the code's normal operation — using a known-bad input where failure = silence is impossible to misinterpret.