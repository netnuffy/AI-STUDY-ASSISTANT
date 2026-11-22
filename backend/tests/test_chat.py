"""Chat API tests (mocked RAG service)."""

import uuid
from datetime import datetime, timedelta, timezone

from models.chat_message import ChatMessage, ChatRole
from schemas.chat import ChatResponse, ChatSource
from tests.conftest import TestingSessionLocal


def _fake_answer(db, user, question, document_id):
    return ChatResponse(
        answer="Cats sleep a lot.",
        sources=[ChatSource(page=3, excerpt="Cats sleep for 16 hours a day.")],
        document_id=document_id,
    )


def test_chat_requires_auth(client):
    resp = client.post("/api/v1/chat", json={"question": "Hello?"})
    assert resp.status_code == 401


def test_chat_ask_returns_answer(client, auth_headers, monkeypatch):
    monkeypatch.setattr("api.v1.chat.rag_service.answer_question", _fake_answer)
    resp = client.post(
        "/api/v1/chat",
        json={"question": "How long do cats sleep?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "Cats sleep a lot."
    assert body["sources"][0]["page"] == 3
    assert body["document_id"] is None


def test_chat_ask_passes_document_id(client, auth_headers, monkeypatch):
    seen = {}

    def capturing(db, user, question, document_id):
        seen["document_id"] = document_id
        return ChatResponse(answer="a", sources=[], document_id=document_id)

    monkeypatch.setattr("api.v1.chat.rag_service.answer_question", capturing)
    doc_id = str(uuid.uuid4())
    resp = client.post(
        "/api/v1/chat",
        json={"question": "Q?", "document_id": doc_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert seen["document_id"] == uuid.UUID(doc_id)


def test_chat_ask_empty_question(client, auth_headers):
    resp = client.post("/api/v1/chat", json={"question": ""}, headers=auth_headers)
    assert resp.status_code == 422


def test_chat_history_returns_messages_in_order(client, auth_headers):
    me = client.get("/api/v1/auth/me", headers=auth_headers).json()
    user_id = uuid.UUID(me["id"])
    now = datetime.now(timezone.utc)
    db = TestingSessionLocal()
    db.add(
        ChatMessage(
            user_id=user_id,
            document_id=None,
            role=ChatRole.USER,
            content="Q1",
            created_at=now,
        )
    )
    db.add(
        ChatMessage(
            user_id=user_id,
            document_id=None,
            role=ChatRole.ASSISTANT,
            content="A1",
            created_at=now + timedelta(seconds=1),
        )
    )
    db.commit()
    db.close()
    resp = client.get("/api/v1/chat/history", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert [m["content"] for m in body] == ["Q1", "A1"]
    assert [m["role"] for m in body] == ["user", "assistant"]
