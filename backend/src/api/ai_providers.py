"""API endpoints for user AI provider and agent model settings."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ai_provider_manager import (
    AIProviderConfig,
    AIProviderManager,
    AIProviderPatch,
    AIProviderPublic,
    AgentModelConfig,
)
from utils.dynamic_llm_client import DynamicLLMClient

router = APIRouter(prefix="/api/ai-providers", tags=["AI Providers"])
AGENT_NAMES = ("owl", "dog", "beaver", "cat")


def _extract_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization")
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def get_provider_manager(request: Request) -> AIProviderManager:
    return AIProviderManager(access_token=_extract_bearer_token(request))


def _raise_storage_error(exc: Exception) -> None:
    raise HTTPException(
        status_code=500,
        detail=f"AI settings storage failed: {exc}",
    ) from exc


async def require_user_id(request: Request) -> str:
    auth_dependency = getattr(request.app.state, "require_current_user_id", None)
    if auth_dependency is None:
        raise HTTPException(status_code=500, detail="Auth dependency is not configured")
    user_id = await auth_dependency(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id


@router.get("/providers", response_model=list[AIProviderPublic])
async def list_providers(
    user_id: str = Depends(require_user_id),
    manager: AIProviderManager = Depends(get_provider_manager),
):
    try:
        return manager.list_providers(user_id)
    except Exception as exc:
        _raise_storage_error(exc)


@router.post("/providers", response_model=AIProviderPublic)
async def save_provider(
    config: AIProviderConfig,
    user_id: str = Depends(require_user_id),
    manager: AIProviderManager = Depends(get_provider_manager),
):
    try:
        return manager.save_provider(user_id, config)
    except Exception as exc:
        _raise_storage_error(exc)


@router.put("/providers/{provider_name}", response_model=AIProviderPublic)
async def update_provider(
    provider_name: str,
    patch: AIProviderPatch,
    user_id: str = Depends(require_user_id),
    manager: AIProviderManager = Depends(get_provider_manager),
):
    try:
        return manager.update_provider(user_id, provider_name.lower(), patch)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _raise_storage_error(exc)


@router.delete("/providers/{provider_name}")
async def delete_provider(
    provider_name: str,
    user_id: str = Depends(require_user_id),
    manager: AIProviderManager = Depends(get_provider_manager),
):
    try:
        manager.delete_provider(user_id, provider_name.lower())
        return {"success": True}
    except Exception as exc:
        _raise_storage_error(exc)


@router.get("/agents/config", response_model=dict[str, AgentModelConfig])
async def get_agent_configs(
    user_id: str = Depends(require_user_id),
    manager: AIProviderManager = Depends(get_provider_manager),
):
    try:
        return manager.get_all_agent_configs(user_id)
    except Exception as exc:
        _raise_storage_error(exc)


@router.post("/agents/config", response_model=AgentModelConfig)
async def save_agent_config(
    config: AgentModelConfig,
    user_id: str = Depends(require_user_id),
    manager: AIProviderManager = Depends(get_provider_manager),
):
    try:
        return manager.save_agent_config(user_id, config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _raise_storage_error(exc)


@router.post("/agents/config/batch", response_model=list[AgentModelConfig])
async def save_agent_configs_batch(
    configs: list[AgentModelConfig],
    user_id: str = Depends(require_user_id),
    manager: AIProviderManager = Depends(get_provider_manager),
):
    try:
        return manager.save_all_agent_configs(user_id, configs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _raise_storage_error(exc)


@router.post("/providers/test")
async def test_provider_connection(
    config: AIProviderConfig,
    user_id: str = Depends(require_user_id),
):
    return await DynamicLLMClient().test_connection(config)


@router.post("/agents/diagnostics")
async def diagnose_agent_connections(
    user_id: str = Depends(require_user_id),
    manager: AIProviderManager = Depends(get_provider_manager),
):
    return await DynamicLLMClient(manager).diagnose_agent_connections(
        user_id, AGENT_NAMES
    )
