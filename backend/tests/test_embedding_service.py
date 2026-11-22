"""Embedding service tests with a real ChromaDB (ephemeral) and fake embeddings."""

import uuid

import chromadb
import pytest

from core import chroma as chroma_client
from services import embedding_service


def _fake_embed_texts(texts):
    """Deterministic 3-dim vectors keyed on topic words, so similarity is exact."""
    vectors = []
    for t in texts:
        t = t.lower()
        if "cat" in t:
            vectors.append([1.0, 0.0, 0.0])
        elif "dog" in t:
            vectors.append([0.0, 1.0, 0.0])
        elif "quantum" in t:
            vectors.append([0.0, 0.0, 1.0])
        else:
            vectors.append([0.33, 0.33, 0.33])
    return vectors


@pytest.fixture()
def collection():
    # EphemeralClient shares one in-memory store per process, so each test
    # needs a uniquely named collection to start empty.
    client = chromadb.EphemeralClient()
    return client.create_collection(f"pdf_chunks_{uuid.uuid4().hex[:8]}")


@pytest.fixture(autouse=True)
def _patch_chroma_and_gemini(monkeypatch, collection):
    monkeypatch.setattr("core.chroma.get_collection", lambda: collection)
    monkeypatch.setattr(
        "services.embedding_service.gemini.embed_texts", _fake_embed_texts
    )


def _chunks(*texts):
    return [{"text": t, "page": i + 1, "chunk_index": i} for i, t in enumerate(texts)]


def test_embed_and_store_chunks(collection):
    user_id, doc_id = uuid.uuid4(), uuid.uuid4()
    n = embedding_service.embed_and_store_chunks(
        user_id,
        doc_id,
        _chunks("Cats sleep all day.", "Dogs love walks."),
        "notes.pdf",
    )
    assert n == 2
    assert collection.count() == 2


def test_semantic_search_finds_relevant_chunk():
    user_id, doc_id = uuid.uuid4(), uuid.uuid4()
    embedding_service.embed_and_store_chunks(
        user_id,
        doc_id,
        _chunks(
            "Cats sleep all day.",
            "Dogs love walks.",
            "Quantum physics is strange.",
        ),
        "notes.pdf",
    )
    results = chroma_client.query_chunks([1.0, 0.0, 0.0], user_id=user_id, top_k=3)
    assert results[0]["text"] == "Cats sleep all day."
    assert results[0]["distance"] == pytest.approx(0.0)


def test_search_filters_by_user():
    u1, u2, doc_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    embedding_service.embed_and_store_chunks(
        u1, doc_id, _chunks("Cats sleep all day."), "a.pdf"
    )
    embedding_service.embed_and_store_chunks(
        u2, doc_id, _chunks("Cats are secret."), "b.pdf"
    )
    results = chroma_client.query_chunks([1.0, 0.0, 0.0], user_id=u1, top_k=5)
    assert len(results) == 1
    assert results[0]["text"] == "Cats sleep all day."


def test_search_filters_by_document():
    user_id, d1, d2 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    embedding_service.embed_and_store_chunks(
        user_id, d1, _chunks("Cats sleep all day."), "a.pdf"
    )
    embedding_service.embed_and_store_chunks(
        user_id, d2, _chunks("Cats are secret."), "b.pdf"
    )
    results = chroma_client.query_chunks(
        [1.0, 0.0, 0.0], user_id=user_id, document_id=d1, top_k=5
    )
    assert len(results) == 1
    assert results[0]["text"] == "Cats sleep all day."


def test_get_document_text_orders_by_chunk_index():
    user_id, doc_id = uuid.uuid4(), uuid.uuid4()
    chunks = [
        {"text": "third", "page": 3, "chunk_index": 2},
        {"text": "first", "page": 1, "chunk_index": 0},
        {"text": "second", "page": 2, "chunk_index": 1},
    ]
    embedding_service.embed_and_store_chunks(user_id, doc_id, chunks, "notes.pdf")
    assert (
        embedding_service.get_document_text(user_id, doc_id)
        == "first\n\nsecond\n\nthird"
    )


def test_delete_document_embeddings(collection):
    user_id, d1, d2 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    embedding_service.embed_and_store_chunks(
        user_id, d1, _chunks("Cats sleep."), "a.pdf"
    )
    embedding_service.embed_and_store_chunks(
        user_id, d2, _chunks("Dogs bark."), "b.pdf"
    )
    assert collection.count() == 2
    embedding_service.delete_document_embeddings(d1)
    assert collection.count() == 1
    assert embedding_service.get_document_text(user_id, d2) == "Dogs bark."
    assert embedding_service.get_document_text(user_id, d1) == ""


def test_embed_empty_chunks_returns_zero(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "services.embedding_service.gemini.embed_texts",
        lambda texts: calls.append(texts) or _fake_embed_texts(texts),
    )
    assert (
        embedding_service.embed_and_store_chunks(
            uuid.uuid4(), uuid.uuid4(), [], "x.pdf"
        )
        == 0
    )
    assert calls == []  # No embedding call for an empty chunk list.
