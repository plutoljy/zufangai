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


def test_agent_chat_returns_reply_for_contract_owner(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    main.contracts_store["contract-1"] = {
        "id": "contract-1",
        "owner_id": "user-1",
        "user_id": "user-1",
        "filename": "lease.docx",
        "text": "月租金 4980 元，水费 6 元/吨，电费 0.8 元/度。",
        "location": "shanghai",
        "status": "completed",
        "created_at": 10.0,
        "last_accessed_at": 10.0,
    }
    main.analysis_results["contract-1"] = {
        "risk_items": [{"risk_level": "high", "issue": "水费过高"}],
        "report": {"report_markdown": "# 报告"},
        "_meta": {
            "owner_id": "user-1",
            "completed_at": 20.0,
            "last_accessed_at": 20.0,
            "burn_after_reading": False,
        },
    }

    def fake_chat(
        *,
        agent_key: str,
        contract_text: str,
        report: dict,
        messages: list[dict],
        question: str,
        user_id: str | None = None,
        access_token: str | None = None,
    ) -> str:
        assert agent_key == "beaver"
        assert "水费 6 元/吨" in contract_text
        assert report["risk_items"][0]["issue"] == "水费过高"
        assert messages == [{"role": "user", "content": "这条怎么算的？"}]
        assert question == "如果房东坚持不改怎么办？"
        assert user_id == "user-1"
        assert access_token is None
        return "这是 Beaver 的追问回复"

    monkeypatch.setattr(main, "generate_agent_chat_reply", fake_chat)

    response = client.post(
        "/api/contracts/contract-1/agents/beaver/chat",
        headers={"Authorization": "Bearer user-1"},
        json={
            "question": "如果房东坚持不改怎么办？",
            "messages": [{"role": "user", "content": "这条怎么算的？"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["contract_id"] == "contract-1"
    assert payload["agent"] == "beaver"
    assert payload["reply"] == "这是 Beaver 的追问回复"


def test_agent_chat_rejects_non_owner(client: TestClient):
    main.contracts_store["contract-1"] = {
        "id": "contract-1",
        "owner_id": "user-1",
        "user_id": "user-1",
        "filename": "lease.docx",
        "text": "secret contract",
        "location": "shanghai",
        "status": "completed",
        "created_at": 10.0,
        "last_accessed_at": 10.0,
    }
    main.analysis_results["contract-1"] = {
        "risk_items": [],
        "report": {"report_markdown": "# 报告"},
        "_meta": {
            "owner_id": "user-1",
            "completed_at": 20.0,
            "last_accessed_at": 20.0,
            "burn_after_reading": False,
        },
    }

    response = client.post(
        "/api/contracts/contract-1/agents/owl/chat",
        headers={"Authorization": "Bearer user-2"},
        json={"question": "解释一下", "messages": []},
    )

    assert response.status_code == 403
