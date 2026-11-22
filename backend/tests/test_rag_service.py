"""RAG service tests: real ChromaDB retrieval, mocked Gemini."""

import uuid

import chromadb
import pytest

from core import chroma as chroma_client
from core.exceptions import NotFoundError
from models.chat_message import ChatMessage, ChatRole
from models.study_document import DocumentStatus, StudyDocument
from models.user import User
from services import rag_service
from tests.conftest import TestingSessionLocal


def _fake_embed_query(text):
    t = text.lower()
    if "cat" in t:
        return [1.0, 0.0, 0.0]
    if "dog" in t:
        return [0.0, 1.0, 0.0]
    return [0.33, 0.33, 0.33]


@pytest.fixture()
def collection():
    # EphemeralClient shares one in-memory store per process, so each test
    # needs a uniquely named collection to start empty.
    client = chromadb.EphemeralClient()
    return client.create_collection(f"pdf_chunks_{uuid.uuid4().hex[:8]}")


@pytest.fixture(autouse=True)
def _patch_chroma_and_gemini(monkeypatch, collection):
    monkeypatch.setattr("core.chroma.get_collection", lambda: collection)
    monkeypatch.setattr("services.rag_service.gemini.embed_query", _fake_embed_query)


@pytest.fixture()
def user_and_doc():
    db = TestingSessionLocal()
    user = User(
        email=f"rag-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Rag Tester",
        hashed_password="hashed",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    doc = StudyDocument(
        user_id=user.id,
        title="notes.pdf",
        filename="notes.pdf",
        file_path="/tmp/notes.pdf",
        file_size_bytes=1234,
        status=DocumentStatus.READY,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    yield db, user, doc
    db.close()


def _store_chunks(user_id, doc_id, items):
    """items: list of (text, page, chunk_index, vector)."""
    chunks = [
        {
            "id": str(uuid.uuid4()),
            "text": text,
            "user_id": str(user_id),
            "document_id": str(doc_id),
            "page": page,
            "chunk_index": idx,
            "source_title": "notes.pdf",
        }
        for text, page, idx, _ in items
    ]
    vectors = [v for _, _, _, v in items]
    chroma_client.add_chunks(chunks, vectors)


def test_answer_question_grounds_answer_in_chunks(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    _store_chunks(
        user.id,
        doc.id,
        [
            ("Cats sleep for 16 hours a day.", 3, 0, [1.0, 0.0, 0.0]),
            ("Dogs need daily walks.", 5, 1, [0.0, 1.0, 0.0]),
        ],
    )
    seen = {}

    def fake_generate(prompt, system_instruction=None, json_mode=False, temperature=0.3):
        seen["prompt"] = prompt
        seen["system"] = system_instruction
        return "Cats sleep a lot. [p. 3]"

    monkeypatch.setattr("services.rag_service.gemini.generate_text", fake_generate)
    result = rag_service.answer_question(db, user, "How long do cats sleep?", doc.id)
    assert result.answer == "Cats sleep a lot. [p. 3]"
    assert result.document_id == doc.id
    # Nearest chunk first, both present as sources.
    assert result.sources[0].page == 3
    assert len(result.sources) == 2
    # The prompt sent to Gemini contains the retrieved context.
    assert "Cats sleep for 16 hours a day." in seen["prompt"]
    assert "If the answer is not in the context" in seen["system"]
    # Both messages saved to history.
    messages = db.query(ChatMessage).filter(ChatMessage.user_id == user.id).all()
    assert [m.role for m in messages] == [ChatRole.USER, ChatRole.ASSISTANT]
    assert messages[0].content == "How long do cats sleep?"


def test_answer_question_no_chunks_returns_fallback(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    calls = []

    def counting(prompt, system_instruction=None, json_mode=False, temperature=0.3):
        calls.append(prompt)
        return "should not be called"

    monkeypatch.setattr("services.rag_service.gemini.generate_text", counting)
    result = rag_service.answer_question(db, user, "What is quantum physics?", doc.id)
    assert "couldn't find" in result.answer
    assert result.sources == []
    assert calls == []  # No Gemini call when nothing was retrieved.
    messages = db.query(ChatMessage).filter(ChatMessage.user_id == user.id).all()
    assert len(messages) == 2  # Question + fallback still saved to history.


def test_answer_question_document_not_found(user_and_doc):
    db, user, _ = user_and_doc
    with pytest.raises(NotFoundError):
        rag_service.answer_question(db, user, "Hello?", uuid.uuid4())


def test_answer_question_scopes_to_document(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    other_doc_id = uuid.uuid4()
    # Same vector for both, so only the document_id filter can separate them.
    _store_chunks(user.id, doc.id, [("Cats sleep a lot.", 1, 0, [1.0, 0.0, 0.0])])
    _store_chunks(user.id, other_doc_id, [("Dogs bark loudly.", 2, 0, [1.0, 0.0, 0.0])])
    seen = {}

    def capture(prompt, system_instruction=None, json_mode=False, temperature=0.3):
        seen["prompt"] = prompt
        return "answer"

    monkeypatch.setattr("services.rag_service.gemini.generate_text", capture)
    rag_service.answer_question(db, user, "Tell me about cats", doc.id)
    assert "Cats sleep a lot." in seen["prompt"]
    assert "Dogs bark loudly." not in seen["prompt"]


def test_answer_question_across_all_documents(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    _store_chunks(user.id, doc.id, [("Cats sleep a lot.", 1, 0, [1.0, 0.0, 0.0])])
    seen = {}

    def capture(prompt, system_instruction=None, json_mode=False, temperature=0.3):
        seen["prompt"] = prompt
        return "answer"

    monkeypatch.setattr("services.rag_service.gemini.generate_text", capture)
    result = rag_service.answer_question(db, user, "Tell me about cats", None)
    assert result.document_id is None
    assert "Cats sleep a lot." in seen["prompt"]
