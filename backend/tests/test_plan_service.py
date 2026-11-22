"""Study plan service tests with a mocked Gemini client."""

import uuid
from datetime import date, timedelta

import pytest

from core.exceptions import BadRequestError, NotFoundError
from models.study_document import DocumentStatus, StudyDocument
from models.study_plan import StudyPlan
from models.user import User
from schemas.study_plan import StudyPlanCreate
from services import plan_service
from tests.conftest import TestingSessionLocal


@pytest.fixture()
def user_and_doc():
    db = TestingSessionLocal()
    user = User(
        email=f"sp-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Plan Tester",
        hashed_password="hashed",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    doc = StudyDocument(
        user_id=user.id,
        title="biology.pdf",
        filename="biology.pdf",
        file_path="/tmp/biology.pdf",
        file_size_bytes=1234,
        status=DocumentStatus.READY,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    yield db, user, doc
    db.close()


def _create_data(doc, **overrides):
    data = {
        "title": "Biology Final",
        "goal": "Pass the biology final",
        "exam_date": date.today() + timedelta(days=14),
        "daily_minutes": 60,
        "document_ids": [doc.id],
    }
    data.update(overrides)
    return StudyPlanCreate(**data)


def _mock_gemini(monkeypatch, result):
    monkeypatch.setattr(
        "services.plan_service.gemini.generate_json",
        lambda *a, **k: result,
    )


def _insert_plan(db, user, tasks):
    plan = StudyPlan(
        user_id=user.id,
        title="Plan",
        goal="Goal",
        exam_date=None,
        daily_minutes=30,
        tasks=tasks,
        weekly_goals=[],
        revision_schedule=[],
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def test_generate_study_plan_creates_all_three_outputs(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    today = date.today()
    _mock_gemini(
        monkeypatch,
        {
            # Deliberately out of order: tasks must come back sorted by date,
            # goals sorted by week.
            "tasks": [
                {
                    "date": (today + timedelta(days=1)).isoformat(),
                    "topic": "Cell biology",
                    "minutes": 60,
                    "document_id": str(doc.id),
                },
                {
                    "date": today.isoformat(),
                    "topic": "Intro + syllabus",
                    "minutes": 30,
                    "document_id": None,
                },
            ],
            "weekly_goals": [
                {"week": 2, "goal": "Master genetics"},
                {"week": 1, "goal": "Master cell biology"},
            ],
            "revision_schedule": [
                {
                    "date": (today + timedelta(days=13)).isoformat(),
                    "topic": "Full revision",
                    "minutes": 60,
                },
            ],
        },
    )
    plan = plan_service.generate_study_plan(db, user, _create_data(doc))
    assert plan.title == "Biology Final"
    assert plan.daily_minutes == 60
    assert [t["date"] for t in plan.tasks] == [
        today.isoformat(),
        (today + timedelta(days=1)).isoformat(),
    ]
    assert all(t["done"] is False for t in plan.tasks)
    assert plan.tasks[1]["document_id"] == str(doc.id)
    assert [g["week"] for g in plan.weekly_goals] == [1, 2]
    assert plan.weekly_goals[0]["goal"] == "Master cell biology"
    assert len(plan.revision_schedule) == 1
    assert plan.revision_schedule[0]["topic"] == "Full revision"


def test_generate_study_plan_handles_bare_array(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    today = date.today()
    _mock_gemini(
        monkeypatch,
        [
            {
                "date": today.isoformat(),
                "topic": "Only task",
                "minutes": 30,
            }
        ],
    )
    plan = plan_service.generate_study_plan(db, user, _create_data(doc))
    assert len(plan.tasks) == 1
    assert plan.weekly_goals == []
    assert plan.revision_schedule == []


def test_generate_study_plan_handles_garbage_response(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    _mock_gemini(monkeypatch, "not json at all")
    with pytest.raises(BadRequestError, match="Could not generate"):
        plan_service.generate_study_plan(db, user, _create_data(doc))


def test_generate_study_plan_skips_invalid_tasks(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    today = date.today()
    _mock_gemini(
        monkeypatch,
        {
            "tasks": [
                {"date": "2026-13-40", "topic": "Bad date", "minutes": 30},
                {"date": today.isoformat(), "topic": "", "minutes": 30},
                {
                    "date": (today + timedelta(days=1)).isoformat(),
                    "topic": "Bad minutes",
                    "minutes": "abc",
                },
                {
                    "date": (today + timedelta(days=2)).isoformat(),
                    "topic": "Hallucinated doc",
                    "minutes": 30,
                    "document_id": str(uuid.uuid4()),
                },
                {
                    "date": (today + timedelta(days=2)).isoformat(),
                    "topic": "Duplicate date",
                    "minutes": 30,
                },
                {
                    "date": (today + timedelta(days=3)).isoformat(),
                    "topic": "Good task",
                    "minutes": 45,
                    "document_id": str(doc.id),
                },
                "not a dict",
            ]
        },
    )
    plan = plan_service.generate_study_plan(db, user, _create_data(doc))
    assert [t["topic"] for t in plan.tasks] == [
        "Bad minutes",
        "Hallucinated doc",
        "Good task",
    ]
    assert plan.tasks[0]["minutes"] == 60  # invalid minutes → daily default
    assert plan.tasks[1]["document_id"] is None  # unknown doc → null
    assert plan.tasks[2]["document_id"] == str(doc.id)


def test_generate_study_plan_past_exam_date(user_and_doc):
    db, user, doc = user_and_doc
    with pytest.raises(BadRequestError, match="in the future"):
        plan_service.generate_study_plan(
            db,
            user,
            _create_data(doc, exam_date=date.today() - timedelta(days=1)),
        )


def test_generate_study_plan_no_exam_date_defaults_14_days(
    user_and_doc, monkeypatch
):
    db, user, doc = user_and_doc
    today = date.today()
    seen = {}

    def capture(prompt, system_instruction=None, temperature=0.3):
        seen["prompt"] = prompt
        return [
            {"date": today.isoformat(), "topic": "Task", "minutes": 30},
        ]

    monkeypatch.setattr("services.plan_service.gemini.generate_json", capture)
    plan = plan_service.generate_study_plan(
        db, user, _create_data(doc, exam_date=None)
    )
    assert (today + timedelta(days=14)).isoformat() in seen["prompt"]
    assert plan.exam_date is None


def test_generate_study_plan_document_not_found(user_and_doc):
    db, user, doc = user_and_doc
    with pytest.raises(NotFoundError):
        plan_service.generate_study_plan(
            db, user, _create_data(doc, document_ids=[uuid.uuid4()])
        )


def test_generate_study_plan_no_valid_tasks(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    _mock_gemini(
        monkeypatch,
        {"tasks": [{"date": "not-a-date", "topic": "Bad", "minutes": 30}]},
    )
    with pytest.raises(BadRequestError, match="Could not generate"):
        plan_service.generate_study_plan(db, user, _create_data(doc))


def test_update_task_marks_done(user_and_doc):
    db, user, _ = user_and_doc
    plan = _insert_plan(
        db,
        user,
        [
            {"date": "2026-11-23", "topic": "A", "minutes": 30, "done": False},
            {"date": "2026-11-24", "topic": "B", "minutes": 30, "done": False},
        ],
    )
    updated = plan_service.update_task(db, user, plan.id, 0, True)
    assert updated.tasks[0]["done"] is True
    assert updated.tasks[1]["done"] is False


def test_update_task_out_of_range(user_and_doc):
    db, user, _ = user_and_doc
    plan = _insert_plan(
        db, user, [{"date": "2026-11-23", "topic": "A", "minutes": 30, "done": False}]
    )
    for bad_index in (1, -1):
        with pytest.raises(NotFoundError):
            plan_service.update_task(db, user, plan.id, bad_index, True)


def test_update_task_other_users_plan(user_and_doc):
    db, user, _ = user_and_doc
    other = User(
        email=f"sp-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Other",
        hashed_password="x",
    )
    db.add(other)
    db.commit()
    db.refresh(other)
    plan = _insert_plan(
        db,
        other,
        [{"date": "2026-11-23", "topic": "A", "minutes": 30, "done": False}],
    )
    with pytest.raises(NotFoundError):
        plan_service.update_task(db, user, plan.id, 0, True)
