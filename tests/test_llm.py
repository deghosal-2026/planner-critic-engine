"""LLM provider layer tests (F-20..F-24): protocol, registry, transport, enforcer.

The hermetic contract: every test runs against a fake or httpx-mocked
transport with **zero network**. The provider protocol is asserted via a fake
conforming implementation; the registry via TOML round-trips; the OpenAI
transport via mocked ``httpx`` responses; the structured-output enforcer via
valid/invalid payload sequences.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import httpx
import pytest

from conftest import make_plan
from planner_critic.llm.base import (
    BadJSONError,
    Completion,
    LLMProvider,
    Message,
    ProviderError,
    ProviderTimeout,
    ToolSchema,
)
from planner_critic.llm.registry import (
    DEFAULT_ROLES,
    ProviderRegistry,
    ProviderSpec,
)
from planner_critic.llm.structured import StructuredEnforcer
from planner_critic.llm.transport_openai import OpenAICompatibleProvider
from planner_critic.schema.plan import PlanVersion
from planner_critic.types import PlanningError


class FakeProvider:
    """A minimal conforming provider; real-only, zero network."""

    name = "fake"
    base_url = "http://fake.local"
    model = "fake-model"

    def __init__(self, content: str = '{"ok": true}') -> None:
        """Store the canned completion content."""
        self.content = content
        self.calls = 0

    def complete(
        self,
        messages: Sequence[Message],
        tool_schemas: Sequence[ToolSchema] = (),
    ) -> Completion:
        """Return the canned completion and count the call."""
        self.calls += 1
        return Completion(content=self.content, finish_reason="stop")


def test_protocol_runtime_checkable() -> None:
    """A conforming implementation is recognized by the protocol."""
    assert isinstance(FakeProvider(), LLMProvider)


def test_provider_failure_types_are_fail_closed() -> None:
    """ProviderError subclasses share the base so the loop can catch them."""
    assert issubclass(ProviderTimeout, ProviderError)
    for exc in (ProviderTimeout("slow"), ProviderError("boom")):
        assert str(exc)


# --- Registry (F-21, F-23) --------------------------------------------------


def test_registry_empty_when_config_absent(tmp_path) -> None:
    """A missing config file yields an empty registry, not a crash."""
    registry = ProviderRegistry.load(tmp_path / "nope.toml")
    assert registry.providers == {}
    assert registry.roles == {}


def test_registry_skips_malformed_entries(tmp_path, caplog) -> None:
    """Malformed provider/role entries are skipped with a warning, not a crash."""
    bad = tmp_path / "bad.toml"
    bad.write_text('[providers]\nfoo = "not-a-table"\n\n[roles]\nplanner = 42\n')
    registry = ProviderRegistry.load(bad)
    assert registry.providers == {}
    assert registry.roles == {}
    assert "malformed" in caplog.text


def test_registry_add_save_load_round_trip(tmp_path) -> None:
    """A provider added + saved survives a reload (config persistence)."""
    path = tmp_path / "plancritic.toml"
    registry = ProviderRegistry.load(path)
    registry.add(
        "local",
        base_url="http://localhost:11434/v1",
        model="llama3.2",
        role="planner",
    )
    registry.save()

    reloaded = ProviderRegistry.load(path)
    assert reloaded.providers["local"] == ProviderSpec(
        name="local",
        transport="openai-compatible",
        base_url="http://localhost:11434/v1",
        model="llama3.2",
        api_key=None,
    )
    assert reloaded.roles == {"planner": "local"}


def test_registry_remove_unbinds_roles(tmp_path) -> None:
    """Removing a provider also clears its role bindings."""
    path = tmp_path / "plancritic.toml"
    registry = ProviderRegistry.load(path)
    registry.add("local", base_url="x", model="m", role="critic")
    assert registry.remove("local")
    assert "critic" not in registry.roles
    assert not registry.remove("local")


def test_registry_roles_survive_save(tmp_path) -> None:
    """Role→provider mapping persists through a save/reload."""
    path = tmp_path / "plancritic.toml"
    registry = ProviderRegistry.load(path)
    registry.add("p", base_url="a", model="m1", role="planner")
    registry.add("c", base_url="b", model="m2", role="critic")
    registry.save()
    reloaded = ProviderRegistry.load(path)
    assert reloaded.roles["planner"] == "p"
    assert reloaded.roles["critic"] == "c"


def test_registry_round_trip_handles_api_key(tmp_path) -> None:
    """An api-key-bearing provider round-trips with the key intact."""
    path = tmp_path / "plancritic.toml"
    registry = ProviderRegistry.load(path)
    registry.add("openai", base_url="https://api.openai.com/v1", model="gpt-4o",
                 api_key="sk-secret")
    registry.save()
    reloaded = ProviderRegistry.load(path)
    assert reloaded.providers["openai"].api_key == "sk-secret"


def test_get_provider_materializes_transport(tmp_path) -> None:
    """get_provider constructs a configured OpenAI-compatible transport."""
    registry = ProviderRegistry.load(tmp_path / "plancritic.toml")
    registry.add("local", base_url="http://x/v1", model="m", role="planner")
    provider = registry.get_provider("planner")
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "http://x/v1"


def test_get_provider_unbound_role_fails_closed() -> None:
    """An unbound role raises PlanningError (fail-closed, no silent default)."""
    registry = ProviderRegistry()
    with pytest.raises(PlanningError):
        registry.get_provider("planner")


def test_get_provider_unknown_reference_fails_closed(tmp_path) -> None:
    """A role pointing at a missing provider raises PlanningError."""
    registry = ProviderRegistry.load(tmp_path / "x.toml")
    registry.roles["planner"] = "ghost"
    with pytest.raises(PlanningError):
        registry.get_provider("planner")


def test_default_roles_are_planner_and_critic() -> None:
    """The registry owns exactly the two engine roles (F-23)."""
    assert DEFAULT_ROLES == ("planner", "critic")


# --- OpenAI-compatible transport (F-22) -------------------------------------


def _mock_client(json_payload: dict, status: int = 200) -> httpx.Client:
    """Build an httpx Client with a fixed JSON response."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=json_payload, request=request)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_transport_returns_completion() -> None:
    """A successful Chat Completions response yields a Completion."""
    provider = OpenAICompatibleProvider(
        name="local",
        base_url="http://localhost:11434/v1",
        model="llama3.2",
        client=_mock_client(
            {
                "choices": [
                    {"message": {"content": '{"plan": "ok"}'}, "finish_reason": "stop"}
                ]
            }
        ),
    )
    completion = provider.complete([Message(role="user", content="plan")])
    assert completion.content == '{"plan": "ok"}'
    assert completion.finish_reason == "stop"


