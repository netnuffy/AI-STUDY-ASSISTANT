import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.v1.deps import get_current_user
from core.exceptions import NotFoundError
from database.session import get_db
from models.study_document import StudyDocument
from models.flashcard import Flashcard
from models.user import User
from schemas.flashcard import (
    FlashcardGenerateRequest,
    FlashcardResponse,
    FlashcardReviewRequest,
)
from services import flashcard_service

router = APIRouter(tags=["flashcards"])


@router.post(
    "/documents/{document_id}/flashcards/generate",
    response_model=list[FlashcardResponse],
    status_code=201,
)
def generate_flashcards(
    document_id: uuid.UUID,
    data: FlashcardGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return flashcard_service.generate_flashcards(
        db, current_user, document_id, count=data.count, difficulty=data.difficulty
    )


@router.get(
    "/documents/{document_id}/flashcards", response_model=list[FlashcardResponse]
)
def list_flashcards(
    document_id: uuid.UUID,
    known: bool | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(StudyDocument)
        .filter(StudyDocument.id == document_id, StudyDocument.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise NotFoundError("StudyDocument not found")
    query = db.query(Flashcard).filter(
        Flashcard.document_id == doc.id, Flashcard.user_id == current_user.id
    )
    if known is not None:
        query = query.filter(Flashcard.known == known)
    # Unknown cards first (simple spaced repetition: what you don't know
    # resurfaces first), then oldest first within each group.
    return query.order_by(Flashcard.known, Flashcard.created_at).all()


@router.patch("/flashcards/{flashcard_id}/review", response_model=FlashcardResponse)
def review_flashcard(
    flashcard_id: uuid.UUID,
    data: FlashcardReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return flashcard_service.review_flashcard(db, current_user, flashcard_id, data.known)
