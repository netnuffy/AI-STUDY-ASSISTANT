import enum
import uuid
from datetime import date as DateType

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Date, ForeignKey, Integer, UUID, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class ActivityType(str, enum.Enum):
    READING = "reading"
    CHAT = "chat"
    FLASHCARDS = "flashcards"
    QUIZ = "quiz"


class StudySession(Base):
    __tablename__ = "study_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    # values_callable: persist lowercase enum VALUES ("reading"), not member
    # NAMES ("READING") — the Postgres enum type only accepts the values.
    activity_type: Mapped[ActivityType] = mapped_column(
        SAEnum(ActivityType, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[DateType] = mapped_column(
        Date, server_default=func.current_date(), nullable=False, index=True
    )

    user: Mapped["User"] = relationship(back_populates="study_sessions")
    document: Mapped["StudyDocument | None"] = relationship(back_populates="study_sessions")
