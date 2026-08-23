"""Coverage tests for posture.py — PostureResolver and context collection."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from planner_critic.posture import (
    PostureResolver,
    PostureRule,
    ResolvedPosture,
    _matched_signal,
    _matches,
    register_context_source,
)
from planner_critic.schema.goal import RiskTolerance


def test_posture_rule_creation() -> None:
    rule = PostureRule(match={"env": "prod"}, posture=RiskTolerance.STRICT)
    assert rule.match == {"env": "prod"}
    assert rule.posture is RiskTolerance.STRICT


def test_resolved_posture_reason_code() -> None:
    rp = ResolvedPosture(posture=RiskTolerance.BALANCED, rule_id=None, context_signal=None)
    assert rp.reason_code is not None


def test_posture_resolver_from_dict() -> None:
    resolver = PostureResolver.from_dict(
        [
            {"match": {"env": "prod"}, "posture": "strict"},
            {"match": {"env": "dev"}, "posture": "balanced"},
        ]
    )
    assert len(resolver._rules) == 2


def test_posture_resolver_from_yaml(tmp_path: Path) -> None:
    yaml_file = tmp_path / "posture.yaml"
    yaml_file.write_text(
        yaml.dump(
            {
                "posture_rules": [
                    {"match": {"env": "prod"}, "posture": "strict"},
                ],
            }
        )
    )
    resolver = PostureResolver.from_yaml(str(yaml_file))
    assert len(resolver._rules) == 1


def test_posture_resolver_no_rules_fallback() -> None:
    resolver = PostureResolver()
    result = resolver.resolve(RiskTolerance.BALANCED)
    assert result.posture is RiskTolerance.BALANCED
    assert result.rule_id is None


def test_posture_resolver_match_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "prod")
    resolver = PostureResolver.from_dict(
        [
            {"match": {"env": "prod"}, "posture": "strict"},
        ]
    )
    result = resolver.resolve(RiskTolerance.BALANCED)
    assert result.posture is RiskTolerance.STRICT
    assert result.rule_id == 0
    assert result.context_signal is not None
    assert "env" in result.context_signal


def test_posture_resolver_match_regex(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "staging")
    resolver = PostureResolver.from_dict(
        [
            {"match": {"env": "re:stag.*"}, "posture": "strict"},
        ]
    )
    result = resolver.resolve(RiskTolerance.BALANCED)
    assert result.posture is RiskTolerance.STRICT


def test_posture_resolver_no_match_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "dev")
    resolver = PostureResolver.from_dict(
        [
            {"match": {"env": "prod"}, "posture": "strict"},
        ]
    )
    result = resolver.resolve(RiskTolerance.BALANCED)
    assert result.posture is RiskTolerance.BALANCED
    assert result.rule_id is None


def test_matches_exact() -> None:
    assert _matches({"env": "prod"}, {"env": "prod"})
    assert not _matches({"env": "prod"}, {"env": "dev"})


def test_matches_regex() -> None:
    assert _matches({"env": "re:prod.*"}, {"env": "production"})
    assert not _matches({"env": "re:dev.*"}, {"env": "production"})


def test_matched_signal() -> None:
    assert _matched_signal({"env": "prod"}, {"env": "prod"}) == "env=prod"
    assert _matched_signal({"env": ""}, {"env": ""}) == ""


def test_collect_context_git_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PC_GIT_BRANCH", "main")
    from planner_critic.posture import _collect_context

    ctx = _collect_context()
    assert ctx["git_branch"] == "main"


def test_register_context_source(monkeypatch: pytest.MonkeyPatch) -> None:
    register_context_source("custom", lambda: "custom_value")
    from planner_critic.posture import _collect_context

    ctx = _collect_context()
    assert ctx.get("custom") == "custom_value"
