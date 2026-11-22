"""Seed demo data for a local preview: one user with documents, a summary,
flashcards, a quiz + attempt, study sessions, and a study plan.

Usage (from the backend directory, with the tables already created):

    DATABASE_URL="sqlite:////tmp/preview.db" python seed_demo.py

Demo login: demo@demo.com / demo1234

Safe to re-run: if the demo user already exists, nothing is seeded.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

from database.session import SessionLocal
from models.chat_message import ChatMessage, ChatRole
from models.flashcard import Difficulty, Flashcard
from models.progress import ActivityType, StudySession
from models.quiz import Quiz, QuizAttempt
from models.study_document import DocumentStatus, StudyDocument
from models.study_plan import StudyPlan
from models.summary import Summary
from models.user import User

DEMO_EMAIL = "demo@demo.com"


def main() -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if user is None:
            print(f"No user {DEMO_EMAIL} — register it first, then re-run.")
            return
        if db.query(StudyDocument).filter(StudyDocument.user_id == user.id).first():
            print("Demo data already seeded.")
            return

        today = date.today()
        now = datetime.now(timezone.utc)

        bio = StudyDocument(
            user_id=user.id,
            title="Biology Notes",
            filename="biology-notes.pdf",
            file_path="./uploads/demo-biology.pdf",
            file_size_bytes=245_760,
            page_count=12,
            status=DocumentStatus.READY,
        )
        chem = StudyDocument(
            user_id=user.id,
            title="Chemistry Basics",
            filename="chemistry-basics.pdf",
            file_path="./uploads/demo-chemistry.pdf",
            file_size_bytes=180_224,
            page_count=8,
            status=DocumentStatus.READY,
        )
        db.add_all([bio, chem])
        db.flush()

        db.add(
            Summary(
                document_id=bio.id,
                content=(
                    "These notes cover cell biology: the structure and function "
                    "of the cell, mitochondria as the powerhouse of the cell, "
                    "and how photosynthesis converts light into chemical energy. "
                    "The key idea is that every living process comes back to "
                    "energy transfer inside the cell."
                ),
                key_points=[
                    "The cell is the basic unit of life",
                    "Mitochondria produce ATP through respiration",
                    "Photosynthesis stores light energy as glucose",
                ],
                key_concepts=[
                    {"term": "Mitochondria", "definition": "Organelle that produces ATP"},
                    {"term": "Photosynthesis", "definition": "Process converting light to chemical energy"},
                ],
                important_questions=[
                    "What is the function of mitochondria?",
                    "How does photosynthesis store energy?",
                ],
            )
        )

        cards = [
            ("What is the powerhouse of the cell?", "Mitochondria", "easy", True),
            ("What does photosynthesis produce?", "Glucose and oxygen", "easy", True),
            ("Which organelle contains DNA?", "The nucleus (and mitochondria)", "medium", False),
            ("What is ATP?", "The cell's main energy currency", "medium", False),
        ]
        for front, back, difficulty, known in cards:
            db.add(
                Flashcard(
                    document_id=bio.id,
                    user_id=user.id,
                    front=front,
                    back=back,
                    difficulty=Difficulty(difficulty),
                    known=known,
                    review_count=1 if known else 0,
                )
            )

        quiz = Quiz(
            document_id=bio.id,
            user_id=user.id,
            title="Biology Notes — Quiz 1",
            questions=[
                {
                    "type": "multiple_choice",
                    "question": "Which organelle produces ATP?",
                    "options": ["Nucleus", "Mitochondria", "Ribosome", "Golgi body"],
                    "correct_index": 1,
                    "explanation": "Mitochondria generate ATP through cellular respiration.",
                },
                {
                    "type": "true_false",
                    "question": "Photosynthesis takes place in the mitochondria.",
                    "correct": False,
                    "explanation": "Photosynthesis takes place in chloroplasts.",
                },
                {
                    "type": "short_answer",
                    "question": "What is the powerhouse of the cell?",
                    "answer": "Mitochondria",
                    "explanation": "Mitochondria are called the powerhouse of the cell.",
                },
            ],
        )
        db.add(quiz)
        db.flush()
        db.add(
            QuizAttempt(
                quiz_id=quiz.id,
                user_id=user.id,
                score=2,
                total=3,
                answers=[1, 1, "Mitochondria"],
                completed_at=now - timedelta(hours=2),
            )
        )

        # Study sessions for the last 5 days (streak + activity chart).
        for days_ago, minutes, activity in [
            (4, 25, ActivityType.READING),
            (3, 40, ActivityType.FLASHCARDS),
            (2, 30, ActivityType.CHAT),
            (1, 45, ActivityType.QUIZ),
            (0, 20, ActivityType.READING),
        ]:
            db.add(
                StudySession(
                    user_id=user.id,
                    document_id=bio.id,
                    activity_type=activity,
                    duration_minutes=minutes,
                    date=today - timedelta(days=days_ago),
                )
            )

        db.add(
            StudyPlan(
                user_id=user.id,
                title="Biology",
                goal="Score 85%+ in the biology final",
                exam_date=today + timedelta(days=14),
                daily_minutes=45,
                tasks=[
                    {"date": str(today), "topic": "Cell structure", "document_id": str(bio.id), "minutes": 45, "done": True},
                    {"date": str(today + timedelta(days=1)), "topic": "Photosynthesis", "document_id": str(bio.id), "minutes": 45, "done": False},
                    {"date": str(today + timedelta(days=2)), "topic": "Cell respiration", "document_id": str(bio.id), "minutes": 45, "done": False},
                ],
                weekly_goals=[
                    {"week": 1, "goal": "Finish cell biology chapters", "start_date": str(today), "end_date": str(today + timedelta(days=6))},
                    {"week": 2, "goal": "Revise + take 3 practice quizzes", "start_date": str(today + timedelta(days=7)), "end_date": str(today + timedelta(days=13))},
                ],
                revision_schedule=[
                    {"date": str(today + timedelta(days=3)), "topic": "Cell structure revision", "minutes": 20},
                    {"date": str(today + timedelta(days=6)), "topic": "Full chapter revision", "minutes": 30},
                ],
                is_active=True,
            )
        )

        db.add(
            ChatMessage(
                user_id=user.id,
                document_id=bio.id,
                role=ChatRole.USER,
                content="What is the function of mitochondria?",
            )
        )
        db.add(
            ChatMessage(
                user_id=user.id,
                document_id=bio.id,
                role=ChatRole.ASSISTANT,
                content="Mitochondria produce ATP, the cell's main energy currency, through cellular respiration. (p. 4)",
            )
        )

        db.commit()
        print(f"Seeded demo data for {DEMO_EMAIL}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
