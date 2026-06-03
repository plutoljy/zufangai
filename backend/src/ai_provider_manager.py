"""User-owned AI provider and agent model configuration."""

from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from typing import Literal, Optional

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, Field, field_validator

from config import settings
from database.supabase_client import supabase_client

ProviderName = Literal["openai", "claude", "qwen", "custom"]
AgentName = Literal["owl", "dog", "beaver", "cat"]
APIProtocol = Literal["openai", "anthropic", "qwen", "request"]


class AIProviderConfig(BaseModel):
    provider_name: ProviderName
    api_key: str = Field(min_length=1, max_length=4096)
    base_url: Optional[str] = Field(default=None, max_length=2048)
    model_name: str = Field(min_length=1, max_length=256)
    is_active: bool = True

    @field_validator("provider_name", mode="before")
    @classmethod
    def normalize_provider_name(cls, value: str) -> str:
        return str(value).strip().lower()

    @field_validator("api_key", "model_name")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be empty")
        return value

    @field_validator("base_url")
    @classmethod
    def normalize_base_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip().rstrip("/")
        return value or None


class AIProviderPatch(BaseModel):
    api_key: Optional[str] = Field(default=None, min_length=1, max_length=4096)
    base_url: Optional[str] = Field(default=None, max_length=2048)
    model_name: str = Field(min_length=1, max_length=256)
    is_active: bool = True

    @field_validator("api_key", "model_name")
    @classmethod
    def strip_required_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be empty")
        return value

    @field_validator("base_url")
    @classmethod
    def normalize_base_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip().rstrip("/")
        return value or None


class AIProviderPublic(BaseModel):
    provider_name: ProviderName
    base_url: Optional[str] = None
    model_name: str
    is_active: bool = True
    has_api_key: bool = False
    api_key_masked: Optional[str] = None


