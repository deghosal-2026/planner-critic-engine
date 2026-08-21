# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ |

## Reporting a Vulnerability

To report a security vulnerability, please open a private vulnerability report at:
https://github.com/deghosal-2026/planner-critic-engine/security/advisories/new

Do not open a public issue. You will receive a response within 48 hours.

## OWASP Top 10 Mitigation

| OWASP Category | Status | Mitigation |
|----------------|--------|------------|
| A01: Broken Access Control | Not applicable | The engine is a library/CLI tool, not a multi-tenant service. No user authentication or authorization model. |
| A02: Cryptographic Failures | Mitigated | No secrets stored in code. API keys passed via env vars or TOML config (not committed). Transport encryption via HTTPS for all LLM provider calls. |
| A03: Injection | **Mitigated** | Deterministic gates (§2.5.1) are injection-immune — they do not read goal text. The LLM critic independently flags injection attempts. Proven by field test: adv-07 prompt injection was ignored. |
| A04: Insecure Design | Mitigated | Fail-closed contract (F-73): unapproved plans never reach an executor. Strict tolerance = zero findings tolerated. Escalation path for human override. |
| A05: Security Misconfiguration | Mitigated | Provider config validated on load. Default config uses local model (keyless). Cloud API key documented as env var. |
| A06: Vulnerable Components | Monitored | Python dependencies pinned in pyproject.toml. Dependabot configured for automated updates. |
| A07: Identification & Authentication Failures | Not applicable | No user auth in library/CLI tool. |
| A08: Software & Data Integrity Failures | Mitigated | PyPI provenance attestation via trusted publishing. Signed commits via GitHub. |
| A09: Security Logging & Monitoring | Mitigated | All LLM interactions logged to per-goal JSONL files. Loop termination reason recorded. Escalation events logged. |
| A10: Server-Side Request Forgery | Not applicable | All outbound HTTP requests are to configured LLM provider endpoints only. No user-controlled URL input. |

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
| Fuzzing | ❌ Not implemented | Planned for v0.2.0 |
| License | ✅ Pass | MIT license |
| Maintained | ✅ Pass | Active development |
| Pinned-Dependencies | ✅ Pass | Dependencies pinned |
| SAST | ✅ Pass | Ruff + mypy strict |
| Security-Policy | ✅ Pass | SECURITY.md present |
| Signed-Releases | ✅ Pass | Signed commits |
| Testing | ✅ Pass | pytest + coverage |
| Token-Permissions | ✅ Pass | Minimal token scope |
| Vulnerabilities | ✅ Pass | No known vulnerabilities |

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