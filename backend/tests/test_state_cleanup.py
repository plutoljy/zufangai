from __future__ import annotations

import sys
import types
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

fake_retriever_module = types.ModuleType("knowledge.retriever")


class _FakeRetriever:
    def search_all(self, _query, top_k=3):
        return {"legal_docs": [], "cases": []}


def _get_retriever():
    return _FakeRetriever()


fake_retriever_module.get_retriever = _get_retriever
sys.modules["knowledge.retriever"] = fake_retriever_module

import analysis_queue  # noqa: E402
import main  # noqa: E402


def test_cleanup_runtime_state_removes_stale_contracts_reports_and_tasks():
    analysis_queue.reset_queue_state()
    main.contracts_store.clear()
    main.analysis_results.clear()

    contract_id = "contract-1"
    main.contracts_store[contract_id] = {
        "id": contract_id,
        "owner_id": "user-1",
        "text": "contract text",
        "created_at": 0.0,
        "last_accessed_at": 0.0,
        "burn_after_reading": False,
        "status": "uploaded",
    }
    main.analysis_results[contract_id] = {
        "report": {"summary": {}},
        "_meta": {
            "owner_id": "user-1",
            "completed_at": 0.0,
            "last_accessed_at": 0.0,
            "burn_after_reading": False,
        },
    }
    task = analysis_queue.create_task(contract_id, owner_id="user-1")
    analysis_queue.start_next_task()
    analysis_queue.complete_task(task["task_id"], status="completed", now=0.0)

    summary = main.cleanup_runtime_state(now=3601.0)

    assert contract_id not in main.contracts_store
    assert contract_id not in main.analysis_results
    assert analysis_queue.get_task(task["task_id"]) is None
    assert summary["contracts_removed"] >= 1
    assert summary["reports_removed"] >= 1
    assert summary["tasks_removed"] >= 1


def test_cleanup_runtime_state_does_not_auto_purge_burn_after_reading_before_logout():
    analysis_queue.reset_queue_state()
    main.contracts_store.clear()
    main.analysis_results.clear()

    contract_id = "contract-burn"
    main.contracts_store[contract_id] = {
        "id": contract_id,
        "owner_id": "user-1",
        "text": "contract text",
        "created_at": 0.0,
        "completed_at": 0.0,
        "last_accessed_at": 0.0,
        "burn_after_reading": True,
        "status": "completed",
    }
    main.analysis_results[contract_id] = {
        "report": {"summary": {}},
        "_meta": {
            "owner_id": "user-1",
            "completed_at": 0.0,
            "last_accessed_at": 0.0,
            "burn_after_reading": True,
        },
    }

    summary = main.cleanup_runtime_state(now=301.0)

    assert contract_id in main.contracts_store
    assert contract_id in main.analysis_results
    assert summary["contracts_removed"] == 0
    assert summary["reports_removed"] == 0
