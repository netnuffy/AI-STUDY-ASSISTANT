import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

QuestionType = Literal["multiple_choice", "true_false", "short_answer"]


class QuizGenerateRequest(BaseModel):
    num_questions: int = Field(default=10, ge=1, le=20)
    difficulty: str | None = Field(default=None, pattern="^(easy|medium|hard)$")
    title: str | None = None
    # None = mix all three types.
    question_types: list[QuestionType] | None = None


class QuizQuestionPublic(BaseModel):
    type: str
    question: str
    # 4 options for multiple-choice, ["True", "False"] for true/false,
    # None for short answer (free-text input).
    options: list[str] | None = None


class QuizResponse(BaseModel):
    """Quiz without answers (safe to send to the client)."""

    id: uuid.UUID
    document_id: uuid.UUID
    title: str
    questions: list[QuizQuestionPublic]
    created_at: datetime


class QuizSubmitRequest(BaseModel):
    # One answer per question, in order: int = selected option index
    # (multiple-choice / true-false), str = typed answer (short answer).
    answers: list[int | str]


class QuizResultItem(BaseModel):
    type: str
    question: str
    selected: int | str | None
    # MCQ / True-False: index of the correct option. Short answer: expected text.
    correct: int | str
    is_correct: bool
    explanation: str


class QuizSubmitResponse(BaseModel):
    score: int
    total: int
    results: list[QuizResultItem]


class QuizAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    score: int
    total: int
    answers: list[int | str]
    completed_at: datetime


class RecentAttemptResponse(BaseModel):
    """One quiz attempt with its quiz title, for the dashboard."""

    id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: str
    score: int
    total: int
    percentage: int
    completed_at: datetime
