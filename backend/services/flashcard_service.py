"""Flashcard generation (Gemini) and review tracking (spaced repetition)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core import gemini
from core.exceptions import BadRequestError, NotFoundError
from models.study_document import StudyDocument
from models.flashcard import Difficulty, Flashcard
from models.user import User
from services.embedding_service import get_document_text


def generate_flashcards(
    db: Session,
    user: User,
    document_id: uuid.UUID,
    count: int = 10,
    difficulty: str | None = None,
) -> list[Flashcard]:
    doc = (
        db.query(StudyDocument)
        .filter(StudyDocument.id == document_id, StudyDocument.user_id == user.id)
        .first()
    )
    if not doc:
        raise NotFoundError("StudyDocument not found")
    text = get_document_text(user.id, document_id)
    if not text.strip():
        raise BadRequestError("This document has no processed text yet")

    difficulty_note = (
        f"All flashcards should be {difficulty} difficulty."
        if difficulty
        else "Mix easy, medium and hard flashcards."
    )
    prompt = (
        f"Create {count} flashcards from the study material below. {difficulty_note}\n"
        "Return a JSON array of objects with keys: front, back, "
        "difficulty (easy/medium/hard).\n\n"
        f"Material:\n{text}"
    )
    items = gemini.generate_json(
        prompt, system_instruction="You create high-quality study flashcards."
    )
    if isinstance(items, dict):
        items = items.get("flashcards", [])
    if not isinstance(items, list):
        items = []

    # Skip cards the user already has for this document (regeneration guard).
    existing_fronts = {
        row[0].strip().lower()
        for row in db.query(Flashcard.front)
        .filter(Flashcard.document_id == doc.id, Flashcard.user_id == user.id)
        .all()
    }

    flashcards: list[Flashcard] = []
    seen_fronts = set(existing_fronts)
    for item in items:
        if len(flashcards) >= count:
            break
        if not isinstance(item, dict):
            continue
        front = str(item.get("front", "")).strip()
        back = str(item.get("back", "")).strip()
        if not front or not back:
            continue
        if front.lower() in seen_fronts:
            continue
        seen_fronts.add(front.lower())
        difficulty = str(item.get("difficulty", "medium")).strip().lower()
        if difficulty not in ("easy", "medium", "hard"):
            difficulty = "medium"
        card = Flashcard(
            document_id=doc.id,
            user_id=user.id,
            front=front,
            back=back,
            difficulty=Difficulty(difficulty),
        )
        db.add(card)
        flashcards.append(card)
    db.commit()
    for card in flashcards:
        db.refresh(card)
    return flashcards


def review_flashcard(
    db: Session, user: User, flashcard_id: uuid.UUID, known: bool
) -> Flashcard:
    card = (
        db.query(Flashcard)
        .filter(Flashcard.id == flashcard_id, Flashcard.user_id == user.id)
        .first()
    )
    if not card:
        raise NotFoundError("Flashcard not found")
    card.known = known
    card.review_count += 1
    card.last_reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(card)
    return card
