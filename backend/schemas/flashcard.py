import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FlashcardGenerateRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=50)
    difficulty: str | None = Field(default=None, pattern="^(easy|medium|hard)$")


class FlashcardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    front: str
    back: str
    difficulty: str
    known: bool
    review_count: int
    last_reviewed_at: datetime | None


class FlashcardReviewRequest(BaseModel):
    known: bool
