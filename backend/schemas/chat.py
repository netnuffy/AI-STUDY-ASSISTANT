import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    document_id: uuid.UUID | None = None


class ChatSource(BaseModel):
    page: int | None
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
    document_id: uuid.UUID | None


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    document_id: uuid.UUID | None
    created_at: datetime
