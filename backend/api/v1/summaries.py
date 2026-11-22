import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.v1.deps import get_current_user
from core.exceptions import BadRequestError, NotFoundError
from database.session import get_db
from models.study_document import StudyDocument
from models.summary import Summary
from models.user import User
from services import embedding_service, summary_service

router = APIRouter(prefix="/documents", tags=["summaries"])
recent_router = APIRouter(prefix="/summaries", tags=["summaries"])


class KeyConcept(BaseModel):
    term: str
    definition: str = ""


class SummaryResponse(BaseModel):
    document_id: uuid.UUID
    content: str
    key_points: list[str]
    key_concepts: list[KeyConcept]
    important_questions: list[str]


class RegenerateRequest(BaseModel):
    style: str = Field(default="standard", pattern="^(short|standard|detailed)$")


class RecentSummaryResponse(BaseModel):
    document_id: uuid.UUID
    document_title: str
    content_preview: str
    key_points_count: int
    updated_at: datetime


def _get_document(db: Session, user: User, document_id: uuid.UUID) -> StudyDocument:
    doc = (
        db.query(StudyDocument)
        .filter(StudyDocument.id == document_id, StudyDocument.user_id == user.id)
        .first()
    )
    if not doc:
        raise NotFoundError("StudyDocument not found")
    return doc


def _to_response(doc_id: uuid.UUID, summary: Summary) -> SummaryResponse:
    return SummaryResponse(
        document_id=doc_id,
        content=summary.content,
        key_points=summary.key_points,
        key_concepts=summary.key_concepts,
        important_questions=summary.important_questions,
    )


@router.get("/{document_id}/summary", response_model=SummaryResponse)
def get_summary(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_document(db, current_user, document_id)
    summary = db.query(Summary).filter(Summary.document_id == doc.id).first()
    if not summary:
        raise NotFoundError("Summary is not ready yet")
    return _to_response(doc.id, summary)


@recent_router.get("/recent", response_model=list[RecentSummaryResponse])
def recent_summaries(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The user's most recently updated summaries, for the dashboard."""
    rows = (
        db.query(Summary, StudyDocument.title)
        .join(StudyDocument, Summary.document_id == StudyDocument.id)
        .filter(StudyDocument.user_id == current_user.id)
        .order_by(Summary.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [
        RecentSummaryResponse(
            document_id=s.document_id,
            document_title=title,
            content_preview=s.content[:200],
            key_points_count=len(s.key_points or []),
            updated_at=s.updated_at,
        )
        for s, title in rows
    ]


@router.post("/{document_id}/summary/regenerate", response_model=SummaryResponse)
def regenerate_summary(
    document_id: uuid.UUID,
    data: RegenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_document(db, current_user, document_id)
    text = embedding_service.get_document_text(current_user.id, doc.id)
    if not text.strip():
        raise BadRequestError("This document has no processed text yet")
    result = summary_service.generate_summary(text, style=data.style)
    summary = db.query(Summary).filter(Summary.document_id == doc.id).first()
    if summary:
        summary.content = result["content"]
        summary.key_points = result["key_points"]
        summary.key_concepts = result["key_concepts"]
        summary.important_questions = result["important_questions"]
    else:
        summary = Summary(
            document_id=doc.id,
            content=result["content"],
            key_points=result["key_points"],
            key_concepts=result["key_concepts"],
            important_questions=result["important_questions"],
        )
        db.add(summary)
    db.commit()
    db.refresh(summary)
    return _to_response(doc.id, summary)
