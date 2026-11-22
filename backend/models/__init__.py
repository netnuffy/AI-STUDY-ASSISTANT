"""Importing this package registers every model with Base.metadata."""

from models.chat_message import ChatMessage, ChatRole
from models.study_document import StudyDocument, DocumentStatus
from models.flashcard import Difficulty, Flashcard
from models.progress import ActivityType, StudySession
from models.quiz import Quiz, QuizAttempt
from models.study_plan import StudyPlan
from models.summary import Summary
from models.user import User

__all__ = [
    "ActivityType",
    "ChatMessage",
    "ChatRole",
    "Difficulty",
    "StudyDocument",
    "DocumentStatus",
    "Flashcard",
    "Quiz",
    "QuizAttempt",
    "StudyPlan",
    "StudySession",
    "Summary",
    "User",
]
