"""Tests for critic/planner capability tier split (#257)."""

from __future__ import annotations

from pathlib import Path

from planner_critic.llm.registry import ProviderRegistry


class TestCapabilityTierSplit:
    """Separate providers for planner (cheap) vs critic (capable)."""

    def test_registry_supports_distinct_role_providers(self, tmp_path: Path) -> None:
        """A single config can map planner and critic to different providers."""
        config = tmp_path / "plancritic.toml"
        config.write_text(
            """
[roles]
planner = "fast"
critic = "capable"

[providers.fast]
transport = "openai-compatible"
base_url = "https://example.com/v1"
model = "openai/gpt-4o-mini"

[providers.capable]
transport = "openai-compatible"
base_url = "https://example.com/v1"
model = "openai/gpt-4o"
"""
        )
        reg = ProviderRegistry.load(config)
        assert reg.roles["planner"] == "fast"
        assert reg.roles["critic"] == "capable"

        planner_spec = reg.get_provider("planner")
        critic_spec = reg.get_provider("critic")
        assert planner_spec.model == "openai/gpt-4o-mini"
        assert critic_spec.model == "openai/gpt-4o"

    def test_tier_split_uses_different_models(self, tmp_path: Path) -> None:
        """The planner and critic resolve to different model tiers."""
        config = tmp_path / "plancritic.toml"
        config.write_text(
            """
[roles]
planner = "fast"
critic = "capable"

[providers.fast]
transport = "openai-compatible"
base_url = "https://example.com/v1"
model = "openai/gpt-4o-mini"

[providers.capable]
transport = "openai-compatible"
base_url = "https://example.com/v1"
model = "openai/gpt-4o"
"""
        )
        reg = ProviderRegistry.load(config)
        planner = reg.get_provider("planner")
        critic = reg.get_provider("critic")
        assert planner.model != critic.model
        assert planner.name == "fast"
        assert critic.name == "capable"

    def test_same_provider_for_both_roles_is_baseline(self, tmp_path: Path) -> None:
        """Default config maps both roles to the same provider (baseline)."""
        config = tmp_path / "plancritic.toml"
        config.write_text(
            """
[roles]
planner = "local"
critic = "local"

[providers.local]
transport = "openai-compatible"
base_url = "https://example.com/v1"
model = "openai/gpt-4o-mini"
"""
        )
        reg = ProviderRegistry.load(config)
        planner = reg.get_provider("planner")
        critic = reg.get_provider("critic")
        assert planner.model == critic.model == "openai/gpt-4o-mini"
