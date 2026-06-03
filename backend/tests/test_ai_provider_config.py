from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


class FakeTable:
    def __init__(self, rows):
        self.rows = rows
        self._payload = None
        self._filters = []
        self._select = "*"
        self.deleted = False

    def select(self, value):
        self._select = value
        return self

    def eq(self, key, value):
        self._filters.append((key, value))
        return self

    def upsert(self, payload, on_conflict=None):
        self._payload = payload
        self._on_conflict = on_conflict
        return self

    def delete(self):
        self.deleted = True
        return self

    def execute(self):
        if self._payload is not None:
            existing = None
            for row in self.rows:
                if all(
                    row.get(key) == self._payload.get(key)
                    for key in (self._on_conflict or "").split(",")
                    if key
                ):
                    existing = row
                    break
            if existing:
                existing.update(self._payload)
                return type("Result", (), {"data": [existing]})()
            next_row = {"id": f"row-{len(self.rows) + 1}", **self._payload}
            self.rows.append(next_row)
            return type("Result", (), {"data": [next_row]})()

        filtered = list(self.rows)
        for key, value in self._filters:
            filtered = [row for row in filtered if row.get(key) == value]

        if self.deleted:
            for row in list(filtered):
                self.rows.remove(row)
            return type("Result", (), {"data": filtered})()

        return type("Result", (), {"data": filtered})()


class FakeSupabaseClient:
    def __init__(self):
        self.enabled = True
        self.provider_rows = []
        self.agent_rows = []

    def table(self, name):
        if name == "ai_provider_configs":
            return FakeTable(self.provider_rows)
        if name == "agent_model_configs":
            return FakeTable(self.agent_rows)
        raise AssertionError(f"Unexpected table: {name}")


def test_provider_manager_encrypts_keys_and_returns_masked_configs(monkeypatch):
    from ai_provider_manager import AIProviderConfig, AIProviderManager

    fake_client = FakeSupabaseClient()
    manager = AIProviderManager(fake_client)

    config = AIProviderConfig(
        provider_name="openai",
        api_key="sk-secret-value",
        base_url="https://relay.example/v1",
        model_name="gpt-4o",
    )

    result = manager.save_provider("user-1", config)

    assert result.provider_name == "openai"
    assert result.has_api_key is True
    assert result.api_key_masked == "sk-...alue"
    assert fake_client.provider_rows[0]["api_key_encrypted"] != "sk-secret-value"

    listed = manager.list_providers("user-1")

    assert listed[0].api_key_masked == "sk-...alue"
    assert not hasattr(listed[0], "api_key")


def test_dynamic_client_requires_complete_user_agent_config():
    from ai_provider_manager import AIProviderManager
    from utils.dynamic_llm_client import (
        AIProviderConfigurationError,
        DynamicLLMClient,
    )

    manager = AIProviderManager(FakeSupabaseClient())
    client = DynamicLLMClient(manager)

    with pytest.raises(AIProviderConfigurationError, match="owl"):
        client.get_client_config_for_agent("user-1", "owl")


def test_dynamic_client_passes_access_token_to_provider_manager(monkeypatch):
    import utils.dynamic_llm_client as dynamic_llm_client

    captured = {}

    class CapturingProviderManager:
        def __init__(self, *, access_token=None):
            captured["access_token"] = access_token

        def resolve_agent_config(self, user_id, agent_name):
            raise ValueError("not needed")

    monkeypatch.setattr(
        dynamic_llm_client,
        "AIProviderManager",
        CapturingProviderManager,
    )

    dynamic_llm_client.DynamicLLMClient(access_token="request-jwt")

    assert captured["access_token"] == "request-jwt"


def test_dynamic_client_resolves_configured_agent():
    from ai_provider_manager import (
        AIProviderConfig,
        AgentModelConfig,
        AIProviderManager,
    )
    from utils.dynamic_llm_client import DynamicLLMClient

    fake_client = FakeSupabaseClient()
    manager = AIProviderManager(fake_client)
    manager.save_provider(
        "user-1",
        AIProviderConfig(
            provider_name="custom",
            api_key="relay-key",
            base_url="https://relay.example/v1",
            model_name="default-model",
        ),
    )
    manager.save_agent_config(
        "user-1",
        AgentModelConfig(
            agent_name="cat",
            provider_name="custom",
            model_name="writer-model",
        ),
    )

    config = DynamicLLMClient(manager).get_client_config_for_agent("user-1", "cat")

    assert config.api_key == "relay-key"
    assert config.base_url == "https://relay.example/v1"
    assert config.model_name == "writer-model"
    assert config.api_type == "request"


