import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class TaskItem(BaseModel):
    date: str  # YYYY-MM-DD
    topic: str
    document_id: str | None = None
    minutes: int
    done: bool = False


class WeeklyGoal(BaseModel):
    week: int
    goal: str
    start_date: str | None = None  # YYYY-MM-DD
    end_date: str | None = None  # YYYY-MM-DD


class RevisionItem(BaseModel):
    date: str  # YYYY-MM-DD
    topic: str
    minutes: int


class StudyPlanCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    goal: str = Field(min_length=1, max_length=2000)
    exam_date: date | None = None
    daily_minutes: int = Field(default=30, ge=5, le=480)
    document_ids: list[uuid.UUID] = []


class StudyPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    goal: str
    exam_date: date | None
    daily_minutes: int
    tasks: list[TaskItem]
    weekly_goals: list[WeeklyGoal]
    revision_schedule: list[RevisionItem]
    is_active: bool
    created_at: datetime


class TaskUpdate(BaseModel):
    done: bool
