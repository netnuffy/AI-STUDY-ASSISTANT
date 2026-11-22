"""Study plan API tests."""

import uuid
from datetime import datetime, timedelta, timezone

from models.study_plan import StudyPlan
from tests.conftest import TestingSessionLocal


def _user_id(client, auth_headers):
    me = client.get("/api/v1/auth/me", headers=auth_headers).json()
    return uuid.UUID(me["id"])


def _insert_plan(user_id, title="Plan", created_at=None):
    db = TestingSessionLocal()
    plan = StudyPlan(
        user_id=user_id,
        title=title,
        goal="Goal",
        exam_date=None,
        daily_minutes=60,
        tasks=[
            {
                "date": "2026-11-23",
                "topic": "Cells",
                "document_id": None,
                "minutes": 60,
                "done": False,
            },
            {
                "date": "2026-11-24",
                "topic": "Genetics",
                "document_id": None,
                "minutes": 60,
                "done": False,
            },
        ],
        weekly_goals=[
            {
                "week": 1,
                "goal": "Master cells",
                "start_date": "2026-11-23",
                "end_date": "2026-11-29",
            }
        ],
        revision_schedule=[
            {"date": "2026-12-05", "topic": "Full revision", "minutes": 60}
        ],
    )
    if created_at is not None:
        plan.created_at = created_at
    db.add(plan)
    db.commit()
    db.refresh(plan)
    db.close()
    return plan.id


def test_create_requires_auth(client):
    resp = client.post(
        "/api/v1/study-plans",
        json={"title": "Bio", "goal": "Pass", "daily_minutes": 60},
    )
    assert resp.status_code == 401


def test_create_study_plan(client, auth_headers, monkeypatch):
    user_id = _user_id(client, auth_headers)

    def fake_generate(db, user, data):
        return StudyPlan(
            id=uuid.uuid4(),
            user_id=user.id,
            title=data.title,
            goal=data.goal,
            exam_date=data.exam_date,
            daily_minutes=data.daily_minutes,
            tasks=[
                {
                    "date": "2026-11-23",
                    "topic": "Cells",
                    "document_id": None,
                    "minutes": 60,
                    "done": False,
                }
            ],
            weekly_goals=[
                {
                    "week": 1,
                    "goal": "Master cells",
                    "start_date": "2026-11-23",
                    "end_date": "2026-11-29",
                }
            ],
            revision_schedule=[
                {"date": "2026-12-05", "topic": "Full revision", "minutes": 60}
            ],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(
        "api.v1.study_plans.plan_service.generate_study_plan", fake_generate
    )
    resp = client.post(
        "/api/v1/study-plans",
        json={
            "title": "Biology Final",
            "goal": "Pass the final",
            "exam_date": "2026-12-10",
            "daily_minutes": 60,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Biology Final"
    assert body["exam_date"] == "2026-12-10"
    assert len(body["tasks"]) == 1
    assert body["weekly_goals"][0]["goal"] == "Master cells"
    assert body["revision_schedule"][0]["topic"] == "Full revision"


def test_create_invalid(client, auth_headers):
    cases = [
        {"title": "", "goal": "Pass", "daily_minutes": 60},
        {"title": "Bio", "goal": "Pass", "daily_minutes": 0},
        {"title": "Bio", "goal": "Pass", "daily_minutes": 481},
    ]
    for payload in cases:
        resp = client.post(
            "/api/v1/study-plans", json=payload, headers=auth_headers
        )
        assert resp.status_code == 422


def test_list_study_plans(client, auth_headers):
    user_id = _user_id(client, auth_headers)
    now = datetime.now(timezone.utc)
    _insert_plan(user_id, title="Older", created_at=now)
    _insert_plan(user_id, title="Newer", created_at=now + timedelta(seconds=1))
    resp = client.get("/api/v1/study-plans", headers=auth_headers)
    assert resp.status_code == 200
    assert [p["title"] for p in resp.json()] == ["Newer", "Older"]


def test_get_study_plan(client, auth_headers):
    user_id = _user_id(client, auth_headers)
    plan_id = _insert_plan(user_id)
    resp = client.get(f"/api/v1/study-plans/{plan_id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Plan"
    assert len(body["tasks"]) == 2
    assert len(body["weekly_goals"]) == 1
    assert len(body["revision_schedule"]) == 1


def test_get_study_plan_not_found(client, auth_headers):
    resp = client.get(f"/api/v1/study-plans/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
    # Another user's plan is not visible either.
    plan_id = _insert_plan(uuid.uuid4())
    resp = client.get(f"/api/v1/study-plans/{plan_id}", headers=auth_headers)
    assert resp.status_code == 404


def test_update_task(client, auth_headers):
    user_id = _user_id(client, auth_headers)
    plan_id = _insert_plan(user_id)
    resp = client.patch(
        f"/api/v1/study-plans/{plan_id}/tasks/0",
        json={"done": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tasks"][0]["done"] is True
    assert body["tasks"][1]["done"] is False


def test_update_task_not_found(client, auth_headers):
    user_id = _user_id(client, auth_headers)
    plan_id = _insert_plan(user_id)
    resp = client.patch(
        f"/api/v1/study-plans/{plan_id}/tasks/9",
        json={"done": True},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_delete_study_plan(client, auth_headers):
    user_id = _user_id(client, auth_headers)
    plan_id = _insert_plan(user_id)
    resp = client.delete(f"/api/v1/study-plans/{plan_id}", headers=auth_headers)
    assert resp.status_code == 204
    again = client.get(f"/api/v1/study-plans/{plan_id}", headers=auth_headers)
    assert again.status_code == 404


def test_delete_study_plan_not_found(client, auth_headers):
    plan_id = _insert_plan(uuid.uuid4())
    resp = client.delete(f"/api/v1/study-plans/{plan_id}", headers=auth_headers)
    assert resp.status_code == 404
