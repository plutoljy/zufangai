"""Unified LLM client supporting Claude, OpenAI, Qwen, and custom relay protocols."""

from __future__ import annotations

import time
from typing import Dict, List, Optional

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from utils.agent_config import (
    build_anthropic_messages_url,
    build_chat_completions_url,
    build_request_payload,
    build_request_url,
    extract_request_text,
)


class LLMClient:
    """Unified LLM API client with protocol abstraction and structured logging."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        api_type: str = "claude",
        temperature: float = 0.3,
        timeout: int = 180,
        agent_name: str = "llm",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.api_type = api_type
        self.temperature = temperature
        self.timeout = timeout
        self.agent_name = agent_name
        self._proxies = {"http": None, "https": None}

    def call(self, messages: List[Dict], max_retries: int = 5) -> str:
        """Call LLM with a messages list. Returns response text."""
        url = self._resolve_url()
        headers = self._build_headers()
        last_error: Exception | None = None

        for attempt in range(max_retries):
            start = time.time()
            try:
                payload = self._build_payload(messages)
                payload_size = len(str(payload))

                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                    verify=False,
                    proxies=self._proxies,
                )
                response.raise_for_status()
                content = self._parse_response(response.json())
                if not content:
                    raise ValueError("LLM returned empty content")

                duration = time.time() - start
                print(
                    f"[LLM] {self.agent_name} | {self.api_type} | {url} | "
                    f"{self.model} | {payload_size} bytes | {duration:.1f}s | ok"
                )
                return content

            except Exception as exc:
                last_error = exc
                duration = time.time() - start
                print(
                    f"[LLM] {self.agent_name} | {self.api_type} | {url} | "
                    f"{self.model} | - | {duration:.1f}s | failed: {exc}"
                )
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"[LLM] {self.agent_name}: retry {attempt + 1}/{max_retries} in {wait}s")
                    time.sleep(wait)

        raise RuntimeError(
            f"[LLM] {self.agent_name}: 调用失败 "
            f"(protocol={self.api_type}, endpoint={url}, "
            f"retried={max_retries}x): {last_error}"
        )

    def call_with_prompts(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 5,
    ) -> str:
        """Convenience: build messages from system + user prompt, then call."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.call(messages, max_retries)

    def _resolve_url(self) -> str:
        base = self.base_url.rstrip("/")
        if self.api_type == "claude":
            return build_anthropic_messages_url(base)
        if self.api_type == "request":
            return build_request_url(base)
        return build_chat_completions_url(base)

    def _build_headers(self) -> Dict[str, str]:
        if self.api_type == "claude":
            return {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, messages: List[Dict]) -> Dict:
        if self.api_type == "claude":
            return self._claude_payload(messages)
        if self.api_type == "qwen":
            return self._qwen_payload(messages)
        if self.api_type == "request":
            return build_request_payload(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=8192,
            )
        return self._openai_payload(messages)

    def _claude_payload(self, messages: List[Dict]) -> Dict:
        """Claude Messages API: system prompt merged into user message for relay compatibility."""
        system_text = ""
        user_parts: List[str] = []
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            else:
                user_parts.append(msg["content"])

        combined = f"{system_text}\n\n{''.join(user_parts)}" if system_text else "".join(user_parts)
        return {
            "model": self.model,
            "max_tokens": 8192,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": combined}],
        }

    def _openai_payload(self, messages: List[Dict]) -> Dict:
        """OpenAI-compatible: pass messages as-is (system as role)."""
        return {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": 8192,
        }

    def _qwen_payload(self, messages: List[Dict]) -> Dict:
        """Qwen: merge system into user message (same as Claude relay pattern)."""
        system_text = ""
        user_parts: List[str] = []
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            else:
                user_parts.append(msg["content"])

        combined = f"{system_text}\n\n{''.join(user_parts)}" if system_text else "".join(user_parts)
        return {
            "model": self.model,
            "messages": [{"role": "user", "content": combined}],
            "temperature": self.temperature,
            "max_tokens": 8192,
        }

    def _parse_response(self, result: Dict) -> str:
        if self.api_type == "claude":
            content_list = result.get("content", [])
            if not content_list:
                raise ValueError(f"Claude API returned empty content: {result}")
            return content_list[0].get("text", "")

        if self.api_type == "request":
            return extract_request_text(result)

        # openai / qwen
        choices = result.get("choices", [])
        if not choices:
            raise ValueError(f"OpenAI-compatible API returned empty choices: {result}")
        msg = choices[0].get("message", {})
        content = (
            msg.get("content", "")
            or msg.get("reasoning_content", "")
            or choices[0].get("text", "")
        )
        if not content:
            print(
                f"[LLM] {self.agent_name}: response has choices but no content, "
                f"keys={list(choices[0].keys())}"
            )
        return content
