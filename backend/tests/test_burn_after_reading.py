from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient


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


@pytest.fixture(autouse=True)
def reset_runtime_state():
    main.contracts_store.clear()
    main.analysis_results.clear()
    analysis_queue.reset_queue_state()
    yield
    main.contracts_store.clear()
    main.analysis_results.clear()
    analysis_queue.reset_queue_state()


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    async def fake_require_current_user(
        request: Request, allow_anonymous: bool = False
    ) -> str | None:
        authorization = request.headers.get("authorization")
        if not authorization:
            if allow_anonymous:
                return None
            raise HTTPException(status_code=401, detail="Authentication required")

        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        return token

    monkeypatch.setattr(main, "_require_current_user_id", fake_require_current_user)
    main.app.state.background_runtime_enabled = False
    try:
        with TestClient(main.app) as client:
            yield client
    finally:
        main.app.state.background_runtime_enabled = True


def test_burn_after_reading_cleanup_removes_finished_contract_state(client: TestClient):
    contract_id = "contract-1"
    main.contracts_store[contract_id] = {
        "id": contract_id,
        "owner_id": "user-1",
        "user_id": "user-1",
        "text": "secret contract",
        "location": "beijing",
        "burn_after_reading": True,
        "status": "completed",
        "created_at": 0.0,
        "last_accessed_at": 0.0,
    }
    main.analysis_results[contract_id] = {
        "report": {"summary": {}},
        "_meta": {
            "owner_id": "user-1",
            "completed_at": 10.0,
            "last_accessed_at": 10.0,
            "burn_after_reading": True,
        },
    }
    task = analysis_queue.create_task(contract_id, owner_id="user-1")
    analysis_queue.start_next_task()
    analysis_queue.complete_task(task["task_id"], status="completed", now=10.0)

    response = client.post(
        "/api/contracts/burn-after-reading/cleanup",
        json={"contract_id": contract_id},
        headers={"Authorization": "Bearer user-1"},
    )

    assert response.status_code == 200
    assert response.json()["deleted_contract_ids"] == [contract_id]
    assert contract_id not in main.contracts_store
    assert contract_id not in main.analysis_results
    assert analysis_queue.get_task(task["task_id"]) is None


def test_contract_history_lists_only_owned_reports_with_risk_summary(client: TestClient):
    main.contracts_store["contract-1"] = {
        "id": "contract-1",
        "owner_id": "user-1",
        "user_id": "user-1",
        "filename": "first.docx",
        "location": "shanghai",
        "burn_after_reading": True,
        "status": "completed",
        "created_at": 100.0,
        "completed_at": 150.0,
        "last_accessed_at": 150.0,
    }
    main.analysis_results["contract-1"] = {
        "risk_items": [
            {"risk_level": "high"},
            {"risk_level": "medium"},
            {"risk_level": "medium"},
        ],
        "_meta": {
            "owner_id": "user-1",
            "completed_at": 150.0,
            "last_accessed_at": 150.0,
            "burn_after_reading": True,
        },
    }

    main.contracts_store["contract-2"] = {
        "id": "contract-2",
        "owner_id": "user-2",
        "user_id": "user-2",
        "filename": "second.docx",
        "location": "beijing",
        "burn_after_reading": False,
        "status": "completed",
        "created_at": 200.0,
        "completed_at": 250.0,
        "last_accessed_at": 250.0,
    }
    main.analysis_results["contract-2"] = {
        "risk_items": [{"risk_level": "low"}],
        "_meta": {
            "owner_id": "user-2",
            "completed_at": 250.0,
            "last_accessed_at": 250.0,
            "burn_after_reading": False,
        },
    }

    response = client.get(
        "/api/contracts/history",
        headers={"Authorization": "Bearer user-1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["contracts"]) == 1
    history_item = payload["contracts"][0]
    assert history_item["contract_id"] == "contract-1"
    assert history_item["filename"] == "first.docx"
    assert history_item["location"] == "shanghai"
    assert history_item["burn_after_reading"] is True
    assert history_item["risk_summary"] == {
        "high": 1,
        "medium": 2,
        "low": 0,
        "total": 3,
    }