def test_dynamic_client_resolves_agent_owned_api_config():
    from ai_provider_manager import (
        AgentModelConfig,
        AIProviderManager,
    )
    from utils.dynamic_llm_client import DynamicLLMClient

    fake_client = FakeSupabaseClient()
    manager = AIProviderManager(fake_client)
    manager.save_agent_config(
        "user-1",
        AgentModelConfig(
            agent_name="owl",
            provider_name="claude",
            api_key="agent-claude-key",
            base_url="https://anthropic-relay.example",
            model_name="claude-sonnet-4-6",
        ),
    )

    config = DynamicLLMClient(manager).get_client_config_for_agent("user-1", "owl")

    assert config.api_key == "agent-claude-key"
    assert config.base_url == "https://anthropic-relay.example"
    assert config.model_name == "claude-sonnet-4-6"
    assert config.api_type == "claude"
    assert fake_client.agent_rows[0]["api_key_encrypted"] != "agent-claude-key"


def test_provider_manager_prefers_rpc_for_agent_config_upsert():
    from ai_provider_manager import (
        AgentModelConfig,
        AIProviderManager,
    )

    class FakeRpcSupabaseClient(FakeSupabaseClient):
        def __init__(self):
            super().__init__()
            self.rpc_calls = []

        def rpc(self, name, params):
            self.rpc_calls.append((name, params))

            class RpcRequest:
                def execute(inner_self):
                    row = {
                        "id": "rpc-row-1",
                        "user_id": params["p_user_id"],
                        "agent_name": params["p_agent_name"],
                        "provider_name": params["p_provider_name"],
                        "api_protocol": params["p_api_protocol"],
                        "api_key_encrypted": params["p_api_key_encrypted"],
                        "base_url": params["p_base_url"],
                        "model_name": params["p_model_name"],
                    }
                    self.agent_rows.append(row)
                    return type("Result", (), {"data": row})()

            return RpcRequest()

    fake_client = FakeRpcSupabaseClient()
    manager = AIProviderManager(fake_client)

    result = manager.save_agent_config(
        "user-1",
        AgentModelConfig(
            agent_name="owl",
            provider_name="custom",
            api_protocol="openai",
            api_key="agent-key",
            base_url="https://relay.example/v1",
            model_name="relay-model",
        ),
    )

    assert fake_client.rpc_calls[0][0] == "upsert_agent_model_config"
    rpc_params = fake_client.rpc_calls[0][1]
    assert rpc_params["p_user_id"] == "user-1"
    assert rpc_params["p_agent_name"] == "owl"
    assert rpc_params["p_api_key_encrypted"] != "agent-key"
    assert result.model_name == "relay-model"


def test_provider_manager_requires_new_key_when_agent_provider_changes():
    from ai_provider_manager import (
        AgentModelConfig,
        AIProviderManager,
    )

    fake_client = FakeSupabaseClient()
    manager = AIProviderManager(fake_client)
    manager.save_agent_config(
        "user-1",
        AgentModelConfig(
            agent_name="owl",
            provider_name="openai",
            api_protocol="openai",
            api_key="old-openai-key",
            base_url="https://api.openai.com/v1",
            model_name="gpt-4o",
        ),
    )

    with pytest.raises(ValueError, match="API Key"):
        manager.save_agent_config(
            "user-1",
            AgentModelConfig(
                agent_name="owl",
                provider_name="custom",
                api_protocol="openai",
                api_key=None,
                base_url="https://new-relay.example/v1",
                model_name="new-model",
            ),
        )


def test_chat_completions_url_accepts_full_endpoint():
    from utils.agent_config import (
        build_anthropic_messages_url,
        build_chat_completions_url,
    )

    assert (
        build_chat_completions_url("https://api.xiaomimimo.com/v1/chat/completions")
        == "https://api.xiaomimimo.com/v1/chat/completions"
    )
    assert (
        build_anthropic_messages_url("https://relay.example/v1")
        == "https://relay.example/v1/messages"
    )
    assert (
        build_anthropic_messages_url("https://relay.example/v1/messages")
        == "https://relay.example/v1/messages"
    )


def test_dynamic_client_diagnoses_agent_connection_without_leaking_key(
    monkeypatch, capsys
):
    import utils.dynamic_llm_client as dynamic_llm_client
    from ai_provider_manager import ResolvedAgentConfig
    from utils.dynamic_llm_client import DynamicLLMClient

    class FakeManager:
        def resolve_agent_config(self, user_id, agent_name):
            assert user_id == "user-1"
            assert agent_name == "owl"
            return ResolvedAgentConfig(
                agent_name="owl",
                provider_name="custom",
                api_key="super-secret-key",
                base_url="https://relay.example/v1",
                model_name="gpt-4o-mini",
                api_type="openai",
            )

    class FakeResponse:
        status_code = 200
        headers = {"content-type": "application/json"}

        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "pong"}}]}

    posted = {}

    def fake_post(url, headers, json, timeout, verify, proxies):
        posted["url"] = url
        posted["headers"] = headers
        posted["payload"] = json
        return FakeResponse()

    monkeypatch.setattr(dynamic_llm_client.requests, "post", fake_post)

    result = asyncio.run(
        DynamicLLMClient(FakeManager()).diagnose_agent_connections(
            "user-1", ["owl"]
        )
    )

    assert result[0]["agent_name"] == "owl"
    assert result[0]["provider_name"] == "custom"
    assert result[0]["api_protocol"] == "openai"
    assert result[0]["model_name"] == "gpt-4o-mini"
    assert result[0]["endpoint"] == "https://relay.example/v1/chat/completions"
    assert result[0]["success"] is True
    assert "super-secret-key" not in str(result)
    assert posted["headers"]["Authorization"] == "Bearer super-secret-key"

    output = capsys.readouterr().out
    assert "[AI Provider] owl" in output
    assert "model=gpt-4o-mini" in output
    assert "check=ok" in output
    assert "super-secret-key" not in output


