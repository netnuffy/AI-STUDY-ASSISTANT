"""StudyDocument lifecycle: create, background processing pipeline, delete."""

import os
import uuid

from sqlalchemy.orm import Session

from core.config import get_settings
from core.exceptions import NotFoundError
from core.logging import get_logger
from database.session import SessionLocal
from models.study_document import StudyDocument, DocumentStatus
from models.summary import Summary
from models.user import User
from services import embedding_service, pdf_service, summary_service

logger = get_logger(__name__)
settings = get_settings()


def create_document(
    db: Session,
    user: User,
    title: str,
    filename: str,
    file_path: str,
    file_size: int,
) -> StudyDocument:
    doc = StudyDocument(
        user_id=user.id,
        title=title,
        filename=filename,
        file_path=file_path,
        file_size_bytes=file_size,
        status=DocumentStatus.UPLOADING,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def process_document_background(document_id: uuid.UUID) -> None:
    """Full pipeline: extract -> chunk -> embed -> summarise.

    Runs in a FastAPI BackgroundTask with its own DB session, so uploads
    return immediately while processing continues.
    """
    db = SessionLocal()
    try:
        doc = db.get(StudyDocument, document_id)
        if not doc:
            logger.error("Background processing: document %s not found", document_id)
            return
        doc.status = DocumentStatus.PROCESSING
        db.commit()

        pages = pdf_service.extract_text_per_page(doc.file_path)
        doc.page_count = len(pages)
        chunks = pdf_service.chunk_pages(pages)
        embedding_service.embed_and_store_chunks(
            doc.user_id, doc.id, chunks, source_title=doc.title
        )
        full_text = "\n\n".join(c["text"] for c in chunks)
        summary_data = summary_service.generate_summary(full_text)
        db.add(
            Summary(
                document_id=doc.id,
                content=summary_data["content"],
                key_points=summary_data["key_points"],
                key_concepts=summary_data["key_concepts"],
                important_questions=summary_data["important_questions"],
            )
        )
        doc.status = DocumentStatus.READY
        db.commit()
        logger.info(
            "StudyDocument %s processed: %d pages, %d chunks", doc.id, len(pages), len(chunks)
        )
    except Exception as exc:
        logger.exception("Failed to process document %s", document_id)
        try:
            doc = db.get(StudyDocument, document_id)
            if doc:
                doc.status = DocumentStatus.FAILED
                doc.error_message = str(exc)[:500]
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def delete_document(db: Session, user: User, document_id: uuid.UUID) -> None:
    doc = (
        db.query(StudyDocument)
        .filter(StudyDocument.id == document_id, StudyDocument.user_id == user.id)
        .first()
    )
    if not doc:
        raise NotFoundError("StudyDocument not found")
    # Vector cleanup is best-effort: a Chroma outage must not block deletion.
    try:
        embedding_service.delete_document_embeddings(doc.id)
    except Exception as exc:
        logger.warning("Could not delete embeddings for %s: %s", doc.id, exc)
    try:
        os.remove(doc.file_path)
    except FileNotFoundError:
        pass
    db.delete(doc)  # cascades to summary, flashcards, quizzes, chat messages
    db.commit()
