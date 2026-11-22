import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.study_document import DocumentStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    filename: str
    file_size_bytes: int
    page_count: int | None
    status: DocumentStatus
    error_message: str | None = None
    created_at: datetime
