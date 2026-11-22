import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.v1.deps import get_current_user
from database.session import get_db
from models.user import User
from schemas.chat import ChatMessageResponse, ChatRequest, ChatResponse
from services import rag_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return rag_service.answer_question(db, current_user, data.question, data.document_id)


@router.get("/history", response_model=list[ChatMessageResponse])
def history(
    document_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return rag_service.get_chat_history(db, current_user, document_id, limit=limit)