def test_dynamic_client_diagnoses_request_protocol_with_direct_endpoint(
    monkeypatch, capsys
):
    import utils.dynamic_llm_client as dynamic_llm_client
    from ai_provider_manager import ResolvedAgentConfig
    from utils.dynamic_llm_client import DynamicLLMClient

    class FakeManager:
        def resolve_agent_config(self, user_id, agent_name):
            return ResolvedAgentConfig(
                agent_name="cat",
                provider_name="custom",
                api_key="relay-secret-key",
                base_url="https://relay.example/api/generate",
                model_name="relay-model",
                api_type="request",
            )

    class FakeResponse:
        status_code = 200
        headers = {"content-type": "application/json"}

        def raise_for_status(self):
            return None

        def json(self):
            return {"text": "pong"}

    posted = {}

    def fake_post(url, headers, json, timeout, verify, proxies):
        posted["url"] = url
        posted["headers"] = headers
        posted["payload"] = json
        return FakeResponse()

    monkeypatch.setattr(dynamic_llm_client.requests, "post", fake_post)

    result = asyncio.run(
        DynamicLLMClient(FakeManager()).diagnose_agent_connections(
            "user-1", ["cat"]
        )
    )

    assert result[0]["api_protocol"] == "request"
    assert result[0]["endpoint"] == "https://relay.example/api/generate"
    assert result[0]["success"] is True
    assert posted["url"] == "https://relay.example/api/generate"
    assert posted["payload"]["model"] == "relay-model"
    assert posted["payload"]["prompt"] == "ping"
    assert "relay-secret-key" not in str(result)
    assert "relay-secret-key" not in capsys.readouterr().out


def test_dynamic_client_diagnoses_missing_agent_config(capsys):
    from utils.dynamic_llm_client import DynamicLLMClient

    class FakeManager:
        def resolve_agent_config(self, user_id, agent_name):
            raise ValueError(f"Agent {agent_name} has not been configured")

    result = asyncio.run(
        DynamicLLMClient(FakeManager()).diagnose_agent_connections(
            "user-1", ["owl"]
        )
    )

    assert result[0]["agent_name"] == "owl"
    assert result[0]["success"] is False
    assert "not been configured" in result[0]["message"]
    assert "check=failed" in capsys.readouterr().out


def test_owl_openai_compatible_response_parses_choices(monkeypatch):
    import utils.llm_client as llm_client
    from agents.owl_analyst import OwlAnalyst
    from ai_provider_manager import ResolvedAgentConfig

    class FakeResponse:
        status_code = 200
        headers = {"content-type": "application/json"}

        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "openai ok"}}]}

    def fake_post(url, headers, json, timeout, verify, proxies):
        assert url == "https://relay.example/v1/chat/completions"
        assert headers["Authorization"] == "Bearer agent-key"
        return FakeResponse()

    monkeypatch.setattr(llm_client.requests, "post", fake_post)

    agent = OwlAnalyst(
        ResolvedAgentConfig(
            agent_name="owl",
            provider_name="custom",
            api_key="agent-key",
            base_url="https://relay.example/v1",
            model_name="gpt-4o-mini",
            api_type="openai",
        )
    )

    assert agent.llm.call(
        [{"role": "user", "content": "hello"}], max_retries=1
    ) == "openai ok"


def test_owl_request_protocol_uses_direct_endpoint_and_parses_text(monkeypatch):
    import utils.llm_client as llm_client
    from agents.owl_analyst import OwlAnalyst
    from ai_provider_manager import ResolvedAgentConfig

    class FakeResponse:
        status_code = 200
        headers = {"content-type": "application/json"}

        def raise_for_status(self):
            return None

        def json(self):
            return {"text": "request ok"}

    def fake_post(url, headers, json, timeout, verify, proxies):
        assert url == "https://relay.example/api/generate"
        assert headers["Authorization"] == "Bearer agent-key"
        assert json["prompt"] == "hello"
        return FakeResponse()

    monkeypatch.setattr(llm_client.requests, "post", fake_post)

    agent = OwlAnalyst(
        ResolvedAgentConfig(
            agent_name="owl",
            provider_name="custom",
            api_key="agent-key",
            base_url="https://relay.example/api/generate",
            model_name="relay-model",
            api_type="request",
        )
    )

    assert agent.llm.call(
        [{"role": "user", "content": "hello"}], max_retries=1
    ) == "request ok"
