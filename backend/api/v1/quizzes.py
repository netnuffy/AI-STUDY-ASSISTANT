import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.v1.deps import get_current_user
from core.exceptions import NotFoundError
from database.session import get_db
from models.quiz import Quiz, QuizAttempt
from models.user import User
from schemas.quiz import (
    QuizAttemptResponse,
    QuizGenerateRequest,
    QuizResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
    RecentAttemptResponse,
)
from services import quiz_service

router = APIRouter(tags=["quizzes"])


@router.get("/quizzes/attempts/recent", response_model=list[RecentAttemptResponse])
def recent_attempts(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The user's most recent quiz attempts across all quizzes, for the dashboard."""
    rows = (
        db.query(QuizAttempt, Quiz.title)
        .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
        .filter(QuizAttempt.user_id == current_user.id)
        .order_by(QuizAttempt.completed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        RecentAttemptResponse(
            id=a.id,
            quiz_id=a.quiz_id,
            quiz_title=title,
            score=a.score,
            total=a.total,
            percentage=round(a.score / a.total * 100) if a.total else 0,
            completed_at=a.completed_at,
        )
        for a, title in rows
    ]


@router.post(
    "/documents/{document_id}/quizzes/generate",
    response_model=QuizResponse,
    status_code=201,
)
def generate_quiz(
    document_id: uuid.UUID,
    data: QuizGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quiz = quiz_service.generate_quiz(
        db,
        current_user,
        document_id,
        num_questions=data.num_questions,
        difficulty=data.difficulty,
        title=data.title,
        question_types=data.question_types,
    )
    return quiz_service.to_public_quiz(quiz)


@router.get("/quizzes/{quiz_id}", response_model=QuizResponse)
def get_quiz(
    quiz_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quiz = (
        db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.user_id == current_user.id).first()
    )
    if not quiz:
        raise NotFoundError("Quiz not found")
    return quiz_service.to_public_quiz(quiz)


@router.post("/quizzes/{quiz_id}/submit", response_model=QuizSubmitResponse)
def submit_quiz(
    quiz_id: uuid.UUID,
    data: QuizSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return quiz_service.submit_quiz(db, current_user, quiz_id, data.answers)


@router.get("/quizzes/{quiz_id}/attempts", response_model=list[QuizAttemptResponse])
def list_attempts(
    quiz_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quiz = (
        db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.user_id == current_user.id).first()
    )
    if not quiz:
        raise NotFoundError("Quiz not found")
    return (
        db.query(QuizAttempt)
        .filter(QuizAttempt.quiz_id == quiz.id, QuizAttempt.user_id == current_user.id)
        .order_by(QuizAttempt.completed_at.desc())
        .all()
    )
