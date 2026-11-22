"""Embed PDF chunks with Gemini and store them in ChromaDB."""

import uuid

from core import chroma as chroma_client
from core import gemini
from core.logging import get_logger

logger = get_logger(__name__)

EMBED_BATCH_SIZE = 100


def embed_and_store_chunks(
    user_id, document_id, chunks: list[dict], source_title: str
) -> int:
    if not chunks:
        return 0
    for c in chunks:
        c["id"] = str(uuid.uuid4())
        c["user_id"] = str(user_id)
        c["document_id"] = str(document_id)
        c["source_title"] = source_title
    for i in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[i : i + EMBED_BATCH_SIZE]
        embeddings = gemini.embed_texts([c["text"] for c in batch])
        chroma_client.add_chunks(batch, embeddings)
    logger.info("Stored %d chunks for document %s", len(chunks), document_id)
    return len(chunks)


def delete_document_embeddings(document_id) -> None:
    chroma_client.delete_document_chunks(document_id)


def get_document_text(user_id, document_id, max_chars: int = 60000) -> str:
    """Reassemble a document's text from its stored chunks (for summary /
    flashcard / quiz generation, without re-reading the PDF)."""
    chunks = chroma_client.get_document_chunks(document_id, user_id)
    text = "\n\n".join(c["text"] for c in chunks)
    return text[:max_chars]
