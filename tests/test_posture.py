from __future__ import annotations

import os

import pytest

from planner_critic.posture import PostureResolver, PostureRule, ResolvedPosture
from planner_critic.schema.goal import RiskTolerance


class TestPostureResolver:
    def test_empty_rules_fallback_to_goal_posture(self) -> None:
        resolver = PostureResolver(rules=[])
        result = resolver.resolve(RiskTolerance.STRICT)
        assert result.posture is RiskTolerance.STRICT
        assert result.rule_id is None
        assert result.context_signal is None

    def test_single_env_rule_matches(self) -> None:
        resolver = PostureResolver(
            rules=[PostureRule(match={"env": "production"}, posture=RiskTolerance.STRICT)]
        )
        with _env(ENV="production"):
            result = resolver.resolve(RiskTolerance.BALANCED)
        assert result.posture is RiskTolerance.STRICT
        assert result.rule_id == 0
        assert "env=production" in (result.context_signal or "")

    def test_first_match_wins_ordered_rules(self) -> None:
        resolver = PostureResolver(
            rules=[
                PostureRule(match={"env": "production"}, posture=RiskTolerance.STRICT),
                PostureRule(match={"env": "staging"}, posture=RiskTolerance.BALANCED),
                PostureRule(match={"env": "dev"}, posture=RiskTolerance.PERMISSIVE),
            ]
        )
        with _env(ENV="staging"):
            result = resolver.resolve(RiskTolerance.STRICT)
        assert result.posture is RiskTolerance.BALANCED
        assert result.rule_id == 1

    def test_permissive_tier_from_context(self) -> None:
        resolver = PostureResolver(
            rules=[PostureRule(match={"env": "dev"}, posture=RiskTolerance.PERMISSIVE)]
        )
        with _env(ENV="dev"):
            result = resolver.resolve(RiskTolerance.STRICT)
        assert result.posture is RiskTolerance.PERMISSIVE

    def test_no_match_fallback(self) -> None:
        resolver = PostureResolver(
            rules=[PostureRule(match={"env": "production"}, posture=RiskTolerance.STRICT)]
        )
        with _env(ENV="testing"):
            result = resolver.resolve(RiskTolerance.BALANCED)
        assert result.posture is RiskTolerance.BALANCED
        assert result.rule_id is None

    def test_git_branch_context(self) -> None:
        resolver = PostureResolver(
            rules=[PostureRule(match={"git_branch": "main"}, posture=RiskTolerance.STRICT)]
        )
        with _env(PC_GIT_BRANCH="main"):
            result = resolver.resolve(RiskTolerance.BALANCED)
        assert result.posture is RiskTolerance.STRICT

    def test_multiple_context_signals(self) -> None:
        resolver = PostureResolver(
            rules=[
                PostureRule(
                    match={"env": "production", "deploy_target": "us-east-1"},
                    posture=RiskTolerance.STRICT,
                )
            ]
        )
        with _env(ENV="production", PC_TERRAFORM_WORKSPACE="us-east-1"):
            result = resolver.resolve(RiskTolerance.BALANCED)
        assert result.posture is RiskTolerance.STRICT

    def test_multiple_context_signals_mismatch(self) -> None:
        resolver = PostureResolver(
            rules=[
                PostureRule(
                    match={"env": "production", "deploy_target": "us-east-1"},
                    posture=RiskTolerance.STRICT,
                )
            ]
        )
        with _env(ENV="production", PC_TERRAFORM_WORKSPACE="us-west-2"):
            result = resolver.resolve(RiskTolerance.PERMISSIVE)
        assert result.posture is RiskTolerance.PERMISSIVE

    def test_regex_pattern_in_rule(self) -> None:
        resolver = PostureResolver(
            rules=[PostureRule(match={"git_branch": "re:feature/.*"}, posture=RiskTolerance.PERMISSIVE)]
        )
        with _env(PC_GIT_BRANCH="feature/add-auth"):
            result = resolver.resolve(RiskTolerance.STRICT)
        assert result.posture is RiskTolerance.PERMISSIVE

    def test_regex_no_match(self) -> None:
        resolver = PostureResolver(
            rules=[PostureRule(match={"git_branch": "re:main"}, posture=RiskTolerance.STRICT)]
        )
        with _env(PC_GIT_BRANCH="develop"):
            result = resolver.resolve(RiskTolerance.BALANCED)
        assert result.posture is RiskTolerance.BALANCED

    def test_platform_signal_pc_env(self) -> None:
        resolver = PostureResolver(
            rules=[PostureRule(match={"pc_env": "prod"}, posture=RiskTolerance.STRICT)]
        )
        with _env(PC_ENV="prod"):
            result = resolver.resolve(RiskTolerance.BALANCED)
        assert result.posture is RiskTolerance.STRICT

    def test_from_dict(self) -> None:
        data = [
            {"match": {"env": "production"}, "posture": "strict"},
            {"match": {"env": "dev"}, "posture": "permissive"},
        ]
        resolver = PostureResolver.from_dict(data)
        assert len(resolver._rules) == 2
        assert resolver._rules[0].posture is RiskTolerance.STRICT
        assert resolver._rules[1].posture is RiskTolerance.PERMISSIVE

    def test_resolved_posture_properties(self) -> None:
        rp = ResolvedPosture(posture=RiskTolerance.PERMISSIVE, rule_id=0, context_signal="env=dev")
        assert rp.reason_code == "posture_resolved"
        assert rp.posture is RiskTolerance.PERMISSIVE
        assert rp.rule_id == 0
        assert rp.context_signal == "env=dev"


class TestRiskTolerancePermissive:
    def test_permissive_enum_value(self) -> None:
        assert RiskTolerance.PERMISSIVE.value == "permissive"

    def test_permissive_is_distinct(self) -> None:
        assert RiskTolerance.PERMISSIVE is not RiskTolerance.STRICT
        assert RiskTolerance.PERMISSIVE is not RiskTolerance.BALANCED


@pytest.fixture(autouse=True)
def _auto_clean_env() -> ...:
    keys = ["ENV", "PC_ENV", "PC_GIT_BRANCH", "PC_TERRAFORM_WORKSPACE", "PC_K8S_NAMESPACE"]
    saved = {k: os.environ.get(k) for k in keys}
    yield
    for k in keys:
        if saved[k] is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = saved[k]


def _env(**kwargs: str) -> ...:
    """Context manager to temporarily set then restore env vars."""

    class _EnvCtx:
        def __enter__(self2) -> None:
            self2._saved = {}
            for k, v in kwargs.items():
                self2._saved[k] = os.environ.get(k)
                os.environ[k] = v

        def __exit__(self2, *args: object) -> None:
            for k, v in self2._saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    return _EnvCtx()
