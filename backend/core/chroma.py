"""ChromaDB client (vector store for PDF chunks).

Supports two modes (see CHROMA_MODE in settings):
- "local": embedded PersistentClient, data in CHROMA_PERSIST_DIR
- "http":  connects to a Chroma server at CHROMA_HOST:CHROMA_PORT

The chromadb package is imported lazily so the app can start without it.
"""

from core.config import get_settings
from core.exceptions import ExternalServiceError
from core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

COLLECTION_NAME = "pdf_chunks"

_client = None
_collection = None


def get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection
    try:
        import chromadb
    except ImportError as exc:
        raise ExternalServiceError("chromadb is not installed") from exc
    if settings.CHROMA_MODE == "http":
        _client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
    else:
        _client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )
    return _collection


def add_chunks(chunks: list[dict], embeddings: list[list[float]]) -> None:
    """Store chunks. Each chunk needs: id, text, user_id, document_id, page,
    chunk_index, source_title."""
    collection = get_collection()
    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=embeddings,
        metadatas=[
            {
                "user_id": c["user_id"],
                "document_id": c["document_id"],
                "page": c["page"],
                "chunk_index": c["chunk_index"],
                "source_title": c.get("source_title", ""),
            }
            for c in chunks
        ],
    )


def query_chunks(
    query_embedding: list[float],
    user_id,
    document_id=None,
    top_k: int = 5,
) -> list[dict]:
    """Similarity search, always filtered by user_id (and document_id if given)."""
    collection = get_collection()
    where: dict = {"user_id": str(user_id)}
    if document_id:
        where = {"$and": [{"user_id": str(user_id)}, {"document_id": str(document_id)}]}
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k, where=where)
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    return [
        {
            "text": d,
            "page": m.get("page"),
            "chunk_index": m.get("chunk_index"),
            "distance": dist,
        }
        for d, m, dist in zip(docs, metas, distances)
    ]


def get_document_chunks(document_id, user_id, limit: int = 500) -> list[dict]:
    """Fetch all stored chunks for one document, in original order."""
    collection = get_collection()
    results = collection.get(
        where={"$and": [{"user_id": str(user_id)}, {"document_id": str(document_id)}]},
        limit=limit,
    )
    docs = results.get("documents", [])
    metas = results.get("metadatas", [])
    chunks = [
        {"text": d, "page": m.get("page"), "chunk_index": m.get("chunk_index", 0)}
        for d, m in zip(docs, metas)
    ]
    return sorted(chunks, key=lambda c: c["chunk_index"])


def delete_document_chunks(document_id) -> None:
    collection = get_collection()
    collection.delete(where={"document_id": str(document_id)})
