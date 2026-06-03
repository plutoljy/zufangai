"""
Rental contract analysis FastAPI application.
Provides upload, direct SSE analysis, queued analysis, and report retrieval.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from typing import Any, AsyncGenerator, Literal, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.agent_chat import generate_agent_chat_reply
from analysis_queue import (
    DONE_SENTINEL,
    cleanup_finished_tasks,
    clear_task,
    create_task,
    get_events,
    get_task,
    list_task_ids_for_contract,
    list_task_ids_for_owner,
    push_event,
)
from analysis_queue_worker import run_queue_worker
from analysis_runtime import run_contract_analysis_events
from config import settings
from database.supabase_client import supabase_client
from models.user_preferences import PreferenceUpdate, UserPreferences
from utils.console_runtime import configure_console_runtime
from utils.document_parser import FileTypeDetector, get_document_parser
from utils.privacy_redactor import redact_sensitive_contract_info
from api.ai_providers import router as ai_providers_router
from api.roommate_api import router as roommate_router

configure_console_runtime()

app = FastAPI(title="租房避坑局 API", version="1.0.0")

allowed_origins = sorted(
    {
        settings.frontend_url,
        "http://0.0.0.0:3000",
        "http://0.0.0.0:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    }
)

local_network_origin_regex = (
    r"^https?://("
    r"localhost|"
    r"127\.0\.0\.1|"
    r"10(?:\.\d{1,3}){3}|"
    r"192\.168(?:\.\d{1,3}){2}|"
    r"172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2}"
    r")(?::\d+)?$"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=local_network_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

contracts_store: dict[str, dict[str, Any]] = {}
analysis_results: dict[str, dict[str, Any]] = {}


class UploadResponse(BaseModel):
    contract_id: str
    status: str


class QueueResponse(BaseModel):
    task_id: str
    contract_id: str
    status: str
    queue_position: int
    stream_token: str


STREAM_TOKEN_TTL_SECONDS = 300
TASK_RETENTION_SECONDS = 1800
RUNTIME_STATE_TTL_SECONDS = 3600
BURN_AFTER_READING_GRACE_SECONDS = 300
CLEANUP_LOOP_INTERVAL_SECONDS = 60


class BurnAfterReadingCleanupRequest(BaseModel):
    contract_id: Optional[str] = None


class AgentChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AgentChatRequest(BaseModel):
    question: str
    messages: list[AgentChatMessage] = Field(default_factory=list)


class AgentChatResponse(BaseModel):
    contract_id: str
    agent: str
    reply: str


def _urlsafe_b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _urlsafe_b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _create_stream_token(task_id: str, owner_id: Optional[str]) -> str:
    issued_at = int(time.time())
    payload = {
        "scope": "analysis_stream",
        "task_id": task_id,
        "owner_id": owner_id,
        "iat": issued_at,
        "exp": issued_at + STREAM_TOKEN_TTL_SECONDS,
    }
    payload_bytes = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    signature = hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).digest()
    return f"{_urlsafe_b64encode(payload_bytes)}.{_urlsafe_b64encode(signature)}"


def _validate_stream_token(task_id: str, stream_token: Optional[str]) -> dict[str, Any]:
    if not stream_token:
        raise HTTPException(status_code=401, detail="Stream token required")

    try:
        payload_part, signature_part = stream_token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid stream token") from exc

    try:
        payload_bytes = _urlsafe_b64decode(payload_part)
        signature = _urlsafe_b64decode(signature_part)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid stream token") from exc

    expected_signature = hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid stream token")

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid stream token") from exc

    if payload.get("scope") != "analysis_stream" or payload.get("task_id") != task_id:
        raise HTTPException(status_code=401, detail="Invalid stream token")
    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=401, detail="Stream token expired")

    return payload


async def _require_current_user_id(
    request: Request, allow_anonymous: bool = False
) -> Optional[str]:
    token = _extract_bearer_token(request)
    if not token:
        if allow_anonymous:
            return None
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = supabase_client.get_user_id_from_access_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")

    return user_id


def _extract_bearer_token(request: Request) -> Optional[str]:
    authorization = request.headers.get("authorization")
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return token


app.state.require_current_user_id = _require_current_user_id
app.include_router(ai_providers_router)
app.include_router(roommate_router)


def _ensure_user_scope(path_user_id: str, current_user_id: Optional[str]) -> None:
    if current_user_id != path_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")


async def _ensure_contract_report_access(
    request: Request, contract_id: str
) -> Optional[str]:
    contract = contracts_store.get(contract_id, {})
    owner_id = contract.get("owner_id")
    if not owner_id:
        return None

    current_user_id = await _require_current_user_id(request)
    if current_user_id != owner_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return current_user_id


async def _ensure_task_access(request: Request, task_id: str) -> dict[str, Any]:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    owner_id = task.get("owner_id")
    if owner_id:
        current_user_id = await _require_current_user_id(request)
        if current_user_id != owner_id:
            raise HTTPException(status_code=403, detail="Forbidden")

    return task


def _serialize_task(task: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in task.items() if key != "owner_id"}


def _build_task_response(task: dict[str, Any]) -> dict[str, Any]:
    response = _serialize_task(task)
    response["stream_token"] = _create_stream_token(
        task["task_id"], task.get("owner_id")
    )
    return response


def _now_ts(now: float | None = None) -> float:
    return float(now if now is not None else time.time())


def _store_analysis_result(
    contract_id: str,
    state: dict[str, Any],
    *,
    now: float | None = None,
) -> None:
    current_time = _now_ts(now)
    contract = contracts_store.get(contract_id, {})
    risk_items = state.get("risk_items", [])
    source_counts: dict[str, int] = {}
    for item in risk_items:
        source = item.get("source", "llm")
        source_counts[source] = source_counts.get(source, 0) + 1
    print(
        "[store_analysis_result] "
        f"contract_id={contract_id} risk_items={len(risk_items)} "
        f"source_counts={source_counts}"
    )
    analysis_results[contract_id] = {
        **state,
        "_meta": {
            "owner_id": contract.get("owner_id"),
            "completed_at": current_time,
            "last_accessed_at": current_time,
            "burn_after_reading": contract.get("burn_after_reading", False),
        },
    }
    if contract:
        contract["status"] = "completed"
        contract["completed_at"] = current_time
        contract["last_accessed_at"] = current_time


def _touch_contract_access(contract_id: str, *, now: float | None = None) -> None:
    contract = contracts_store.get(contract_id)
    if contract is not None:
        contract["last_accessed_at"] = _now_ts(now)


def _touch_report_access(contract_id: str, *, now: float | None = None) -> None:
    result = analysis_results.get(contract_id)
    if result is not None:
        meta = result.setdefault("_meta", {})
        meta["last_accessed_at"] = _now_ts(now)


def _build_report_payload(contract_id: str) -> dict[str, Any]:
    result = analysis_results[contract_id]
    return {
        "contract_id": contract_id,
        "contract_text": contracts_store.get(contract_id, {}).get("text", ""),
        "entities": result.get("entities", {}),
        "risk_items": result.get("risk_items", []),
        "legal_references": result.get("legal_references", []),
        "case_references": result.get("case_references", []),
        "suggestions": result.get("suggestions", []),
        "negotiation_tips": result.get("negotiation_tips", []),
        "calculations": result.get("calculations", {}),
        "report_markdown": result.get("report", {}).get("report_markdown", ""),
        "summary": result.get("report", {}).get("summary", {}),
        "is_template": result.get("is_template", False),
        "privacy_redacted": contracts_store.get(contract_id, {}).get(
            "privacy_redacted", False
        ),
        "redaction_count": contracts_store.get(contract_id, {}).get(
            "redaction_count", 0
        ),
    }


def _build_history_summary(contract_id: str) -> dict[str, Any]:
    contract = contracts_store.get(contract_id, {})
    result = analysis_results.get(contract_id, {})
    risk_items = result.get("risk_items", [])
    risk_summary = {"high": 0, "medium": 0, "low": 0, "total": len(risk_items)}
    for item in risk_items:
        level = item.get("risk_level")
        if level in risk_summary:
            risk_summary[level] += 1

    meta = result.get("_meta", {}) if isinstance(result, dict) else {}
    return {
        "contract_id": contract_id,
        "filename": contract.get("filename") or "未命名合同",
        "location": contract.get("location"),
        "status": contract.get("status", "completed"),
        "created_at": contract.get("created_at"),
        "completed_at": meta.get("completed_at") or contract.get("completed_at"),
        "last_accessed_at": max(
            float(contract.get("last_accessed_at", 0) or 0),
            float(meta.get("last_accessed_at", 0) or 0),
        ),
        "burn_after_reading": bool(contract.get("burn_after_reading")),
        "risk_summary": risk_summary,
    }


def _purge_contract_runtime(contract_id: str) -> bool:
    running_found = False

    for task_id in list_task_ids_for_contract(contract_id):
        task = get_task(task_id)
        if not task:
            continue
        if task.get("status") == "running":
            running_found = True
        else:
            clear_task(task_id)

    if running_found:
        contract = contracts_store.get(contract_id)
        if contract is not None:
            contract["purge_requested"] = True
        result = analysis_results.get(contract_id)
        if result is not None:
            result.setdefault("_meta", {})["purge_requested"] = True
        return False

    contracts_store.pop(contract_id, None)
    analysis_results.pop(contract_id, None)
    return True


def cleanup_runtime_state(*, now: float | None = None) -> dict[str, int]:
    current_time = _now_ts(now)
    tasks_removed = cleanup_finished_tasks(
        TASK_RETENTION_SECONDS,
        now=current_time,
    )
    reports_removed = 0
    contracts_removed = 0

    candidate_ids = set(contracts_store.keys()) | set(analysis_results.keys())
    for contract_id in list(candidate_ids):
        contract = contracts_store.get(contract_id)
        result = analysis_results.get(contract_id)
        result_meta = result.get("_meta", {}) if isinstance(result, dict) else {}

        if contract and contract.get("purge_requested"):
            if _purge_contract_runtime(contract_id):
                contracts_removed += 1
                if result is not None:
                    reports_removed += 1
            continue

        last_accessed_at = max(
            float((contract or {}).get("last_accessed_at", 0) or 0),
            float(result_meta.get("last_accessed_at", 0) or 0),
        )

        should_purge = False
        if contract is not None or result is not None:
            should_purge = (
                current_time - float(last_accessed_at)
                >= RUNTIME_STATE_TTL_SECONDS
            )

        if should_purge and _purge_contract_runtime(contract_id):
            if contract is not None:
                contracts_removed += 1
            if result is not None:
                reports_removed += 1

    return {
        "tasks_removed": len(tasks_removed),
        "contracts_removed": contracts_removed,
        "reports_removed": reports_removed,
    }


async def _post_task_cleanup(task: dict[str, Any]) -> None:
    contract_id = task["contract_id"]
    contract = contracts_store.get(contract_id)
    if contract and contract.get("purge_requested"):
        _purge_contract_runtime(contract_id)


def _load_contract_for_worker(contract_id: str) -> dict[str, Any] | None:
    return contracts_store.get(contract_id)


def _store_result_from_worker(contract_id: str, state: dict[str, Any]) -> None:
    _store_analysis_result(contract_id, state)


async def _cleanup_runtime_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            cleanup_runtime_state()
            await asyncio.wait_for(
                stop_event.wait(), timeout=CLEANUP_LOOP_INTERVAL_SECONDS
            )
        except asyncio.TimeoutError:
            continue


@app.on_event("startup")
async def startup_runtime_workers() -> None:
    if getattr(app.state, "background_runtime_enabled", True) is False:
        return

    if getattr(app.state, "runtime_stop_event", None) is not None:
        return

    stop_event = asyncio.Event()
    app.state.runtime_stop_event = stop_event
    app.state.queue_worker_task = asyncio.create_task(
        run_queue_worker(
            stop_event=stop_event,
            load_contract=_load_contract_for_worker,
            store_result=_store_result_from_worker,
            post_task_cleanup=_post_task_cleanup,
        )
    )
    app.state.runtime_cleanup_task = asyncio.create_task(
        _cleanup_runtime_loop(stop_event)
    )


@app.on_event("shutdown")
async def shutdown_runtime_workers() -> None:
    stop_event = getattr(app.state, "runtime_stop_event", None)
    if stop_event is None:
        return

    stop_event.set()
    for attr in ("queue_worker_task", "runtime_cleanup_task"):
        task = getattr(app.state, attr, None)
        if task is not None:
            await task

    app.state.runtime_stop_event = None
    app.state.queue_worker_task = None
    app.state.runtime_cleanup_task = None


@app.get("/")
async def root():
    return {"status": "ok", "message": "租房避坑局 API"}


@app.post("/api/contracts/upload", response_model=UploadResponse)
async def upload_contract(
    request: Request,
    file: UploadFile = File(...),
    location: Optional[str] = "beijing",
    privacy_mode: bool = Form(False),
    burn_after_reading: bool = Form(False),
    user_id: Optional[str] = Form(None),
):
    try:
        contract_id = str(uuid.uuid4())
        content = await file.read()
        access_token = _extract_bearer_token(request)
        authenticated_user_id = await _require_current_user_id(
            request, allow_anonymous=True
        )

        try:
            file_type = FileTypeDetector.detect(content, file.filename or "")
            FileTypeDetector.validate_size(len(content))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            parser = get_document_parser()
            extracted_text = parser.parse(content, file_type)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"文件解析失败: {exc}") from exc

        redaction_count = 0
        if privacy_mode:
            redaction_result = redact_sensitive_contract_info(extracted_text)
            extracted_text = redaction_result.text
            redaction_count = redaction_result.replacement_count

        created_at = _now_ts()

        contracts_store[contract_id] = {
            "id": contract_id,
            "filename": file.filename or "contract.bin",
            "file_type": file_type,
            "file_size": len(content),
            "text": extracted_text,
            "location": location,
            "privacy_redacted": privacy_mode,
            "redaction_count": redaction_count,
            "burn_after_reading": burn_after_reading,
            # Do not trust the form field for identity; bind ownership to the token instead.
            "user_id": authenticated_user_id,
            "owner_id": authenticated_user_id,
            "auth_access_token": access_token if authenticated_user_id else None,
            "submitted_user_id": user_id,
            "status": "uploaded",
            "created_at": created_at,
            "last_accessed_at": created_at,
            "completed_at": None,
            "purge_requested": False,
        }

        return UploadResponse(contract_id=contract_id, status="uploaded")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _format_sse(event_type: str, data: dict[str, Any]) -> str:
    return f"data: {json.dumps({'type': event_type, **data}, ensure_ascii=False)}\n\n"


@app.get("/api/contracts/{contract_id}/analyze")
async def analyze_contract(contract_id: str):
    if contract_id not in contracts_store:
        raise HTTPException(status_code=404, detail="合同不存在")

    contract = contracts_store[contract_id]
    _touch_contract_access(contract_id)

    async def event_generator():
        try:
            async for event in run_contract_analysis_events(
                contract_id=contract_id,
                contract_text=contract["text"],
                location=contract["location"],
                user_id=contract.get("user_id"),
                access_token=contract.get("auth_access_token"),
            ):
                event_type = event.get("event", "message")
                event_data = event.get("data", {})
                if event_type == "analysis_complete":
                    state = event_data.get("state")
                    if state is not None:
                        _store_analysis_result(contract_id, state)
                    yield _format_sse("analysis_complete", {"contract_id": contract_id})
                else:
                    yield _format_sse(event_type, event_data)
        except Exception as exc:
            yield _format_sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/contracts/{contract_id}/analyze/queue", response_model=QueueResponse)
async def queue_contract_analysis(contract_id: str, request: Request):
    if contract_id not in contracts_store:
        raise HTTPException(status_code=404, detail="合同不存在")

    contract = contracts_store[contract_id]
    _touch_contract_access(contract_id)
    owner_id = contract.get("owner_id")
    if owner_id:
        current_user_id = await _require_current_user_id(request)
        if current_user_id != owner_id:
            raise HTTPException(status_code=403, detail="Forbidden")

    task = create_task(
        contract_id,
        owner_id=owner_id,
        burn_after_reading=contract.get("burn_after_reading", False),
    )

    return QueueResponse(
        **_build_task_response(task),
    )


@app.get("/api/analysis/tasks/{task_id}")
async def get_analysis_task(task_id: str, request: Request):
    task = await _ensure_task_access(request, task_id)
    _touch_contract_access(task["contract_id"])
    return _build_task_response(task)


@app.get("/api/analysis/tasks/{task_id}/stream")
async def stream_analysis_task(task_id: str, stream_token: Optional[str] = None):
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    _validate_stream_token(task_id, stream_token)
    _touch_contract_access(task["contract_id"])

    async def event_generator() -> AsyncGenerator[str, None]:
        offset = 0
        idle_polls = 0
        poll_interval = 0.5

        while True:
            events = get_events(task_id, offset)

            if events:
                idle_polls = 0
                for event in events:
                    event_type = event.get("event", "message")
                    if event_type == DONE_SENTINEL:
                        return
                    yield _format_sse(event_type, event.get("data", {}))
                offset += len(events)
            else:
                idle_polls += 1
                current_task = get_task(task_id)
                if current_task and current_task.get("status") in {"completed", "failed"}:
                    push_event(task_id, DONE_SENTINEL, {})
                    return
                if idle_polls % 10 == 0:
                    yield _format_sse(
                        "heartbeat",
                        {
                            "message": "后台任务仍在运行，继续等待分析结果...",
                            "task_id": task_id,
                            "status": current_task.get("status", "running")
                            if current_task
                            else "running",
                        },
                    )
                await asyncio.sleep(poll_interval)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/contracts/{contract_id}/report")
async def get_report(contract_id: str, request: Request):
    if contract_id not in analysis_results:
        raise HTTPException(status_code=404, detail="报告不存在")

    await _ensure_contract_report_access(request, contract_id)
    _touch_contract_access(contract_id)
    _touch_report_access(contract_id)
    result = analysis_results[contract_id]
    risk_items = result.get("risk_items", [])
    source_counts: dict[str, int] = {}
    for item in risk_items:
        source = item.get("source", "llm")
        source_counts[source] = source_counts.get(source, 0) + 1
    print(
        "[get_report] "
        f"contract_id={contract_id} risk_items={len(risk_items)} "
        f"source_counts={source_counts}"
    )

    return _build_report_payload(contract_id)


@app.get("/api/contracts/history")
async def list_contract_history(request: Request):
    current_user_id = await _require_current_user_id(request)

    summaries: list[dict[str, Any]] = []
    for contract_id, contract in contracts_store.items():
        if contract.get("owner_id") != current_user_id:
            continue
        if contract_id not in analysis_results:
            continue

        _touch_contract_access(contract_id)
        _touch_report_access(contract_id)
        summaries.append(_build_history_summary(contract_id))

    summaries.sort(
        key=lambda item: (
            float(item.get("completed_at") or 0),
            float(item.get("created_at") or 0),
        ),
        reverse=True,
    )
    return {"contracts": summaries}


@app.post(
    "/api/contracts/{contract_id}/agents/{agent_key}/chat",
    response_model=AgentChatResponse,
)
async def chat_with_agent(
    contract_id: str,
    agent_key: str,
    payload: AgentChatRequest,
    request: Request,
):
    if agent_key not in {"owl", "dog", "beaver"}:
        raise HTTPException(status_code=400, detail="Unsupported agent")
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")
    if contract_id not in analysis_results:
        raise HTTPException(status_code=404, detail="Report not found")

    await _ensure_contract_report_access(request, contract_id)
    _touch_contract_access(contract_id)
    _touch_report_access(contract_id)

    report_payload = _build_report_payload(contract_id)
    contract = contracts_store.get(contract_id, {})
    reply = generate_agent_chat_reply(
        agent_key=agent_key,
        contract_text=report_payload.get("contract_text", ""),
        report=report_payload,
        messages=[message.model_dump() for message in payload.messages],
        question=payload.question.strip(),
        user_id=contract.get("user_id"),
        access_token=contract.get("auth_access_token"),
    )

    return AgentChatResponse(
        contract_id=contract_id,
        agent=agent_key,
        reply=reply,
    )


@app.post("/api/contracts/burn-after-reading/cleanup")
async def cleanup_burn_after_reading(
    payload: BurnAfterReadingCleanupRequest,
    request: Request,
):
    current_user_id = await _require_current_user_id(request)

    if payload.contract_id:
        target_ids = [payload.contract_id]
    else:
        target_ids = [
            contract_id
            for contract_id, contract in contracts_store.items()
            if contract.get("owner_id") == current_user_id
            and contract.get("burn_after_reading")
        ]

    deleted_contract_ids: list[str] = []
    scheduled_contract_ids: list[str] = []

    for contract_id in target_ids:
        contract = contracts_store.get(contract_id)
        if contract and contract.get("owner_id") != current_user_id:
            raise HTTPException(status_code=403, detail="Forbidden")

        purged = _purge_contract_runtime(contract_id)
        if purged:
            deleted_contract_ids.append(contract_id)
        elif contract_id in contracts_store:
            contracts_store[contract_id]["purge_requested"] = True
            scheduled_contract_ids.append(contract_id)

    return {
        "deleted_contract_ids": deleted_contract_ids,
        "scheduled_contract_ids": scheduled_contract_ids,
    }


# ===================================
# 用户偏好管理 API
# ===================================


@app.get("/api/preferences/{user_id}", response_model=UserPreferences)
async def get_user_preferences(user_id: str, request: Request):
    """获取用户偏好"""
    current_user_id = await _require_current_user_id(request)
    _ensure_user_scope(user_id, current_user_id)

    preferences = supabase_client.get_user_preferences(user_id)

    if not preferences:
        return UserPreferences(user_id=user_id)

    return preferences


@app.post("/api/preferences/{user_id}", response_model=UserPreferences)
async def create_or_update_preferences(
    user_id: str, update: PreferenceUpdate, request: Request
):
    """创建或更新用户偏好"""
    current_user_id = await _require_current_user_id(request)
    _ensure_user_scope(user_id, current_user_id)

    existing = supabase_client.get_user_preferences(user_id)

    if existing:
        if update.risk_tolerance is not None:
            existing.risk_tolerance = update.risk_tolerance
        if update.focused_risks is not None:
            existing.focused_risks = update.focused_risks
        if update.user_role is not None:
            existing.user_role = update.user_role
        if update.experience_level is not None:
            existing.experience_level = update.experience_level
        if update.region is not None:
            existing.region = update.region
        if update.custom_thresholds is not None:
            existing.custom_thresholds = update.custom_thresholds

        preferences = existing
    else:
        preferences = UserPreferences(user_id=user_id)
        if update.risk_tolerance is not None:
            preferences.risk_tolerance = update.risk_tolerance
        if update.focused_risks is not None:
            preferences.focused_risks = update.focused_risks
        if update.user_role is not None:
            preferences.user_role = update.user_role
        if update.experience_level is not None:
            preferences.experience_level = update.experience_level
        if update.region is not None:
            preferences.region = update.region
        if update.custom_thresholds is not None:
            preferences.custom_thresholds = update.custom_thresholds

    success = supabase_client.save_user_preferences(preferences)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save user preferences")

    return preferences


@app.delete("/api/preferences/{user_id}")
async def delete_user_preferences(user_id: str, request: Request):
    """删除用户偏好"""
    current_user_id = await _require_current_user_id(request)
    _ensure_user_scope(user_id, current_user_id)

    success = supabase_client.delete_user_preferences(user_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete user preferences")

    return {"message": "User preferences deleted successfully"}


@app.post("/api/preferences/{user_id}/reset", response_model=UserPreferences)
async def reset_user_preferences(user_id: str, request: Request):
    """重置用户偏好为默认值"""
    current_user_id = await _require_current_user_id(request)
    _ensure_user_scope(user_id, current_user_id)

    default_preferences = UserPreferences(user_id=user_id)

    success = supabase_client.save_user_preferences(default_preferences)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to reset user preferences")

    return default_preferences


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
