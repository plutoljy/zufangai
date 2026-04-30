from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import main  # noqa: E402
import analysis_queue  # noqa: E402


@pytest.fixture(autouse=True)
def reset_runtime_state():
    main.contracts_store.clear()
    main.analysis_results.clear()
    analysis_queue._tasks.clear()
    analysis_queue._events.clear()
    yield
    main.contracts_store.clear()
    main.analysis_results.clear()
    analysis_queue._tasks.clear()
    analysis_queue._events.clear()


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

    monkeypatch.setattr(
        main,
        "_require_current_user_id",
        fake_require_current_user,
        raising=False,
    )
    async def fake_run_queued_analysis(**_: object) -> None:
        return None

    monkeypatch.setattr(
        main,
        "run_queued_analysis",
        fake_run_queued_analysis,
        raising=False,
    )
    main.app.state.background_runtime_enabled = False
    try:
        with TestClient(main.app) as client:
            yield client
    finally:
        main.app.state.background_runtime_enabled = True


def test_preferences_requires_authenticated_user(client: TestClient):
    response = client.get("/api/preferences/user-1")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_preferences_user_id_must_match_authenticated_user(client: TestClient):
    response = client.get(
        "/api/preferences/user-2",
        headers={"Authorization": "Bearer user-1"},
    )

    assert response.status_code == 403


def test_report_rejects_different_authenticated_user(client: TestClient):
    contract_id = "contract-1"
    main.contracts_store[contract_id] = {
        "id": contract_id,
        "text": "test contract",
        "owner_id": "user-1",
    }
    main.analysis_results[contract_id] = {
        "entities": {},
        "risk_items": [],
        "legal_references": [],
        "case_references": [],
        "suggestions": [],
        "negotiation_tips": [],
        "calculations": {},
        "report": {"report_markdown": "", "summary": {}},
    }

    response = client.get(
        f"/api/contracts/{contract_id}/report",
        headers={"Authorization": "Bearer user-2"},
    )

    assert response.status_code == 403


def test_report_allows_contract_owner(client: TestClient):
    contract_id = "contract-1"
    main.contracts_store[contract_id] = {
        "id": contract_id,
        "text": "test contract",
        "owner_id": "user-1",
    }
    main.analysis_results[contract_id] = {
        "entities": {},
        "risk_items": [],
        "legal_references": [],
        "case_references": [],
        "suggestions": [],
        "negotiation_tips": [],
        "calculations": {},
        "report": {"report_markdown": "", "summary": {}},
    }

    response = client.get(
        f"/api/contracts/{contract_id}/report",
        headers={"Authorization": "Bearer user-1"},
    )

    assert response.status_code == 200
    assert response.json()["contract_id"] == contract_id


def test_task_status_rejects_different_authenticated_user(client: TestClient):
    contract_id = "contract-1"
    main.contracts_store[contract_id] = {
        "id": contract_id,
        "text": "test contract",
        "location": "beijing",
        "owner_id": "user-1",
        "user_id": "user-1",
    }

    queue_response = client.post(
        f"/api/contracts/{contract_id}/analyze/queue",
        headers={"Authorization": "Bearer user-1"},
    )
    assert queue_response.status_code == 200
    task_id = queue_response.json()["task_id"]

    response = client.get(
        f"/api/analysis/tasks/{task_id}",
        headers={"Authorization": "Bearer user-2"},
    )

    assert response.status_code == 403


def test_stream_requires_valid_task_bound_token(client: TestClient):
    contract_id = "contract-1"
    main.contracts_store[contract_id] = {
        "id": contract_id,
        "text": "test contract",
        "location": "beijing",
        "owner_id": "user-1",
        "user_id": "user-1",
    }

    queue_response = client.post(
        f"/api/contracts/{contract_id}/analyze/queue",
        headers={"Authorization": "Bearer user-1"},
    )
    assert queue_response.status_code == 200
    payload = queue_response.json()
    task_id = payload["task_id"]
    stream_token = payload.get("stream_token")

    assert stream_token

    invalid_response = client.get(f"/api/analysis/tasks/{task_id}/stream")
    assert invalid_response.status_code == 401

    analysis_queue.update_task(task_id, status="completed")
    valid_response = client.get(
        f"/api/analysis/tasks/{task_id}/stream?stream_token={stream_token}"
    )
    assert valid_response.status_code == 200


def test_task_status_returns_fresh_stream_token_for_owner(client: TestClient):
    contract_id = "contract-1"
    main.contracts_store[contract_id] = {
        "id": contract_id,
        "text": "test contract",
        "location": "beijing",
        "owner_id": "user-1",
        "user_id": "user-1",
    }

    queue_response = client.post(
        f"/api/contracts/{contract_id}/analyze/queue",
        headers={"Authorization": "Bearer user-1"},
    )
    assert queue_response.status_code == 200
    task_id = queue_response.json()["task_id"]

    response = client.get(
        f"/api/analysis/tasks/{task_id}",
        headers={"Authorization": "Bearer user-1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == task_id
    assert payload["stream_token"]
