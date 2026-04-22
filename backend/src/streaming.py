"""
Helpers for streaming long-running agent execution over SSE-friendly events.
"""

from __future__ import annotations

import asyncio
import time
import weakref
from typing import Any, AsyncGenerator, Callable


_STEP_EXECUTION_SEMAPHORES: weakref.WeakKeyDictionary[
    asyncio.AbstractEventLoop, asyncio.Semaphore
] = weakref.WeakKeyDictionary()


def _get_step_execution_semaphore() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    semaphore = _STEP_EXECUTION_SEMAPHORES.get(loop)
    if semaphore is None:
        semaphore = asyncio.Semaphore(1)
        _STEP_EXECUTION_SEMAPHORES[loop] = semaphore
    return semaphore


def classify_agent_error(exc: Exception) -> str:
    name = exc.__class__.__name__.lower()
    message = str(exc).lower()

    if "timeout" in name or "timeout" in message:
        return "timeout"
    if "connect" in name or "connection" in message:
        return "connection_error"
    if "auth" in name or "permission" in message or "unauthorized" in message:
        return "auth_error"
    if "json" in name or "payload" in message or "parse" in message:
        return "invalid_payload"
    return "execution_error"


def summarize_agent_result(agent: str, state: dict[str, Any]) -> dict[str, Any]:
    if agent == "owl":
        return {
            "entity_count": len(state.get("entities", {})),
            "risk_count": len(state.get("risk_items", [])),
        }
    if agent == "dog":
        return {
            "legal_docs": len(state.get("legal_references", [])),
            "cases": len(state.get("case_references", [])),
        }
    if agent == "beaver":
        metadata = state.get("calculations", {}).get("analysis_metadata", {})
        return {
            "compliant": state.get("calculations", {})
            .get("deposit_check", {})
            .get("compliant", False),
            "mode": metadata.get("mode"),
            "llm_attempted": metadata.get("llm_attempted"),
            "llm_success": metadata.get("llm_success"),
            "llm_error": metadata.get("llm_error"),
        }
    if agent == "cat":
        report = state.get("report", {})
        return {
            "total_risks": report.get("summary", {}).get("total_risks", 0),
            "report_length": len(report.get("report_markdown", "")),
        }
    return {}


async def _run_step_in_order(
    func: Callable[[dict[str, Any]], dict[str, Any]],
    state: dict[str, Any],
    started_event: asyncio.Event,
) -> dict[str, Any]:
    semaphore = _get_step_execution_semaphore()
    async with semaphore:
        started_event.set()
        return await asyncio.to_thread(func, state)


async def stream_agent_step(
    *,
    agent: str,
    step: str,
    message: str,
    state: dict[str, Any],
    func: Callable[[dict[str, Any]], dict[str, Any]],
    timeout_s: float | None,
    heartbeat_interval_s: float = 8.0,
    fallback_timeout_s: float | None = None,
    fallback_func: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    start = time.perf_counter()
    yield {
      "event": "agent_started",
      "data": {
        "agent": agent,
        "step": step,
        "message": message,
      },
    }

    started_event = asyncio.Event()
    task = asyncio.create_task(_run_step_in_order(func, state, started_event))

    while True:
        elapsed = time.perf_counter() - start
        soft_timeout_exceeded = timeout_s is not None and elapsed >= timeout_s
        fallback_timeout_exceeded = (
            fallback_timeout_s is not None and elapsed >= fallback_timeout_s
        )
        if (
            fallback_timeout_exceeded
            and fallback_func is not None
            and started_event.is_set()
        ):
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            result = fallback_func(state)
            yield {
              "event": "agent_completed",
              "data": {
                "agent": agent,
                "step": step,
                "elapsed_ms": elapsed_ms,
                "used_fallback": True,
                **summarize_agent_result(agent, result),
              },
              "_result": result,
            }
            return

        done, _ = await asyncio.wait({task}, timeout=heartbeat_interval_s)
        if task in done:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            exc = task.exception()
            if exc is not None:
                error_code = classify_agent_error(exc)
                yield {
                  "event": "agent_failed",
                  "data": {
                    "agent": agent,
                    "step": step,
                    "error_code": error_code,
                    "message": str(exc),
                    "elapsed_ms": elapsed_ms,
                  },
                  "_failed": True,
                }
                return

            result = task.result()
            yield {
              "event": "agent_completed",
              "data": {
                "agent": agent,
                "step": step,
                "elapsed_ms": elapsed_ms,
                **summarize_agent_result(agent, result),
              },
              "_result": result,
            }
            return

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        progress_message = message
        if not started_event.is_set():
            progress_message = f"{message}（等待前序分析任务释放执行槽位）"
        elif soft_timeout_exceeded:
            progress_message = f"{message}（耗时较长，继续等待结果）"

        yield {
          "event": "agent_progress",
          "data": {
            "agent": agent,
            "step": step,
            "message": progress_message,
            "elapsed_ms": elapsed_ms,
            "soft_timeout_exceeded": soft_timeout_exceeded,
          },
        }
        yield {
          "event": "heartbeat",
          "data": {
            "agent": agent,
            "step": step,
            "elapsed_ms": elapsed_ms,
            "soft_timeout_exceeded": soft_timeout_exceeded,
          },
        }
