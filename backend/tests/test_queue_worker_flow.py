from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import analysis_queue  # noqa: E402
import analysis_queue_worker  # noqa: E402


def test_process_next_queued_task_runs_serially():
    async def scenario() -> None:
        analysis_queue.reset_queue_state()
        first = analysis_queue.create_task("contract-1", owner_id="user-1")
        second = analysis_queue.create_task("contract-2", owner_id="user-1")

        contracts = {
            "contract-1": {
                "id": "contract-1",
                "text": "contract one",
                "location": "beijing",
                "user_id": "user-1",
            },
            "contract-2": {
                "id": "contract-2",
                "text": "contract two",
                "location": "shanghai",
                "user_id": "user-1",
            },
        }
        results: dict[str, dict] = {}
        started = asyncio.Event()
        release = asyncio.Event()

        async def fake_events(*, contract_id: str, **_: object):
            started.set()
            await release.wait()
            yield {
                "event": "analysis_complete",
                "data": {"state": {"report": {"summary": {}}, "contract_id": contract_id}},
            }

        def load_contract(contract_id: str):
            return contracts.get(contract_id)

        def store_result(contract_id: str, state: dict) -> None:
            results[contract_id] = state

        with patch.object(
            analysis_queue_worker,
            "run_contract_analysis_events",
            fake_events,
        ):
            first_run = asyncio.create_task(
                analysis_queue_worker.process_next_queued_task(
                    load_contract=load_contract,
                    store_result=store_result,
                )
            )
            await started.wait()

            second_run = await analysis_queue_worker.process_next_queued_task(
                load_contract=load_contract,
                store_result=store_result,
            )
            assert second_run is False
            assert analysis_queue.get_running_task_id() == first["task_id"]
            assert analysis_queue.get_task(second["task_id"])["status"] == "pending"

            release.set()
            assert await first_run is True

            assert await analysis_queue_worker.process_next_queued_task(
                load_contract=load_contract,
                store_result=store_result,
            ) is True
            assert set(results.keys()) == {"contract-1", "contract-2"}

    asyncio.run(scenario())
