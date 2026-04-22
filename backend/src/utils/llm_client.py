"""
统一的 LLM 客户端，支持 Claude 和千问 API
"""

from __future__ import annotations

import json
import time
from typing import Dict, List, Optional

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LLMClient:
    """统一的 LLM API 客户端"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        api_type: str = "claude",
        temperature: float = 0.3,
        timeout: int = 180
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.api_type = api_type
        self.temperature = temperature
        self.timeout = timeout

    def call(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        max_retries: int = 5
    ) -> str:
        """调用 LLM API"""
        for attempt in range(max_retries):
            try:
                if self.api_type == "claude":
                    return self._call_claude(user_prompt, system_prompt)
                elif self.api_type == "qwen":
                    return self._call_qwen(user_prompt, system_prompt)
                else:
                    raise ValueError(f"Unsupported API type: {self.api_type}")

            except Exception as e:
                print(f"[LLM Client] API call attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"[LLM Client] Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"All {max_retries} API call attempts failed: {e}")

    def _call_claude(self, user_prompt: str, system_prompt: Optional[str] = None) -> str:
        """调用 Claude API"""
        api_url = f"{self.base_url}/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": user_prompt}]
        }

        if system_prompt:
            payload["system"] = system_prompt

        proxies = {'http': None, 'https': None}
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=self.timeout,
            verify=False,
            proxies=proxies
        )

        response.raise_for_status()
        result = response.json()
        return result["content"][0]["text"]

    def _call_qwen(self, user_prompt: str, system_prompt: Optional[str] = None) -> str:
        """调用千问 API"""
        api_url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            # 千问可能不支持 system 角色，合并到 user 消息中
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            messages = [{"role": "user", "content": combined_prompt}]
        else:
            messages = [{"role": "user", "content": user_prompt}]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": 4096
        }

        proxies = {'http': None, 'https': None}
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=self.timeout,
            verify=False,
            proxies=proxies
        )

        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]

    def call_with_chunks(
        self,
        text: str,
        chunk_size: int,
        system_prompt: str,
        chunk_prompt_template: str,
        max_retries: int = 5
    ) -> List[Dict]:
        """分块调用 LLM API"""
        chunks = self._split_into_chunks(text, chunk_size)
        print(f"[LLM Client] 文本分为 {len(chunks)} 块")

        all_results = []
        for i, chunk in enumerate(chunks):
            print(f"[LLM Client] 处理第 {i+1}/{len(chunks)} 块...")
            chunk_prompt = chunk_prompt_template.format(chunk=chunk)

            try:
                response_text = self.call(chunk_prompt, system_prompt, max_retries)
                # 这里假设返回的是 JSON，需要解析
                from utils.json_payload import extract_json_payload
                chunk_result = extract_json_payload(response_text)

                if isinstance(chunk_result, list):
                    all_results.extend(chunk_result)
                elif isinstance(chunk_result, dict):
                    all_results.append(chunk_result)

                print(f"  - 发现 {len(chunk_result) if isinstance(chunk_result, list) else 1} 个结果")
            except Exception as e:
                print(f"  - 处理失败: {e}")
                continue

        return all_results

    def _split_into_chunks(self, text: str, chunk_size: int) -> List[str]:
        """将文本分块，尽量按段落分割"""
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks
