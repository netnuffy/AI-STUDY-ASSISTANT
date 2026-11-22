"""PDF text extraction (PyMuPDF) and chunking for embeddings."""

import re

from core.exceptions import BadRequestError
from core.logging import get_logger

logger = get_logger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def clean_text(text: str) -> str:
    text = re.sub(r"-\n", "", text)  # de-hyphenate words split across lines
    text = re.sub(r"\s+", " ", text)  # collapse whitespace
    return text.strip()


def extract_text_per_page(file_path: str) -> list[dict]:
    """Returns [{"page": 1, "text": "..."}, ...]. Raises BadRequestError if the
    PDF cannot be read, is password-protected, or contains no extractable
    text (e.g. scanned images)."""
    try:
        import fitz  # PyMuPDF (lazy import so the app starts without it)
    except ImportError as exc:
        raise BadRequestError("PDF extraction library is not installed") from exc
    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        raise BadRequestError("Could not open PDF file") from exc
    pages = []
    with doc:
        if doc.needs_pass:
            raise BadRequestError(
                "This PDF is password-protected. Please upload an unlocked PDF."
            )
        for i, page in enumerate(doc):
            pages.append({"page": i + 1, "text": clean_text(page.get_text())})
    if not any(p["text"].strip() for p in pages):
        raise BadRequestError(
            "No readable text found in this PDF (it may be a scanned image)"
        )
    return pages


def chunk_pages(
    pages: list[dict],
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    """Split page texts into overlapping chunks for embeddings.

    Returns [{"text": "...", "page": 1, "chunk_index": 0}, ...].
    Chunks are extended to the next sentence boundary when possible.
    """
    chunks: list[dict] = []
    index = 0
    for page in pages:
        text = page["text"]
        if not text:
            continue
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end < len(text):
                match = re.search(r"[.!?]\s", text[end : end + 200])
                if match:
                    end = end + match.end()
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({"text": chunk_text, "page": page["page"], "chunk_index": index})
                index += 1
            start = max(end - overlap, start + 1)
    return chunks
