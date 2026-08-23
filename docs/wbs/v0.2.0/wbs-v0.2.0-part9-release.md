# WBS — PlannerCritic Engine v0.2.0 Part 9: Release Activities

> **Milestone covered:** M10 (Release Activities)
> **PRD covering this milestone:** [09-roadmap §9.2](../../design/prd/09-roadmap.md#92-v020-p1) · [06-security](../../design/prd/06-security-baseline.md) (§6.2 OpenSSF Silver, §6.3 Hardened) · [07-success-metrics](../../design/prd/07-success-metrics.md) (§7.1 roll-up)

---

## Milestone 10: Release Activities

**Objective:** Make v0.2.0 shippable and credible. Unlike M1–M9 (feature/surface work) this milestone is pure **release work**: packaging the new surfaces, re-validating security posture (OpenSSF Silver + Hardened), a release-gate field sweep, migration/backward-compat verification, release docs, the final quality gate, and the tag/ship. Mirrors the v0.1.0 M10 pattern but for the v0.2.0 surface set.

**PRD coverage:** §9.2 P1 roll-up; OpenSSF Silver; Hardened tier; §7.1 criteria; terminal state for v0.2.0.
**CUJs covered:** all P0 + new enterprise personas verified on the shipped package.

### M10.1 Packaging & pip release (#163)

- Re-verify `pyproject.toml` covers all new entry points + optional deps (rego/cel/notifier/domain packs/studio/IDP integrations). Confirm the pinned `hatchling<1.30` build (commit `6ca21c3`) still holds.
- Fresh-venv `pip install planner-critic` for base + each optional extra; `plancritic --help` lists new commands (check, policy, domains, packs, quota, lessons, diagnose, studio, dashboard, notifier). Build dist; stage/publish v0.2.0 on PyPI.

### M10.2 Security posture — OpenSSF Silver (#164)

- Re-run OpenSSF badge; fix findings from new surfaces. Verify HMAC/`X-Slack-Signature` + Teams JWT verification (#161) on callbacks before proxying; confirm redaction (#159) wired into every external-output surface.
- Update SECURITY.md + OWASP table; document v0.2.0 Hardened checklist rows.

### M10.3 Release-gate sweep + hermetic CI (#165)

- Run the full v0.2.0 field matrix incl. M9 new-domain corpora (#144–148); execute hermetic gate-regression (#126) + injection harness (#125) in CI (100% accuracy + injection-immunity).
- Confirm §7.1 release-critical criteria (blocker-detection ≥90% on seeded flaws; median revisions ≤2; no uncaught `PlanningError`). Any non-green row root-caused + fixed, or filed as a classified, documented caveat.

### M10.4 Migration & backward-compat (#166)

- Verify plan-store schema migration (F-27) is lossless from v0.1.0; existing v0.1.0 plans load/replay; `plancritic migrate` clean upgrade with `schema_version` matching code; diff/replay still work on pre-migration plans.

### M10.5 Release notes v0.2.0 (#167)

- `docs/reference/release-notes-v0.2.0.md`: changelog, breaking changes, upgrade path from v0.1.0. Update CHANGELOG + README quickstart; update API reference for new commands/packs/redaction/domain-pack protocol. Draft release summary.

### M10.6 Final quality gate (#168)

- ruff clean, mypy strict clean, coverage ≥95%, docstrings everywhere, full code review of all v0.2.0 changes resolved. Merge to main; tag v0.2.0; mark milestone complete.

### M10.7 Release coordination (#169)

- Mark all 0.2.0 milestones complete; zero open 0.2.0 issues except documented caveats; tag v0.2.0; crosslink release notes/announcement; update README install/quickstart to the released version.

### M10.8 Benchmarks (carried from M9)

The following benchmarks were deferred from M9 and are executed as part of the release gate:

| # | Issue | Description | Verification |
|---|-------|-------------|-------------|
| 8 | [#177](https://github.com/deghosal-2026/planner-critic-engine/issues/177) | Auto-repair benchmark — measure revision reduction on ordering-violation corpus | ≥30% revision reduction |
| 9 | [#182](https://github.com/deghosal-2026/planner-critic-engine/issues/182) | Rollback credibility field test — 21 goals across 8 domains, 3 credibility patterns | gate false-negative rate + critic recall |
| 10 | [#183](https://github.com/deghosal-2026/planner-critic-engine/issues/183) | Family-histogram stasis benchmark — retrospective revision reduction from family-based convergence | ≥20% revision reduction across 85+ strict-goal traces |

### M10.9 CodeReview bug-fix sweep

> **31 bugs filed as [#184–#214](https://github.com/deghosal-2026/planner-critic-engine/issues/184) during the M10 pre-release code review. All must be fixed before the release gate (unless filed as documented caveats). Grouped by subsystem below.**

| # | File(s) | Issue | Severity |
|---|---------|-------|----------|
| [#184](https://github.com/deghosal-2026/planner-critic-engine/issues/184) | `redaction.py:67,78-83` | Offset corruption leaves partial secrets exposed | Critical |
| [#185](https://github.com/deghosal-2026/planner-critic-engine/issues/185) | `redaction.py:65,93-109` | `redact_dict` loses audit trail for all but last string | Important |
| [#186](https://github.com/deghosal-2026/planner-critic-engine/issues/186) | `policy.py:206-209` | RegoGate passes input via `--data` not `--input` — OPA broken | Critical |
| [#187](https://github.com/deghosal-2026/planner-critic-engine/issues/187) | `guardrail.py:119-129` | `@re_gate` never calls wrapped function — dead code | Critical |
| [#188](https://github.com/deghosal-2026/planner-critic-engine/issues/188) | `loop/_controller.py:234-249` | Auto-converge is no-op stub; auto-repair trace findings dropped at line 367 | Important |
| [#189](https://github.com/deghosal-2026/planner-critic-engine/issues/189) | `loop/convergence.py:20-35` | `_plan_fingerprint` excludes task content — false stalled escalations | Important |
| [#190](https://github.com/deghosal-2026/planner-critic-engine/issues/190) | `loop/autofix.py:253-266` | Precondition closer injects duplicate task IDs | Important |
| [#191](https://github.com/deghosal-2026/planner-critic-engine/issues/191) | `server/mcp.py:329-343` | MCP server caches critic across different goals | Critical |
| [#192](https://github.com/deghosal-2026/planner-critic-engine/issues/192) | `eval/oracle.py:137-141` | Oracle double-counts aligned LLM findings as missed | Critical |
| [#193](https://github.com/deghosal-2026/planner-critic-engine/issues/193) | `quota.py:74-79,92-94` | Substring matching — restricted actions/clusters false positives | Important |
| [#194](https://github.com/deghosal-2026/planner-critic-engine/issues/194) | `drift.py:57-59,73-77` | Downgrade rate counts upgrades; underclaims false positives | Important |
| [#195](https://github.com/deghosal-2026/planner-critic-engine/issues/195) | `state.py:96-100` | `StateLock.WAIT` doesn't wait — behaves like `ESCALATE` | Important |
| [#196](https://github.com/deghosal-2026/planner-critic-engine/issues/196) | `cli/check.py:25-29` | `--fail-on-severity low` broken — INFO severity ignored | Important |
| [#197](https://github.com/deghosal-2026/planner-critic-engine/issues/197) | `cli/diagnose.py:38,138` | `KeyError: 'precondition'` in diagnostic rule | Critical |
| [#198](https://github.com/deghosal-2026/planner-critic-engine/issues/198) | `domains/secops/gates.py:30-32` | BlastRadiusGate ignores drain ordering | Important |
| [#199](https://github.com/deghosal-2026/planner-critic-engine/issues/199) | `domains/secops/gates.py:86,100-102` | LeastPrivilegeGate substring false positives | Important |
| [#200](https://github.com/deghosal-2026/planner-critic-engine/issues/200) | `domains/finops/gates.py:77-83` | BudgetBoundaryGate parses `target` as dollar amount | Important |
| [#201](https://github.com/deghosal-2026/planner-critic-engine/issues/201) | `rollback_synth.py:162-174` | Unknown actions default to `restore_snapshot` instead of noop | Important |
| [#202](https://github.com/deghosal-2026/planner-critic-engine/issues/202) | `domains/base.py:52` | `pack_config` at module scope, not in DomainPack Protocol | Important |
| [#203](https://github.com/deghosal-2026/planner-critic-engine/issues/203) | `notifier.py:307,313-317` | Dedup set has no TTL — unbounded growth | Important |
| [#204](https://github.com/deghosal-2026/planner-critic-engine/issues/204) | 89 strict-goal assertion YAMLs | `approve_expected: true` should be `false` | Important |
| [#205](https://github.com/deghosal-2026/planner-critic-engine/issues/205) | `goals/incident-response/ir-07-*` | Duplicate `ir-07` — adversarial billing duplicates `adv-01` | Critical |
| [#206](https://github.com/deghosal-2026/planner-critic-engine/issues/206) | `eval/label_migration.py:81,151-159` | Invariant gate allows verification to substitute for precondition | Important |
| [#207](https://github.com/deghosal-2026/planner-critic-engine/issues/207) | `escalation.py:160-175` | Rejects LLM blockers despite documenting only deterministic | Important |
| [#208](https://github.com/deghosal-2026/planner-critic-engine/issues/208) | 12 M9 assertion YAMLs | Assertions reference generic codes, not WBS-specified M9 codes | Important |
| [#209](https://github.com/deghosal-2026/planner-critic-engine/issues/209) | 14 M9 domain goals | Absent from plan, run scripts, and results report | Important |
| [#210](https://github.com/deghosal-2026/planner-critic-engine/issues/210) | `notifier.py:184-185` | Empty `signing_secret` silently accepts all callbacks | Important |
| [#211](https://github.com/deghosal-2026/planner-critic-engine/issues/211) | `adapters/autogen.py:139-140` | `_check_precondition` always returns `True` — re-gate never fires | Important |
| [#212](https://github.com/deghosal-2026/planner-critic-engine/issues/212) | `field_test_harness.py:521` | Passes `PlanVersion` instead of `Engine` — adapter never tested | Important |
| [#213](https://github.com/deghosal-2026/planner-critic-engine/issues/213) | `cli/templates.py:91` | Empty findings list — test subcommand never triggers | Important |
| [#214](https://github.com/deghosal-2026/planner-critic-engine/issues/214) | `field_test_harness.py:463-474` | Disconnected `SpendState` — trace metrics always zero | Important |

### M10 Task Checklist

| # | Task | Verify | Issue | Status |
|---|------|--------|-------|--------|
| 1 | Packaging + pip release | fresh-venv install of base + extras; `--help` lists new commands | [#163](https://github.com/deghosal-2026/planner-critic-engine/issues/163) · [ ] |
| 2 | Security posture (OpenSSF Silver + Hardened) | badge passing; callback signatures verified; redaction end-to-end | [#164](https://github.com/deghosal-2026/planner-critic-engine/issues/164) · [ ] |
| 3 | Release-gate sweep + hermetic CI | full matrix green; gate + injection hermetic; §7.1 met | [#165](https://github.com/deghosal-2026/planner-critic-engine/issues/165) · [x] |
| 4 | Migration & backward-compat | v0.1.0 → v0.2.0 lossless; replay works | [#166](https://github.com/deghosal-2026/planner-critic-engine/issues/166) · [ ] |
| 5 | Release notes v0.2.0 | doc authored; API reference + quickstart current | [#167](https://github.com/deghosal-2026/planner-critic-engine/issues/167) · [x] |
| 6 | Final quality gate | ruff/mypy/coverage ≥95; code review resolved; tagged | [#168](https://github.com/deghosal-2026/planner-critic-engine/issues/168) · [ ] |
| 7 | Release coordination | milestones closed; tag + announcement + README updated | [#169](https://github.com/deghosal-2026/planner-critic-engine/issues/169) · [ ] |
| 8 | Auto-repair benchmark (carried from M9) | ≥30% revision reduction on ordering-violation corpus | [#177](https://github.com/deghosal-2026/planner-critic-engine/issues/177) · [x] |
| 9 | Rollback credibility field test (carried from M9) | 21 goals across 8 domains, 3 credibility patterns; measure gate false-negative rate + critic recall | [#182](https://github.com/deghosal-2026/planner-critic-engine/issues/182) · [x] |
| 10 | Family-histogram stasis benchmark (carried from M9) | ≥20% revision reduction from family-based convergence signal across 85+ strict-goal traces | [#183](https://github.com/deghosal-2026/planner-critic-engine/issues/183) · [x] |
| 11 | **CodeReview bug-fix sweep** — fix or classify all 31 bugs | every [#184–#214](https://github.com/deghosal-2026/planner-critic-engine/issues/184) closed or filed as documented caveat | [#184–#214](https://github.com/deghosal-2026/planner-critic-engine/issues/184) · [x] |

### M10 Success Metrics

| Metric | Target | Verification |
|--------|--------|-------------|
| PyPI install | base + all extras on fresh venv | release smoke test |
| Security | OpenSSF Silver + Hardened rows verified | audit in SECURITY.md |
| Release gate | full v0.2.0 matrix green; hermetic CI passes | field-test report |
| Migration | lossless v0.1.0 → v0.2.0; replay works | migration suite |
| Docs | release notes + API reference current; quickstart runs | doc review |
| Quality | coverage ≥95; ruff + mypy strict clean; review done | final gate |
| Release | tag v0.2.0; milestones complete | tag + milestone closure |

### M10 Exit Gate

- [ ] Release-blocking issues: 0 (all gate failures resolved or filed as classified caveats)
- [x] All [#184–#214](https://github.com/deghosal-2026/planner-critic-engine/issues/184) CodeReview bugs fixed or filed as documented caveats
- [ ] Coverage > 95; lint clean; code review passed
- [ ] OpenSSF Silver + Hardened posture documented in SECURITY.md
- [ ] Quickstart + release notes verified from a clean venv
- [ ] `pip install planner-critic==0.2.0` from PyPI verified
- [ ] tag v0.2.0; all 0.2.0 milestones complete

**Dependency:** M1–M9. **Produces:** the **v0.2.0 release artifact** + foundation for v0.3.0 (P2 items — see [index](wbs-v0.2.0-index.md) and [09-roadmap §9.3](../../design/prd/09-roadmap.md#93-v030-p2)).