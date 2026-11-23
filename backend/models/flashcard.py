import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin


class Difficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Flashcard(Base, TimestampMixin):
    __tablename__ = "flashcards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    # values_callable: persist lowercase enum VALUES ("easy"), not member
    # NAMES ("EASY") — the Postgres enum type only accepts the values.
    difficulty: Mapped[Difficulty] = mapped_column(
        SAEnum(Difficulty, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=Difficulty.MEDIUM,
    )
    known: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    document: Mapped["StudyDocument"] = relationship(back_populates="flashcards")
    user: Mapped["User"] = relationship(back_populates="flashcards")
