"""Study plan generation (Gemini) and task tracking."""

import uuid
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from core import gemini
from core.exceptions import BadRequestError, NotFoundError
from models.study_document import StudyDocument
from models.study_plan import StudyPlan
from models.user import User
from schemas.study_plan import StudyPlanCreate


def _valid_date(value) -> str | None:
    """Return the value if it's a valid YYYY-MM-DD date string, else None."""
    if not isinstance(value, str):
        return None
    try:
        datetime.strptime(value.strip(), "%Y-%m-%d")
    except ValueError:
        return None
    return value.strip()


def _valid_minutes(value, default: int) -> int:
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return default
    return minutes if minutes > 0 else default


def _normalise_tasks(items, doc_ids: set[str], daily_minutes: int) -> list[dict]:
    """Validate daily tasks: real dates, non-empty topics, sane minutes,
    document_id must be one of the selected docs (else None). Sorted by
    date, deduplicated by date."""
    tasks = []
    seen_dates = set()
    if not isinstance(items, list):
        return tasks
    for item in items:
        if not isinstance(item, dict):
            continue
        day = _valid_date(item.get("date"))
        topic = str(item.get("topic", "")).strip()
        if not day or not topic or day in seen_dates:
            continue
        seen_dates.add(day)
        doc_id = item.get("document_id")
        doc_id = str(doc_id) if doc_id and str(doc_id) in doc_ids else None
        tasks.append(
            {
                "date": day,
                "topic": topic,
                "document_id": doc_id,
                "minutes": _valid_minutes(item.get("minutes"), daily_minutes),
                "done": False,
            }
        )
    return sorted(tasks, key=lambda t: t["date"])


def _normalise_weekly_goals(items) -> list[dict]:
    goals = []
    if not isinstance(items, list):
        return goals
    for item in items:
        if not isinstance(item, dict):
            continue
        goal = str(item.get("goal", "")).strip()
        if not goal:
            continue
        try:
            week = int(item.get("week", len(goals) + 1))
        except (TypeError, ValueError):
            week = len(goals) + 1
        goals.append(
            {
                "week": week,
                "goal": goal,
                "start_date": _valid_date(item.get("start_date")),
                "end_date": _valid_date(item.get("end_date")),
            }
        )
    return sorted(goals, key=lambda g: g["week"])


def _normalise_revision_schedule(items, daily_minutes: int) -> list[dict]:
    sessions = []
    if not isinstance(items, list):
        return sessions
    for item in items:
        if not isinstance(item, dict):
            continue
        day = _valid_date(item.get("date"))
        topic = str(item.get("topic", "")).strip()
        if not day or not topic:
            continue
        sessions.append(
            {
                "date": day,
                "topic": topic,
                "minutes": _valid_minutes(item.get("minutes"), daily_minutes),
            }
        )
    return sorted(sessions, key=lambda s: s["date"])


def generate_study_plan(db: Session, user: User, data: StudyPlanCreate) -> StudyPlan:
    if data.exam_date and data.exam_date < date.today():
        raise BadRequestError("Exam date must be in the future")
    docs: list[StudyDocument] = []
    if data.document_ids:
        docs = (
            db.query(StudyDocument)
            .filter(
                StudyDocument.id.in_(data.document_ids), StudyDocument.user_id == user.id
            )
            .all()
        )
        if len(docs) != len(data.document_ids):
            raise NotFoundError("One or more documents were not found")

    end = data.exam_date or (date.today() + timedelta(days=14))
    days = max((end - date.today()).days, 1)
    doc_ids = {str(d.id) for d in docs}
    doc_list = "\n".join(
        f"- {d.title} (id: {d.id}, {d.page_count or '?'} pages)" for d in docs
    ) or "- No specific documents selected"

    prompt = (
        f"Create a {days}-day study plan. Goal: {data.goal}. "
        f"The student can study {data.daily_minutes} minutes per day. "
        f"Start date: {date.today().isoformat()}. Exam date: {end.isoformat()}.\n"
        f"Study material:\n{doc_list}\n\n"
        "Return a JSON object with exactly these keys:\n"
        "- tasks: one object per day — date (YYYY-MM-DD), topic, minutes, "
        "document_id (one of the document IDs above, or null). Spread the "
        "topics evenly across the days.\n"
        "- weekly_goals: one object per week — week (1, 2, ...), goal, "
        "start_date, end_date. Each week's goal should say what the student "
        "will have mastered by the end of that week.\n"
        "- revision_schedule: spaced revision sessions — date, topic, minutes. "
        "Schedule revision of earlier topics in later weeks, and a full "
        "revision in the last 2 days before the exam."
    )
    result = gemini.generate_json(
        prompt, system_instruction="You are a study planning expert."
    )
    if isinstance(result, list):
        # Old shape: a bare array of tasks.
        result = {"tasks": result}
    if not isinstance(result, dict):
        result = {}
    tasks = _normalise_tasks(result.get("tasks"), doc_ids, data.daily_minutes)
    if not tasks:
        raise BadRequestError(
            "Could not generate a valid study plan from this input. "
            "Please try again."
        )
    plan = StudyPlan(
        user_id=user.id,
        title=data.title,
        goal=data.goal,
        exam_date=data.exam_date,
        daily_minutes=data.daily_minutes,
        tasks=tasks,
        weekly_goals=_normalise_weekly_goals(result.get("weekly_goals")),
        revision_schedule=_normalise_revision_schedule(
            result.get("revision_schedule"), data.daily_minutes
        ),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def update_task(
    db: Session, user: User, plan_id: uuid.UUID, task_index: int, done: bool
) -> StudyPlan:
    plan = (
        db.query(StudyPlan)
        .filter(StudyPlan.id == plan_id, StudyPlan.user_id == user.id)
        .first()
    )
    if not plan:
        raise NotFoundError("Study plan not found")
    if task_index < 0 or task_index >= len(plan.tasks):
        raise NotFoundError("Task not found")
    tasks = list(plan.tasks)
    tasks[task_index] = {**tasks[task_index], "done": done}
    plan.tasks = tasks  # reassign so SQLAlchemy tracks the change
    db.commit()
    db.refresh(plan)
    return plan
