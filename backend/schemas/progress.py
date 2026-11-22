import uuid
from datetime import date as DateType

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    activity_type: str = Field(pattern="^(reading|chat|flashcards|quiz)$")
    duration_minutes: int = Field(ge=1, le=1440)
    document_id: uuid.UUID | None = None
    date: DateType | None = None


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    activity_type: str
    duration_minutes: int
    document_id: uuid.UUID | None
    date: DateType


class StatsResponse(BaseModel):
    total_minutes: int
    streak_days: int
    total_documents: int
    total_quizzes_taken: int
    average_quiz_score: float | None  # percentage 0-100
    flashcards_known: int
    flashcards_total: int


class ActivityPoint(BaseModel):
    date: DateType
    minutes: int
