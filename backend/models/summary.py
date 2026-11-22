import uuid

from sqlalchemy import JSON, ForeignKey, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin


class Summary(Base, TimestampMixin):
    __tablename__ = "summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # List of {term, definition}
    key_concepts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # List of exam-style question strings
    important_questions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    document: Mapped["StudyDocument"] = relationship(back_populates="summary")
