"""
Application configuration.
Loads values from backend/.env and environment variables.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Primary relay used by all LLM-backed agents.
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-5.4"

    # 千问 API 配置（主要 LLM）
    qwen_api_key: Optional[str] = None
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode"
    qwen_model: str = "qwen-max"

    # Claude API 配置（中转）
    claude_base_url: str = "https://web.codetab.cc"
    claude_api_key_opus: Optional[str] = None
    claude_api_key_sonnet: Optional[str] = None
    claude_api_key_beaver: Optional[str] = None  # Beaver 专用 API Key
    claude_base_url_beaver: Optional[str] = None  # Beaver 专用 Base URL
    claude_model_beaver: Optional[str] = None  # Beaver 专用模型
    claude_model_opus: str = "claude-opus-4-6"
    claude_model_sonnet: str = "claude-sonnet-4-6"

    # Deprecated provider fields kept only for backward compatibility.
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    anthropic_api_key: Optional[str] = None

    # Embeddings stay on Alibaba Cloud.
    embedding_api_key: str = ""
    embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_model: str = "text-embedding-v1"

    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_url: str = "http://localhost:5173"

    max_file_size: int = 52428800
    upload_dir: str = "data/uploads"

    # Supabase 配置
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    ai_provider_encryption_key: Optional[str] = None

    model_config = ConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "..", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


def validate_config(settings: Settings) -> None:
    warnings: list[str] = []

    if not settings.openai_api_key:
      warnings.append("[WARN] OPENAI_API_KEY is not configured; LLM-backed agents will fall back.")

    if not settings.embedding_api_key:
      warnings.append("[WARN] EMBEDDING_API_KEY is not configured; retriever embeddings will fail.")

    if not settings.supabase_url or not (
        settings.supabase_service_role_key or settings.supabase_key
    ):
      warnings.append(
          "[INFO] Supabase credentials are not configured; user preferences will be disabled."
      )

    if settings.supabase_url and settings.supabase_key and not settings.supabase_service_role_key:
      warnings.append(
          "[WARN] SUPABASE_SERVICE_ROLE_KEY is not configured; backend AI provider settings may be blocked by RLS in production."
      )

    if not settings.ai_provider_encryption_key:
      warnings.append(
          "[WARN] AI_PROVIDER_ENCRYPTION_KEY is not configured; saved AI provider keys will be encrypted with a derived fallback key."
      )

    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if not os.path.exists(env_path):
      warnings.append("[WARN] backend/.env was not found. Copy .env.example first.")

    if warnings:
      print("\n" + "=" * 60)
      print("Configuration check")
      for warning in warnings:
          print(f"  {warning}")
      print("=" * 60 + "\n")


try:
    settings = Settings()
    validate_config(settings)
except Exception as exc:
    print(f"\n[ERROR] Failed to load configuration: {exc}")
    print("Please check backend/.env or environment variables.\n")
    sys.exit(1)
