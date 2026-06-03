"""Resolve per-user LLM configuration for analysis agents."""

from __future__ import annotations

from typing import Iterable

import requests

from ai_provider_manager import AIProviderConfig
from ai_provider_manager import AIProviderManager, ResolvedAgentConfig
from utils.agent_config import (
    build_anthropic_messages_url,
    build_chat_completions_url,
    build_request_payload,
    build_request_url,
    extract_request_text,
)


class AIProviderConfigurationError(RuntimeError):
    pass


class DynamicLLMClient:
    def __init__(
        self,
        provider_manager: AIProviderManager | None = None,
        access_token: str | None = None,
    ):
        self.provider_manager = provider_manager or AIProviderManager(
            access_token=access_token
        )

    def get_client_config_for_agent(
        self, user_id: str, agent_name: str
    ) -> ResolvedAgentConfig:
        try:
            return self.provider_manager.resolve_agent_config(user_id, agent_name)
        except Exception as exc:
            raise AIProviderConfigurationError(
                f"AI model for agent '{agent_name}' is not configured correctly: {exc}"
            ) from exc

    async def test_connection(self, config: AIProviderConfig) -> dict:
        api_type = self.provider_manager._infer_api_type(config.provider_name)
        try:
            base_url = (config.base_url or _default_base_url(config.provider_name)).rstrip("/")
            if api_type == "claude":
                response = requests.post(
                    build_anthropic_messages_url(base_url),
                    headers={
                        "x-api-key": config.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": config.model_name,
                        "max_tokens": 256,
                        "messages": [{"role": "user", "content": "ping"}],
                    },
                    timeout=20,
                    verify=False,
                    proxies={"http": None, "https": None},
                )
            elif api_type == "request":
                response = requests.post(
                    build_request_url(base_url),
                    headers={
                        "Authorization": f"Bearer {config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=build_request_payload(
                        model=config.model_name,
                        messages=[{"role": "user", "content": "ping"}],
                        max_tokens=256,
                    ),
                    timeout=20,
                    verify=False,
                    proxies={"http": None, "https": None},
                )
            else:
                response = requests.post(
                    build_chat_completions_url(base_url),
                    headers={
                        "Authorization": f"Bearer {config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": config.model_name,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 256,
                    },
                    timeout=20,
                    verify=False,
                    proxies={"http": None, "https": None},
                )
            response.raise_for_status()
            return {"success": True, "message": "Connection succeeded"}
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    async def diagnose_agent_connections(
        self, user_id: str, agent_names: Iterable[str]
    ) -> list[dict]:
        results: list[dict] = []
        for agent_name in agent_names:
            try:
                config = self.get_client_config_for_agent(user_id, agent_name)
                result = self._check_agent_connection(config)
            except Exception as exc:
                result = {
                    "agent_name": agent_name,
                    "provider_name": None,
                    "api_protocol": None,
                    "base_url": None,
                    "model_name": None,
                    "endpoint": None,
                    "success": False,
                    "message": str(exc),
                }
            self._log_agent_diagnostic(result)
            results.append(result)
        return results

    def _check_agent_connection(self, config: ResolvedAgentConfig) -> dict:
        endpoint = _endpoint_for_config(config)
        try:
            response = requests.post(
                endpoint,
                headers=_headers_for_config(config),
                json=_payload_for_config(config),
                timeout=20,
                verify=False,
                proxies={"http": None, "https": None},
            )
            response.raise_for_status()
            _extract_connection_probe_content(config, response.json())
            return {
                **_public_config_fields(config, endpoint),
                "success": True,
                "message": "Connection succeeded",
            }
        except Exception as exc:
            return {
                **_public_config_fields(config, endpoint),
                "success": False,
                "message": str(exc),
            }

    def _log_agent_diagnostic(self, result: dict) -> None:
        status = "ok" if result.get("success") else "failed"
        print(
            "[AI Provider] "
            f"{result.get('agent_name')}: "
            f"provider={result.get('provider_name') or '-'} "
            f"protocol={result.get('api_protocol') or '-'} "
            f"base_url={result.get('base_url') or '-'} "
            f"model={result.get('model_name') or '-'} "
            f"endpoint={result.get('endpoint') or '-'} "
            f"key={result.get('api_key_masked') or '-'} "
            f"check={status} "
            f"message={result.get('message')}"
        )


def _default_base_url(provider_name: str) -> str:
    if provider_name == "openai":
        return "https://api.openai.com"
    if provider_name == "qwen":
        return "https://dashscope.aliyuncs.com/compatible-mode/v1"
    return ""


def _api_protocol_for_config(config: ResolvedAgentConfig) -> str:
    if config.api_type == "claude":
        return "anthropic"
    if config.api_type == "qwen":
        return "qwen"
    if config.api_type == "request":
        return "request"
    return "openai"


def _endpoint_for_config(config: ResolvedAgentConfig) -> str:
    base_url = (config.base_url or _default_base_url(config.provider_name)).rstrip("/")
    if config.api_type == "request":
        return build_request_url(base_url)
    if config.api_type == "claude":
        return build_anthropic_messages_url(base_url)
    return build_chat_completions_url(base_url)


def _headers_for_config(config: ResolvedAgentConfig) -> dict[str, str]:
    if config.api_type == "claude":
        return {
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
    if config.api_type == "request":
        return {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
    return {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }


def _payload_for_config(config: ResolvedAgentConfig) -> dict:
    if config.api_type == "claude":
        return {
            "model": config.model_name,
            "max_tokens": 256,
            "messages": [{"role": "user", "content": "ping"}],
        }
    if config.api_type == "request":
        return build_request_payload(
            model=config.model_name,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=256,
        )
    return {
        "model": config.model_name,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 256,
    }


def _extract_connection_probe_content(config: ResolvedAgentConfig, result: dict) -> str:
    if config.api_type == "claude":
        content_list = result.get("content", [])
        if not content_list:
            raise ValueError(f"Anthropic-compatible API returned empty content: {result}")
        content = content_list[0].get("text", "")
    elif config.api_type == "request":
        content = extract_request_text(result)
    else:
        choices = result.get("choices", [])
        if not choices:
            print(f"[AI Provider] probe response (no choices): {str(result)[:500]}")
            raise ValueError(f"OpenAI-compatible API returned empty choices: {result}")
        msg = choices[0].get("message", {})
        content = (
            msg.get("content", "")
            or msg.get("reasoning_content", "")
            or choices[0].get("text", "")
        )

    if not content:
        print(f"[AI Provider] probe response (empty content): {str(result)[:500]}")
        raise ValueError("LLM connection probe returned empty content")
    return content


def _mask_key(key: str) -> str:
    if not key or len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


def _public_config_fields(config: ResolvedAgentConfig, endpoint: str) -> dict:
    return {
        "agent_name": config.agent_name,
        "provider_name": config.provider_name,
        "api_protocol": _api_protocol_for_config(config),
        "base_url": config.base_url,
        "model_name": config.model_name,
        "endpoint": endpoint,
        "api_key_masked": _mask_key(config.api_key),
    }
