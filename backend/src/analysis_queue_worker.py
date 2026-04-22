"""
Background worker for queued contract analysis tasks.
"""

from __future__ import annotations

import asyncio
import inspect
import traceback
from collections.abc import Awaitable, Callable
from typing import Any

from analysis_queue import (
    DONE_SENTINEL,
    complete_task,
    push_event,
    start_next_task,
)
from analysis_runtime import run_contract_analysis_events

LoadContract = Callable[[str], dict[str, Any] | None]
StoreResult = Callable[[str, dict[str, Any]], None]
PostTaskCleanup = Callable[[dict[str, Any]], Awaitable[None] | None]


async def process_next_queued_task(
    *,
    load_contract: LoadContract,
    store_result: StoreResult,
    post_task_cleanup: PostTaskCleanup | None = None,
) -> bool:
    task = start_next_task()
    if task is None:
        return False

    task_id = task["task_id"]
    contract_id = task["contract_id"]
    contract = load_contract(contract_id)

    if contract is None:
        push_event(task_id, "error", {"message": "Contract data not found"})
        push_event(task_id, DONE_SENTINEL, {})
        task = complete_task(
            task_id,
            status="failed",
            error="Contract data not found",
        ) or task
        await _run_post_task_cleanup(post_task_cleanup, task)
        return True

    try:
        async for event in run_contract_analysis_events(
            contract_id=contract_id,
            contract_text=contract["text"],
            location=contract["location"],
            user_id=contract.get("user_id"),
        ):
            event_type = event.get("event", "message")
            event_data = event.get("data", {})

            if event_type == "analysis_complete":
                state = event_data.get("state")
                if state is not None:
                    store_result(contract_id, state)
                push_event(task_id, event_type, {"contract_id": contract_id})
                continue

            push_event(task_id, event_type, event_data)

        push_event(task_id, DONE_SENTINEL, {})
        task = complete_task(task_id, status="completed") or task
    except Exception as exc:
        traceback.print_exc()
        push_event(task_id, "error", {"message": str(exc)})
        push_event(task_id, DONE_SENTINEL, {})
        task = complete_task(task_id, status="failed", error=str(exc)) or task

    await _run_post_task_cleanup(post_task_cleanup, task)
    return True


async def run_queue_worker(
    *,
    stop_event: asyncio.Event,
    load_contract: LoadContract,
    store_result: StoreResult,
    post_task_cleanup: PostTaskCleanup | None = None,
    idle_poll_interval_s: float = 0.25,
) -> None:
    while not stop_event.is_set():
        processed = await process_next_queued_task(
            load_contract=load_contract,
            store_result=store_result,
            post_task_cleanup=post_task_cleanup,
        )
        if processed:
            continue

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=idle_poll_interval_s)
        except asyncio.TimeoutError:
            continue


async def _run_post_task_cleanup(
    callback: PostTaskCleanup | None,
    task: dict[str, Any],
) -> None:
    if callback is None:
        return

    maybe_awaitable = callback(task)
    if inspect.isawaitable(maybe_awaitable):
        await maybe_awaitable
