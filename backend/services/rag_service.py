"""Retrieval-Augmented Generation: answer questions grounded in the user's PDFs."""

import uuid

from sqlalchemy.orm import Session

from core import chroma as chroma_client
from core import gemini
from core.exceptions import NotFoundError
from models.chat_message import ChatMessage, ChatRole
from models.study_document import StudyDocument
from models.user import User
from schemas.chat import ChatResponse, ChatSource

SYSTEM_PROMPT = (
    "You are a helpful study assistant. Answer the student's question using ONLY "
    "the context below, which comes from their uploaded study material. "
    "If the answer is not in the context, say so honestly and do not guess. "
    "Keep answers clear and concise, and use simple language."
)


def answer_question(
    db: Session, user: User, question: str, document_id: uuid.UUID | None
) -> ChatResponse:
    if document_id:
        doc = (
            db.query(StudyDocument)
            .filter(StudyDocument.id == document_id, StudyDocument.user_id == user.id)
            .first()
        )
        if not doc:
            raise NotFoundError("StudyDocument not found")

    query_embedding = gemini.embed_query(question)
    results = chroma_client.query_chunks(
        query_embedding, user_id=user.id, document_id=document_id, top_k=5
    )

    if not results:
        # Nothing relevant stored: answer deterministically instead of
        # spending a Gemini call on an empty context.
        answer = (
            "I couldn't find anything about that in your documents. "
            "Try rephrasing the question, or upload material that covers this topic."
        )
        sources = []
    else:
        context = "\n\n---\n\n".join(f"[Page {r['page']}] {r['text']}" for r in results)
        prompt = f"Context from the student's documents:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        answer = gemini.generate_text(prompt, system_instruction=SYSTEM_PROMPT, temperature=0.2)
        sources = [ChatSource(page=r["page"], excerpt=r["text"][:200]) for r in results]

    db.add(
        ChatMessage(
            user_id=user.id, document_id=document_id, role=ChatRole.USER, content=question
        )
    )
    db.add(
        ChatMessage(
            user_id=user.id,
            document_id=document_id,
            role=ChatRole.ASSISTANT,
            content=answer,
        )
    )
    db.commit()
    return ChatResponse(answer=answer, sources=sources, document_id=document_id)


def get_chat_history(
    db: Session, user: User, document_id: uuid.UUID | None, limit: int = 50
) -> list[ChatMessage]:
    query = db.query(ChatMessage).filter(ChatMessage.user_id == user.id)
    if document_id:
        query = query.filter(ChatMessage.document_id == document_id)
    # Newest first from the DB, then reversed so the client sees chronological order.
    return query.order_by(ChatMessage.created_at.desc()).limit(limit).all()[::-1]