def test_transport_sends_base_url_and_json_mode() -> None:
    """The request hits base_url/chat/completions with JSON mode requested."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]},
            request=request,
        )

    provider = OpenAICompatibleProvider(
        name="local",
        base_url="http://localhost:11434/v1",
        model="llama3.2",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    provider.complete([Message(role="user", content="plan")])

    import json

    assert captured[0].url == "http://localhost:11434/v1/chat/completions"
    body = json.loads(captured[0].content)
    assert body["response_format"] == {"type": "json_object"}
    assert body["model"] == "llama3.2"


def test_transport_sends_api_key_when_set() -> None:
    """An api_key is sent as a bearer header when configured."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer sk-x"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]},
            request=request,
        )

    provider = OpenAICompatibleProvider(
        name="openai",
        base_url="https://api.openai.com/v1",
        model="gpt-4o",
        api_key="sk-x",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    provider.complete([Message(role="user", content="hi")])


def test_transport_http_error_is_fail_closed() -> None:
    """An HTTP 500 surfaces ProviderTimeout (fail-closed, no guess)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom", request=request)

    provider = OpenAICompatibleProvider(
        name="local",
        base_url="http://x/v1",
        model="m",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(ProviderTimeout):
        provider.complete([Message(role="user", content="hi")])


def test_transport_bad_shape_is_bad_json() -> None:
    """A response without choices surfaces BadJSONError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True}, request=request)

    provider = OpenAICompatibleProvider(
        name="local",
        base_url="http://x/v1",
        model="m",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(BadJSONError):
        provider.complete([Message(role="user", content="hi")])


def test_transport_timeout_is_provider_timeout() -> None:
    """A transport-level timeout surfaces ProviderTimeout."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    provider = OpenAICompatibleProvider(
        name="local",
        base_url="http://x/v1",
        model="m",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(ProviderTimeout):
        provider.complete([Message(role="user", content="hi")])


# --- Structured-output enforcement (F-24, F-70) ------------------------------


def test_enforcer_validates_on_first_try() -> None:
    """A schema-valid completion validates immediately (1 call)."""
    payload = make_plan(plan_id="p", version=1).to_dict()
    provider = FakeProvider(content=_json(payload))
    enforcer = StructuredEnforcer(provider, max_retries=2)
    plan = enforcer.complete([Message(role="user", content="plan")], PlanVersion)
    assert plan.id == "p"
    assert provider.calls == 1


def test_enforcer_retries_bad_json_then_succeeds() -> None:
    """mismatch → retry → success honors the bounded retry budget."""
    calls = {"n": 0}

    class FlakyProvider(FakeProvider):
        def complete(self, messages, tool_schemas=()):
            calls["n"] += 1
            if calls["n"] == 1:
                return Completion(content="not json", finish_reason="stop")
            return Completion(content=_valid_plan_json(), finish_reason="stop")

    enforcer = StructuredEnforcer(FlakyProvider(), max_retries=2)
    plan = enforcer.complete([Message(role="user", content="plan")], PlanVersion)
    assert plan.id == "p"
    assert calls["n"] == 2


def test_enforcer_retries_schema_mismatch_then_succeeds() -> None:
    """A wrong-schema payload is retried, then the right one validates."""
    calls = {"n": 0}

    class WrongFirst(FakeProvider):
        def complete(self, messages, tool_schemas=()):
            calls["n"] += 1
            if calls["n"] == 1:
                return Completion(content='{"not_a_plan": true}', finish_reason="stop")
            return Completion(content=_valid_plan_json(), finish_reason="stop")

    enforcer = StructuredEnforcer(WrongFirst(), max_retries=2)
    plan = enforcer.complete([Message(role="user", content="plan")], PlanVersion)
    assert plan.id == "p"
    assert calls["n"] == 2


def test_enforcer_persistent_mismatch_fails_closed() -> None:
    """Persistent mismatch exhausts retries then raises PlanningError."""
    provider = FakeProvider(content=_json({"not": "a plan"}))
    enforcer = StructuredEnforcer(provider, max_retries=2)
    with pytest.raises(PlanningError) as excinfo:
        enforcer.complete([Message(role="user", content="plan")], PlanVersion)
    assert excinfo.value.reason_code == "planning_unavailable"
    assert provider.calls == 3  # max_retries + 1 attempts


def test_enforcer_tolerates_markdown_fences() -> None:
    """Markdown-fenced JSON is parsed despite the fences."""
    payload = make_plan(plan_id="p", version=1).to_dict()
    provider = FakeProvider(content=f"```json\n{_json(payload)}\n```")
    enforcer = StructuredEnforcer(provider, max_retries=1)
    assert enforcer.complete([Message(role="user", content="plan")], PlanVersion).id == "p"


def _json(data: dict) -> str:
    """Render a dict as compact JSON."""
    return json.dumps(data)


def _valid_plan_json() -> str:
    """Render a valid PlanVersion as JSON (test helper)."""
    return _json(make_plan(plan_id="p", version=1).to_dict())


# --- providers CLI (F-21) ----------------------------------------------------


def test_providers_cli_add_persists(tmp_path, capsys) -> None:
    """``providers add`` writes the config file for a later reload."""
    from planner_critic.cli.providers import run_providers

    config = tmp_path / "plancritic.toml"
    assert (
        run_providers(
            [
                "--config",
                str(config),
                "add",
                "local",
                "--base-url",
                "http://localhost:11434/v1",
                "--model",
                "llama3.2",
                "--role",
                "planner",
            ]
        )
        == 0
    )
    assert "added provider 'local'" in capsys.readouterr().out
    assert ProviderRegistry.load(config).roles["planner"] == "local"


def test_providers_cli_list_shows_roles_and_providers(tmp_path, capsys) -> None:
    """``providers list`` renders role bindings and provider definitions."""
    from planner_critic.cli.providers import run_providers

    config = tmp_path / "plancritic.toml"
    registry = ProviderRegistry.load(config)
    registry.add("local", base_url="http://x/v1", model="m", role="planner")
    registry.save()

    assert run_providers(["--config", str(config), "list"]) == 0
    out = capsys.readouterr().out
    assert "planner -> local" in out
    assert "local: openai-compatible @ http://x/v1 [m]" in out


def test_providers_cli_rm_removes(tmp_path, capsys) -> None:
    """``providers rm`` removes a provider and persists the change."""
    from planner_critic.cli.providers import run_providers

    config = tmp_path / "plancritic.toml"
    registry = ProviderRegistry.load(config)
    registry.add("local", base_url="http://x/v1", model="m", role="critic")
    registry.save()

    assert run_providers(["--config", str(config), "rm", "local"]) == 0
    assert "removed provider 'local'" in capsys.readouterr().out
    assert "local" not in ProviderRegistry.load(config).providers


def test_providers_cli_rm_missing_is_nonzero(tmp_path, capsys) -> None:
    """Removing a nonexistent provider fails with a nonzero exit code."""
    from planner_critic.cli.providers import run_providers

    config = tmp_path / "plancritic.toml"
    assert run_providers(["--config", str(config), "rm", "ghost"]) == 1
    assert "no provider named 'ghost'" in capsys.readouterr().out


def test_transport_sends_tool_schemas() -> None:
    """Tool schemas are serialized into the request payload when provided."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]},
            request=request,
        )

    provider = OpenAICompatibleProvider(
        name="local",
        base_url="http://x/v1",
        model="m",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    provider.complete(
        [Message(role="user", content="hi")],
        tool_schemas=[
            ToolSchema(name="lookup", description="find", parameters={"type": "object"})
        ],
    )
    body = json.loads(captured[0].content)
    assert body["tools"][0]["function"]["name"] == "lookup"


def test_enforcer_non_object_json() -> None:
    """A top-level JSON array is rejected as non-object."""
    provider = FakeProvider(content="[1, 2, 3]")
    enforcer = StructuredEnforcer(provider, max_retries=0)
    with pytest.raises(PlanningError):
        enforcer.complete([Message(role="user", content="plan")], PlanVersion)


def test_enforcer_uses_json_fence_prefix() -> None:
    """A ```json```-prefixed fence is handled like a plain fence."""
    payload = make_plan(plan_id="p", version=1).to_dict()
    provider = FakeProvider(content=f"```json\n{_json(payload)}\n```")
    enforcer = StructuredEnforcer(provider, max_retries=1)
    assert enforcer.complete([Message(role="user", content="plan")], PlanVersion).id == "p"


def test_transport_non_string_content_is_bad_json() -> None:
    """A non-string message content surfaces BadJSONError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": 123}, "finish_reason": "stop"}]},
            request=request,
        )

    provider = OpenAICompatibleProvider(
        name="local",
        base_url="http://x/v1",
        model="m",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(BadJSONError):
        provider.complete([Message(role="user", content="hi")])


def test_transport_length_truncation_is_fail_closed() -> None:
    """A truncated JSON-mode completion surfaces ProviderTimeout immediately."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "[1.1]"}, "finish_reason": "length"}]},
            request=request,
        )

    provider = OpenAICompatibleProvider(
        name="local",
        base_url="http://x/v1",
        model="m",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(ProviderTimeout):
        provider.complete([Message(role="user", content="hi")])
