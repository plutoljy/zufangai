"""
In-memory analysis task queue for long-running contract reviews.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from typing import Any, Optional

DONE_SENTINEL = "_done"
FINISHED_STATUSES = {"completed", "failed", "cancelled"}

_tasks: dict[str, dict[str, Any]] = {}
_events: dict[str, list[dict[str, Any]]] = {}
_pending_task_ids: deque[str] = deque()
_running_task_id: str | None = None
_lock = threading.Lock()


def _now_ts(now: float | None = None) -> float:
    return float(now if now is not None else time.time())


def _recompute_queue_positions() -> None:
    if _running_task_id and _running_task_id in _tasks:
        _tasks[_running_task_id]["queue_position"] = 1

    base_position = 2 if _running_task_id and _running_task_id in _tasks else 1
    for index, task_id in enumerate(_pending_task_ids, start=base_position):
        if task_id in _tasks:
            _tasks[task_id]["queue_position"] = index

    for task_id, task in _tasks.items():
        if task_id != _running_task_id and task_id not in _pending_task_ids:
            task["queue_position"] = None


def reset_queue_state() -> None:
    global _running_task_id
    with _lock:
        _tasks.clear()
        _events.clear()
        _pending_task_ids.clear()
        _running_task_id = None


def create_task(
    contract_id: str,
    owner_id: str | None = None,
    now: float | None = None,
    **metadata: Any,
) -> dict[str, Any]:
    with _lock:
        task_id = uuid.uuid4().hex
        task = {
            "task_id": task_id,
            "contract_id": contract_id,
            "owner_id": owner_id,
            "status": "pending",
            "created_at": _now_ts(now),
            "started_at": None,
            "completed_at": None,
            "queue_position": None,
            **metadata,
        }
        _tasks[task_id] = task
        _events[task_id] = []
        _pending_task_ids.append(task_id)
        _recompute_queue_positions()
        return dict(task)


def start_next_task(now: float | None = None) -> Optional[dict[str, Any]]:
    global _running_task_id
    with _lock:
        if _running_task_id is not None or not _pending_task_ids:
            return None

        task_id = _pending_task_ids.popleft()
        task = _tasks.get(task_id)
        if task is None:
            _recompute_queue_positions()
            return None

        task["status"] = "running"
        task["started_at"] = _now_ts(now)
        task["completed_at"] = None
        task.pop("error", None)
        _running_task_id = task_id
        _recompute_queue_positions()
        return dict(task)


def get_task(task_id: str) -> Optional[dict[str, Any]]:
    with _lock:
        task = _tasks.get(task_id)
        return dict(task) if task else None


def get_running_task_id() -> str | None:
    with _lock:
        return _running_task_id


def get_pending_task_ids() -> list[str]:
    with _lock:
        return list(_pending_task_ids)


def list_task_ids_for_contract(contract_id: str) -> list[str]:
    with _lock:
        return [
            task_id
            for task_id, task in _tasks.items()
            if task.get("contract_id") == contract_id
        ]


def list_task_ids_for_owner(owner_id: str) -> list[str]:
    with _lock:
        return [
            task_id
            for task_id, task in _tasks.items()
            if task.get("owner_id") == owner_id
        ]


def update_task(task_id: str, **updates: Any) -> None:
    with _lock:
        if task_id in _tasks:
            _tasks[task_id].update(updates)


def complete_task(
    task_id: str,
    *,
    status: str,
    error: str | None = None,
    now: float | None = None,
) -> Optional[dict[str, Any]]:
    global _running_task_id
    with _lock:
        task = _tasks.get(task_id)
        if task is None:
            return None

        task["status"] = status
        task["completed_at"] = _now_ts(now)
        if error:
            task["error"] = error
        else:
            task.pop("error", None)

        if _running_task_id == task_id:
            _running_task_id = None

        _recompute_queue_positions()
        return dict(task)


def push_event(task_id: str, event_type: str, data: dict[str, Any]) -> None:
    with _lock:
        if task_id not in _events:
            _events[task_id] = []
        _events[task_id].append({"event": event_type, "data": data})


def get_events(task_id: str, offset: int = 0) -> list[dict[str, Any]]:
    with _lock:
        return list(_events.get(task_id, [])[offset:])


def mark_task_for_purge(task_id: str) -> None:
    update_task(task_id, purge_requested=True)


def cleanup_finished_tasks(
    max_age_seconds: float,
    *,
    now: float | None = None,
) -> list[str]:
    current_time = _now_ts(now)
    with _lock:
        removable = [
            task_id
            for task_id, task in _tasks.items()
            if task.get("status") in FINISHED_STATUSES
            and task.get("completed_at") is not None
            and current_time - float(task["completed_at"]) >= max_age_seconds
        ]

        for task_id in removable:
            _tasks.pop(task_id, None)
            _events.pop(task_id, None)

        if removable:
            _recompute_queue_positions()

        return removable


def clear_task(task_id: str) -> None:
    global _running_task_id
    with _lock:
        _tasks.pop(task_id, None)
        _events.pop(task_id, None)
        if _running_task_id == task_id:
            _running_task_id = None
        if task_id in _pending_task_ids:
            _pending_task_ids.remove(task_id)
        _recompute_queue_positions()