class AgentModelConfig(BaseModel):
    agent_name: AgentName
    provider_name: ProviderName
    api_protocol: Optional[APIProtocol] = None
    api_key: Optional[str] = Field(default=None, min_length=1, max_length=4096, exclude=True)
    base_url: Optional[str] = Field(default=None, max_length=2048)
    model_name: str = Field(min_length=1, max_length=256)
    has_api_key: bool = False
    api_key_masked: Optional[str] = None

    @field_validator("agent_name", "provider_name", "api_protocol", mode="before")
    @classmethod
    def normalize_names(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return str(value).strip().lower()

    @field_validator("api_key", "model_name")
    @classmethod
    def strip_model_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be empty")
        return value

    @field_validator("base_url")
    @classmethod
    def normalize_base_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip().rstrip("/")
        return value or None


@dataclass(frozen=True)
class ResolvedAgentConfig:
    agent_name: AgentName
    provider_name: ProviderName
    api_key: str
    base_url: Optional[str]
    model_name: str
    api_type: Literal["openai", "claude", "qwen", "request"]


class AIProviderStorageError(RuntimeError):
    pass


class _RequestScopedSupabaseClient:
    def __init__(self, client):
        self.client = client
        self.enabled = True


class AIProviderManager:
    def __init__(
        self,
        client=None,
        encryption_key: str | bytes | None = None,
        access_token: str | None = None,
    ):
        self.client = client or self._build_request_scoped_client(access_token) or supabase_client
        self.cipher = Fernet(self._resolve_encryption_key(encryption_key))

    def _build_request_scoped_client(self, access_token: str | None):
        if (
            not access_token
            or settings.supabase_service_role_key
            or not settings.supabase_url
            or not settings.supabase_key
        ):
            return None

        try:
            from supabase import create_client

            client = create_client(settings.supabase_url, settings.supabase_key)
            client.postgrest.auth(access_token)
            return _RequestScopedSupabaseClient(client)
        except Exception as exc:
            raise AIProviderStorageError(
                "Unable to create Supabase client for authenticated user"
            ) from exc

    def _resolve_encryption_key(self, explicit_key: str | bytes | None) -> bytes:
        raw_key = explicit_key or os.getenv("AI_PROVIDER_ENCRYPTION_KEY") or os.getenv(
            "ENCRYPTION_KEY"
        )
        if raw_key:
            return raw_key.encode("utf-8") if isinstance(raw_key, str) else raw_key

        seed = os.getenv("JWT_SECRET_KEY") or "local-development-ai-provider-key"
        digest = hashlib.sha256(seed.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)

    def _table(self, name: str):
        if not getattr(self.client, "enabled", False) or not getattr(
            self.client, "client", self.client
        ):
            raise AIProviderStorageError("Supabase is not configured")

        table_owner = getattr(self.client, "client", self.client)
        return table_owner.table(name)

    def _rpc(self, name: str, params: dict):
        client_owner = getattr(self.client, "client", self.client)
        rpc_method = getattr(client_owner, "rpc", None)
        if rpc_method is None:
            return None
        return rpc_method(name, params).execute()

    def _encrypt_api_key(self, api_key: str) -> str:
        return self.cipher.encrypt(api_key.encode("utf-8")).decode("utf-8")

    def _decrypt_api_key(self, encrypted_api_key: str) -> str:
        try:
            return self.cipher.decrypt(encrypted_api_key.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise AIProviderStorageError("Unable to decrypt AI provider API key") from exc

    def _mask_api_key(self, api_key: str) -> str:
        if len(api_key) <= 8:
            return "****"
        return f"{api_key[:3]}...{api_key[-4:]}"

    def _provider_public_from_row(self, row: dict) -> AIProviderPublic:
        encrypted_key = row.get("api_key_encrypted") or row.get("api_key")
        masked_key = None
        has_api_key = bool(encrypted_key)
        if encrypted_key:
            masked_key = self._mask_api_key(self._decrypt_api_key(encrypted_key))

        return AIProviderPublic(
            provider_name=row["provider_name"],
            base_url=row.get("base_url"),
            model_name=row["model_name"],
            is_active=row.get("is_active", True),
            has_api_key=has_api_key,
            api_key_masked=masked_key,
        )

    def save_provider(self, user_id: str, config: AIProviderConfig) -> AIProviderPublic:
        encrypted_key = self._encrypt_api_key(config.api_key)
        payload = {
            "user_id": user_id,
            "provider_name": config.provider_name,
            "api_key_encrypted": encrypted_key,
            "base_url": config.base_url,
            "model_name": config.model_name,
            "is_active": config.is_active,
        }
        result = (
            self._table("ai_provider_configs")
            .upsert(payload, on_conflict="user_id,provider_name")
            .execute()
        )
        row = result.data[0] if result.data else payload
        return self._provider_public_from_row(row)

    def update_provider(
        self, user_id: str, provider_name: ProviderName, patch: AIProviderPatch
    ) -> AIProviderPublic:
        existing = self._get_provider_row(user_id, provider_name)
        if not existing:
            if not patch.api_key:
                raise ValueError("API key is required for a new provider")
            return self.save_provider(
                user_id,
                AIProviderConfig(
                    provider_name=provider_name,
                    api_key=patch.api_key,
                    base_url=patch.base_url,
                    model_name=patch.model_name,
                    is_active=patch.is_active,
                ),
            )

        encrypted_key = (
            self._encrypt_api_key(patch.api_key)
            if patch.api_key
            else existing.get("api_key_encrypted") or existing.get("api_key")
        )
        payload = {
            "user_id": user_id,
            "provider_name": provider_name,
            "api_key_encrypted": encrypted_key,
            "base_url": patch.base_url,
            "model_name": patch.model_name,
            "is_active": patch.is_active,
        }
        result = (
            self._table("ai_provider_configs")
            .upsert(payload, on_conflict="user_id,provider_name")
            .execute()
        )
        row = result.data[0] if result.data else payload
        return self._provider_public_from_row(row)

    def list_providers(self, user_id: str) -> list[AIProviderPublic]:
        result = (
            self._table("ai_provider_configs")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        return [self._provider_public_from_row(row) for row in result.data or []]

    def get_provider(self, user_id: str, provider_name: str) -> Optional[AIProviderPublic]:
        row = self._get_provider_row(user_id, provider_name)
        return self._provider_public_from_row(row) if row else None

    def get_provider_secret(self, user_id: str, provider_name: str) -> Optional[dict]:
        row = self._get_provider_row(user_id, provider_name)
        if not row or not row.get("is_active", True):
            return None
        encrypted_key = row.get("api_key_encrypted") or row.get("api_key")
        if not encrypted_key:
            return None
        return {
            **row,
            "api_key": self._decrypt_api_key(encrypted_key),
        }

    def delete_provider(self, user_id: str, provider_name: str) -> None:
        (
            self._table("ai_provider_configs")
            .delete()
            .eq("user_id", user_id)
            .eq("provider_name", provider_name)
            .execute()
        )

    def save_agent_config(
        self, user_id: str, config: AgentModelConfig
    ) -> AgentModelConfig:
        existing = self._get_agent_row(user_id, config.agent_name)
        next_protocol = (
            "request"
            if config.provider_name == "custom"
            else config.api_protocol or self._infer_api_protocol(config.provider_name)
        )
        existing_secret_can_be_reused = bool(existing) and all(
            [
                existing.get("provider_name") == config.provider_name,
                (existing.get("api_protocol") or self._infer_api_protocol(existing["provider_name"]))
                == next_protocol,
                (existing.get("base_url") or None) == (config.base_url or None),
            ]
        )
        if not config.api_key and existing and not existing_secret_can_be_reused:
            raise ValueError(
                "API Key is required when changing an agent provider, protocol, or Base URL"
            )
        encrypted_key = (
            self._encrypt_api_key(config.api_key)
            if config.api_key
            else (existing or {}).get("api_key_encrypted")
        )
        if not encrypted_key and not self.get_provider_secret(user_id, config.provider_name):
            raise ValueError(f"Provider {config.provider_name} is not configured")

        payload = {
            "user_id": user_id,
            "agent_name": config.agent_name,
            "provider_name": config.provider_name,
            "api_protocol": next_protocol,
            "api_key_encrypted": encrypted_key,
            "base_url": config.base_url,
            "model_name": config.model_name,
        }
        rpc_row = self._upsert_agent_config_with_rpc(payload)
        if rpc_row is not None:
            return self._agent_config_from_row(rpc_row)

        result = (
            self._table("agent_model_configs")
            .upsert(payload, on_conflict="user_id,agent_name")
            .execute()
        )
        row = result.data[0] if result.data else payload
        return self._agent_config_from_row(row)

    def _upsert_agent_config_with_rpc(self, payload: dict) -> dict | None:
        try:
            result = self._rpc(
                "upsert_agent_model_config",
                {
                    "p_user_id": payload["user_id"],
                    "p_agent_name": payload["agent_name"],
                    "p_provider_name": payload["provider_name"],
                    "p_api_protocol": payload["api_protocol"],
                    "p_api_key_encrypted": payload.get("api_key_encrypted"),
                    "p_base_url": payload.get("base_url"),
                    "p_model_name": payload["model_name"],
                },
            )
        except Exception as exc:
            error_text = str(exc)
            if "upsert_agent_model_config" in error_text and (
                "Could not find" in error_text
                or "schema cache" in error_text
                or "does not exist" in error_text
                or "PGRST202" in error_text
            ):
                return None
            raise

        if result is None:
            return None

        data = getattr(result, "data", None)
        if isinstance(data, list):
            return data[0] if data else payload
        if isinstance(data, dict):
            return data
        return payload

    def save_all_agent_configs(
        self, user_id: str, configs: list[AgentModelConfig]
    ) -> list[AgentModelConfig]:
        return [self.save_agent_config(user_id, config) for config in configs]

    def get_agent_config(
        self, user_id: str, agent_name: str
    ) -> Optional[AgentModelConfig]:
        row = self._get_agent_row(user_id, agent_name)
        return self._agent_config_from_row(row) if row else None

    def get_all_agent_configs(self, user_id: str) -> dict[str, AgentModelConfig]:
        result = (
            self._table("agent_model_configs")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        return {
            row["agent_name"]: self._agent_config_from_row(row)
            for row in result.data or []
        }

    def resolve_agent_config(self, user_id: str, agent_name: str) -> ResolvedAgentConfig:
        row = self._get_agent_row(user_id, agent_name)
        if not row:
            raise ValueError(f"Agent {agent_name} has not been configured")

        encrypted_key = row.get("api_key_encrypted")
        if encrypted_key:
            return ResolvedAgentConfig(
                agent_name=row["agent_name"],
                provider_name=row["provider_name"],
                api_key=self._decrypt_api_key(encrypted_key),
                base_url=row.get("base_url"),
                model_name=row["model_name"],
                api_type=self._api_protocol_to_api_type(
                    self._infer_api_protocol(row["provider_name"])
                    if row["provider_name"] == "custom"
                    else row.get("api_protocol")
                    or self._infer_api_protocol(row["provider_name"])
                ),
            )

        agent_config = self._agent_config_from_row(row)
        provider = self.get_provider_secret(user_id, agent_config.provider_name)
        if not provider:
            raise ValueError(
                f"Provider {agent_config.provider_name} is missing or inactive"
            )

        return ResolvedAgentConfig(
            agent_name=agent_config.agent_name,
            provider_name=agent_config.provider_name,
            api_key=provider["api_key"],
            base_url=provider.get("base_url"),
            model_name=agent_config.model_name or provider["model_name"],
            api_type=self._api_protocol_to_api_type(
                self._infer_api_protocol(agent_config.provider_name)
                if agent_config.provider_name == "custom"
                else agent_config.api_protocol
                or self._infer_api_protocol(agent_config.provider_name)
            ),
        )

    def _agent_config_from_row(self, row: dict) -> AgentModelConfig:
        encrypted_key = row.get("api_key_encrypted")
        return AgentModelConfig(
            agent_name=row["agent_name"],
            provider_name=row["provider_name"],
            api_protocol=(
                self._infer_api_protocol(row["provider_name"])
                if row["provider_name"] == "custom"
                else row.get("api_protocol")
                or self._infer_api_protocol(row["provider_name"])
            ),
            base_url=row.get("base_url"),
            model_name=row["model_name"],
            has_api_key=bool(encrypted_key),
            api_key_masked=(
                self._mask_api_key(self._decrypt_api_key(encrypted_key))
                if encrypted_key
                else None
            ),
        )

    def _infer_api_protocol(self, provider_name: str) -> APIProtocol:
        if provider_name == "claude":
            return "anthropic"
        if provider_name == "qwen":
            return "qwen"
        if provider_name == "custom":
            return "request"
        return "openai"

    def _api_protocol_to_api_type(
        self, api_protocol: str
    ) -> Literal["openai", "claude", "qwen", "request"]:
        if api_protocol == "anthropic":
            return "claude"
        if api_protocol == "qwen":
            return "qwen"
        if api_protocol == "request":
            return "request"
        return "openai"

    def _infer_api_type(
        self, provider_name: str
    ) -> Literal["openai", "claude", "qwen", "request"]:
        if provider_name == "claude":
            return "claude"
        if provider_name == "qwen":
            return "qwen"
        if provider_name == "custom":
            return "request"
        return "openai"

    def _get_provider_row(self, user_id: str, provider_name: str) -> Optional[dict]:
        result = (
            self._table("ai_provider_configs")
            .select("*")
            .eq("user_id", user_id)
            .eq("provider_name", provider_name)
            .execute()
        )
        return result.data[0] if result.data else None

    def _get_agent_row(self, user_id: str, agent_name: str) -> Optional[dict]:
        result = (
            self._table("agent_model_configs")
            .select("*")
            .eq("user_id", user_id)
            .eq("agent_name", agent_name)
            .execute()
        )
        return result.data[0] if result.data else None
