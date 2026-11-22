"""Aggregates all v1 routers. Mounted at /api/v1 in the app factory."""

from fastapi import APIRouter

from api.v1 import (
    auth,
    chat,
    documents,
    flashcards,
    progress,
    quizzes,
    study_plans,
    summaries,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(summaries.router)
api_router.include_router(summaries.recent_router)
api_router.include_router(chat.router)
api_router.include_router(flashcards.router)
api_router.include_router(quizzes.router)
api_router.include_router(study_plans.router)
api_router.include_router(progress.router)
