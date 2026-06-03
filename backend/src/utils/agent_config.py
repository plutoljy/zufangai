"""Helpers for applying per-user LLM config to existing agents."""

from __future__ import annotations

from ai_provider_manager import ResolvedAgentConfig


def apply_llm_config(agent, config: ResolvedAgentConfig) -> None:
    agent.api_key = config.api_key
    agent.base_url = (config.base_url or "").rstrip("/")
    agent.model = config.model_name
    agent.api_type = config.api_type
    agent.use_llm = True


def build_chat_completions_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    return f"{normalized}/v1/chat/completions"


def build_anthropic_messages_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/messages"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/messages"
    return f"{normalized}/v1/messages"


def build_request_url(base_url: str) -> str:
    return base_url.rstrip("/")


def messages_to_prompt(messages: list[dict]) -> str:
    if not messages:
        return ""
    return "\n\n".join(str(message.get("content", "")) for message in messages)


def build_request_payload(
    *,
    model: str,
    messages: list[dict],
    temperature: float | None = None,
    max_tokens: int = 8192,
) -> dict:
    prompt = messages_to_prompt(messages)
    payload = {
        "model": model,
        "messages": messages,
        "prompt": prompt,
        "max_tokens": max_tokens,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    return payload


def extract_request_text(result: dict) -> str:
    if isinstance(result.get("text"), str):
        return result["text"]
    if isinstance(result.get("answer"), str):
        return result["answer"]
    if isinstance(result.get("response"), str):
        return result["response"]
    if isinstance(result.get("output"), str):
        return result["output"]

    data = result.get("data")
    if isinstance(data, dict):
        if isinstance(data.get("text"), str):
            return data["text"]
        if isinstance(data.get("answer"), str):
            return data["answer"]
        if isinstance(data.get("content"), str):
            return data["content"]

    choices = result.get("choices", [])
    if choices:
        return choices[0].get("message", {}).get("content", "") or choices[0].get(
            "text", ""
        )

    content = result.get("content", [])
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict):
            return first.get("text", "") or first.get("content", "")
        if isinstance(first, str):
            return first
    if isinstance(content, str):
        return content

    return ""
