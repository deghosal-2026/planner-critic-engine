# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | ✅ |
| 0.1.x   | ✅ |

## Reporting a Vulnerability

To report a security vulnerability, please open a private vulnerability report at:
https://github.com/deghosal-2026/planner-critic-engine/security/advisories/new

Do not open a public issue. You will receive a response within 48 hours.

## OWASP Top 10 Mitigation

| OWASP Category | Status | Mitigation |
|----------------|--------|------------|
| A01: Broken Access Control | Not applicable | The engine is a library/CLI tool, not a multi-tenant service. No user authentication or authorization model. |
| A02: Cryptographic Failures | Mitigated | No secrets stored in code. API keys passed via env vars or TOML config (not committed). Transport encryption via HTTPS for all LLM provider calls. Secret/PII redaction (#159) strips sensitive data from all external-output surfaces. Plan-signature persistence (#176) provides cryptographic integrity for approved plans. |
| A03: Injection | **Mitigated** | Deterministic gates (§2.5.1) are injection-immune — they do not read goal text. The LLM critic independently flags injection attempts. Proven by field test: adv-07 prompt injection was ignored. Webhook notifier verifies HMAC signatures (Slack `X-Slack-Signature`, Teams JWT) before proxying callbacks (#161). |
| A04: Insecure Design | Mitigated | Fail-closed contract (F-73): unapproved plans never reach an executor. Strict tolerance = zero findings tolerated. Escalation path for human override. Run budgets (#150) and state locking (#151) prevent resource exhaustion and concurrent-state corruption. |
| A05: Security Misconfiguration | Mitigated | Provider config validated on load. Default config uses local model (keyless). Cloud API key documented as env var. Posture rules (#149) can dynamically escalate risk tolerance based on environment context (env, git branch, deploy target). |
| A06: Vulnerable Components | Monitored | Python dependencies pinned in pyproject.toml. Dependabot configured for automated updates. |
| A07: Identification & Authentication Failures | Not applicable | No user auth in library/CLI tool. |
| A08: Software & Data Integrity Failures | Mitigated | PyPI provenance attestation via trusted publishing. Signed commits via GitHub. Plan-signature persistence (#176) hashes plan content on approval — tampering detected on replay. |
| A09: Security Logging & Monitoring | Mitigated | All LLM interactions logged to per-goal JSONL files. Loop termination reason recorded. Escalation events logged. Precondition ledger (#158) tracks every precondition establishment across plan versions. Finding-drift observability (#181) alerts when gate outcomes diverge from expected patterns. |
| A10: Server-Side Request Forgery | Not applicable | All outbound HTTP requests are to configured LLM provider endpoints only. No user-controlled URL input. Webhook URLs are configured, not user-supplied. |

## OpenSSF Scorecard

| Check | Status | Notes |
|-------|--------|-------|
| Binary-Artifacts | ✅ Pass | No binary artifacts in repo |
| Branch-Protection | ✅ Pass | main branch protected |
| CI-Tests | ✅ Pass | CI runs on every PR |
| Code-Review | ✅ Pass | PRs require review |
| Contributors | ✅ Pass | Active maintenance |
| Dangerous-Workflow | ✅ Pass | No dangerous workflow patterns |
| Dependency-Update-Tool | ✅ Pass | Dependabot configured |
| Fuzzing | ❌ Not implemented | Deferred to v0.3.0 |
| License | ✅ Pass | MIT license |
| Maintained | ✅ Pass | Active development |
| Pinned-Dependencies | ✅ Pass | Dependencies pinned |
| SAST | ✅ Pass | Ruff + mypy strict |
| Security-Policy | ✅ Pass | SECURITY.md present |
| Signed-Releases | ✅ Pass | Signed commits |
| Testing | ✅ Pass | pytest + coverage (threshold 92%) |
| Token-Permissions | ✅ Pass | Minimal token scope |
| Vulnerabilities | ✅ Pass | No known vulnerabilities |

## Hardened Security Tier (v0.2.0)

The Hardened tier adds v0.2.0 security features beyond the Essential baseline. All items must be verified before release.

- [x] **Secret/PII redaction** (#159) — regex-based redaction strips secrets and PII from all external-output surfaces (CLI stdout, HTTP responses, MCP tool results, notifier payloads). Audit trail preserved per redaction event.
- [x] **Webhook callback verification** (#161) — Slack `X-Slack-Signature` HMAC-SHA256 verification; Teams OAuth JWT verification. Callbacks with missing or invalid signatures are rejected before proxying.
- [x] **Plan-signature persistence** (#176) — cryptographic hash of plan content stored on approval. Replay verifies signature integrity; tampered plans detected on load.
- [x] **Run budgets** (#150) — hard limits on LLM spend per planning session (max tokens, max calls, max revisions). Exhaustion terminates the loop and escalates, preventing runaway costs.
- [x] **State locking** (#151) — `StateLock` guards concurrent plan revisions with WAIT/ESCALATE strategies. Prevents concurrent-state corruption from overlapping planning sessions.
- [x] **Dynamic posture** (#149) — environment-aware risk tolerance resolution. Posture rules match on env, git branch, deploy target, or k8s namespace using exact and regex patterns. Rules can escalate from `balanced` to `strict` in production contexts.
- [x] **Blast-radius quotas** (#132) — restrict concurrent task scope by action type and cluster. Prevents runaway destructive actions (e.g., >N resource changes per plan).
- [x] **Precondition ledger** (#158) — every precondition establishment is recorded with the plan version that created it. Drift detection alerts when preconditions established by a superseded plan version are used.
- [x] **Finding-drift observability** (#181) — tracks severity drift between LLM-assigned and code-enforced severity per finding. Alerts on sustained drift patterns.

## Essential Security Tier (Self-Audit)

- [x] **No secrets in code** — API keys use env vars or config files, not committed
- [x] **Fail-closed** — unapproved plans never reach executor
- [x] **Injection-immune** — deterministic gates don't read goal text
- [x] **Dependency scanning** — Dependabot enabled
- [x] **SAST** — Ruff + mypy strict in CI
- [x] **Signed commits** — all commits signed
- [x] **Branch protection** — main branch requires PR + review
- [x] **Security policy** — this file published
- [x] **Vulnerability reporting** — private advisory channel open
- [x] **Secret/PII redaction** — regex-based, wired into every external-output surface
- [x] **Webhook verification** — HMAC + JWT on callbacks, empty secret rejected
- [x] **Plan integrity** — cryptographic plan signatures, verified on replay
- [x] **Run budgets** — hard limits, fail-closed on exhaustion
- [x] **State isolation** — concurrent-plan locking
- [x] **Environment-aware posture** — dynamic tolerance in production contexts