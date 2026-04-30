from __future__ import annotations

import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import analysis_queue  # noqa: E402


def test_queue_tracks_fifo_order_and_positions():
    analysis_queue.reset_queue_state()

    first = analysis_queue.create_task("contract-1", owner_id="user-1")
    second = analysis_queue.create_task("contract-2", owner_id="user-1")

    started = analysis_queue.start_next_task()

    assert started is not None
    assert started["task_id"] == first["task_id"]
    assert analysis_queue.get_running_task_id() == first["task_id"]
    assert analysis_queue.get_pending_task_ids() == [second["task_id"]]
    assert analysis_queue.get_task(first["task_id"])["queue_position"] == 1
    assert analysis_queue.get_task(second["task_id"])["queue_position"] == 2


def test_clear_task_recomputes_pending_positions():
    analysis_queue.reset_queue_state()

    first = analysis_queue.create_task("contract-1", owner_id="user-1")
    second = analysis_queue.create_task("contract-2", owner_id="user-1")
    third = analysis_queue.create_task("contract-3", owner_id="user-1")

    analysis_queue.clear_task(second["task_id"])

    assert analysis_queue.get_pending_task_ids() == [
        first["task_id"],
        third["task_id"],
    ]
    assert analysis_queue.get_task(first["task_id"])["queue_position"] == 1
    assert analysis_queue.get_task(third["task_id"])["queue_position"] == 2


def test_cleanup_finished_tasks_removes_old_completed_state():
    analysis_queue.reset_queue_state()

    task = analysis_queue.create_task("contract-1", owner_id="user-1")
    analysis_queue.start_next_task()
    analysis_queue.push_event(task["task_id"], "analysis_complete", {"ok": True})
    analysis_queue.complete_task(task["task_id"], status="completed", now=100.0)

    removed = analysis_queue.cleanup_finished_tasks(max_age_seconds=30, now=131.0)

    assert removed == [task["task_id"]]
    assert analysis_queue.get_task(task["task_id"]) is None
    assert analysis_queue.get_events(task["task_id"]) == []
