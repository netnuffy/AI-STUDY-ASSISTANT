"""Regression tests for the Postgres enum bug (found live 2026-11-23).

SQLAlchemy's Enum type persists member NAMES ("UPLOADING") by default, but
migration 0001 created the Postgres enum types with the lowercase VALUES
("uploading"). On Postgres every INSERT into documents, flashcards,
study_sessions and chat_messages failed with
``psycopg.errors.InvalidTextRepresentation: invalid input value for enum``.

SQLite tests cannot catch this because SQLite has no real enums, so these
tests check the values the columns actually bind when compiled against the
PostgreSQL dialect.
"""

import pytest
from sqlalchemy.dialects import postgresql

from models.chat_message import ChatMessage, ChatRole
from models.flashcard import Difficulty, Flashcard
from models.progress import ActivityType, StudySession
from models.study_document import DocumentStatus, StudyDocument

DIALECT = postgresql.dialect()


def bound_value(column, member):
    processor = column.type.bind_processor(DIALECT)
    assert processor is not None, f"no bind processor for {column}"
    return processor(member)


@pytest.mark.parametrize(
    ("column", "member", "expected"),
    [
        (StudyDocument.__table__.c.status, DocumentStatus.UPLOADING, "uploading"),
        (StudyDocument.__table__.c.status, DocumentStatus.PROCESSING, "processing"),
        (StudyDocument.__table__.c.status, DocumentStatus.READY, "ready"),
        (StudyDocument.__table__.c.status, DocumentStatus.FAILED, "failed"),
        (Flashcard.__table__.c.difficulty, Difficulty.EASY, "easy"),
        (Flashcard.__table__.c.difficulty, Difficulty.MEDIUM, "medium"),
        (Flashcard.__table__.c.difficulty, Difficulty.HARD, "hard"),
        (StudySession.__table__.c.activity_type, ActivityType.READING, "reading"),
        (StudySession.__table__.c.activity_type, ActivityType.CHAT, "chat"),
        (StudySession.__table__.c.activity_type, ActivityType.FLASHCARDS, "flashcards"),
        (StudySession.__table__.c.activity_type, ActivityType.QUIZ, "quiz"),
        (ChatMessage.__table__.c.role, ChatRole.USER, "user"),
        (ChatMessage.__table__.c.role, ChatRole.ASSISTANT, "assistant"),
    ],
)
def test_enum_columns_bind_lowercase_values(column, member, expected):
    assert bound_value(column, member) == expected
