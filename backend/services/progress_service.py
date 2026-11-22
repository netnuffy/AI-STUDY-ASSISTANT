"""Progress tracking: study sessions, streaks, stats and activity charts."""

from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.study_document import StudyDocument
from models.flashcard import Flashcard
from models.progress import ActivityType, StudySession
from models.quiz import QuizAttempt
from models.user import User
from schemas.progress import ActivityPoint, SessionCreate, StatsResponse


def log_session(db: Session, user: User, data: SessionCreate) -> StudySession:
    session = StudySession(
        user_id=user.id,
        document_id=data.document_id,
        activity_type=ActivityType(data.activity_type),
        duration_minutes=data.duration_minutes,
        date=data.date or date.today(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _calculate_streak(db: Session, user_id) -> int:
    dates = [
        row[0]
        for row in db.query(StudySession.date)
        .filter(StudySession.user_id == user_id)
        .distinct()
        .order_by(StudySession.date.desc())
        .all()
    ]
    if not dates:
        return 0
    date_set = set(dates)
    today = date.today()
    # A streak counts as alive if the user studied today or yesterday.
    current = today if today in date_set else today - timedelta(days=1)
    streak = 0
    while current in date_set:
        streak += 1
        current -= timedelta(days=1)
    return streak


def get_stats(db: Session, user: User) -> StatsResponse:
    total_minutes = (
        db.query(func.coalesce(func.sum(StudySession.duration_minutes), 0))
        .filter(StudySession.user_id == user.id)
        .scalar()
        or 0
    )
    total_documents = (
        db.query(func.count(StudyDocument.id)).filter(StudyDocument.user_id == user.id).scalar()
        or 0
    )
    attempts = db.query(QuizAttempt).filter(QuizAttempt.user_id == user.id).all()
    average_quiz_score = None
    if attempts:
        average_quiz_score = round(
            sum(a.score / a.total for a in attempts if a.total) / len(attempts) * 100, 1
        )
    flashcards_total = (
        db.query(func.count(Flashcard.id))
        .filter(Flashcard.user_id == user.id)
        .scalar()
        or 0
    )
    flashcards_known = (
        db.query(func.count(Flashcard.id))
        .filter(Flashcard.user_id == user.id, Flashcard.known.is_(True))
        .scalar()
        or 0
    )
    return StatsResponse(
        total_minutes=int(total_minutes),
        streak_days=_calculate_streak(db, user.id),
        total_documents=int(total_documents),
        total_quizzes_taken=len(attempts),
        average_quiz_score=average_quiz_score,
        flashcards_known=int(flashcards_known),
        flashcards_total=int(flashcards_total),
    )


def get_activity(db: Session, user: User, days: int = 30) -> list[ActivityPoint]:
    since = date.today() - timedelta(days=days - 1)
    rows = (
        db.query(StudySession.date, func.sum(StudySession.duration_minutes))
        .filter(StudySession.user_id == user.id, StudySession.date >= since)
        .group_by(StudySession.date)
        .order_by(StudySession.date)
        .all()
    )
    by_date = {row[0]: int(row[1]) for row in rows}
    return [
        ActivityPoint(
            date=since + timedelta(days=i),
            minutes=by_date.get(since + timedelta(days=i), 0),
        )
        for i in range(days)
    ]
