from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.v1.deps import get_current_user
from database.session import get_db
from models.user import User
from schemas.progress import (
    ActivityPoint,
    SessionCreate,
    SessionResponse,
    StatsResponse,
)
from services import progress_service

router = APIRouter(prefix="/progress", tags=["progress"])


@router.post("/sessions", response_model=SessionResponse, status_code=201)
def log_session(
    data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return progress_service.log_session(db, current_user, data)


@router.get("/stats", response_model=StatsResponse)
def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return progress_service.get_stats(db, current_user)


@router.get("/activity", response_model=list[ActivityPoint])
def get_activity(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return progress_service.get_activity(db, current_user, days=days)
