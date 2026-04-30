from __future__ import annotations

import asyncio
import sys
import threading
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import streaming  # noqa: E402


def test_fallback_does_not_start_next_threaded_step_while_previous_one_is_still_running():
    first_started = threading.Event()
    first_release = threading.Event()
    second_started = threading.Event()

    def first_func(state: dict[str, object]) -> dict[str, object]:
        first_started.set()
        first_release.wait(timeout=1.0)
        return {"step": state["step_name"]}

    def second_func(state: dict[str, object]) -> dict[str, object]:
        second_started.set()
        return {"step": state["step_name"]}

    async def run_scenario() -> None:
        async for event in streaming.stream_agent_step(
            agent="owl",
            step="first",
            message="first",
            state={"step_name": "first"},
            func=first_func,
            timeout_s=0.01,
            heartbeat_interval_s=0.01,
            fallback_timeout_s=0.02,
            fallback_func=lambda state: {"step": f"{state['step_name']}-fallback"},
        ):
            if event["event"] == "agent_completed":
                break

        assert first_started.is_set()

        second_task = asyncio.create_task(
            _consume_some_events(
                streaming.stream_agent_step(
                    agent="dog",
                    step="second",
                    message="second",
                    state={"step_name": "second"},
                    func=second_func,
                    timeout_s=0.1,
                    heartbeat_interval_s=0.01,
                )
            )
        )

        await asyncio.sleep(0.05)
        assert not second_started.is_set()

        first_release.set()
        await asyncio.wait_for(asyncio.to_thread(second_started.wait), timeout=1.0)
        await second_task

    asyncio.run(run_scenario())


async def _consume_some_events(stream):
    async for event in stream:
        if event["event"] == "agent_completed":
            break
