"""Quiz API tests."""

import uuid
from datetime import datetime, timedelta, timezone

from models.quiz import Quiz, QuizAttempt
from tests.conftest import TestingSessionLocal

# A minimal valid one-page PDF (same bytes as test_documents.py).
MINIMAL_PDF = (
    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
    b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 24 Tf 100 700 Td (Hello World) Tj ET\nendstream\nendobj\n"
    b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    b"trailer\n<< /Root 1 0 R /Size 6 >>\n%%EOF\n"
)

MIXED_QUESTIONS = [
    {
        "type": "multiple_choice",
        "question": "What is the capital of France?",
        "options": ["London", "Paris", "Berlin", "Madrid"],
        "correct_index": 1,
        "explanation": "Paris is the capital.",
    },
    {
        "type": "true_false",
        "question": "The Earth is flat.",
        "correct": False,
        "explanation": "The Earth is an oblate spheroid.",
    },
    {
        "type": "short_answer",
        "question": "What process do plants use to make food?",
        "answer": "photosynthesis",
        "explanation": "Photosynthesis converts light to energy.",
    },
]


def _upload_doc(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "api.v1.documents.process_document_background", lambda document_id: None
    )
    resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("notes.pdf", MINIMAL_PDF, "application/pdf")},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _user_id(client, auth_headers):
    me = client.get("/api/v1/auth/me", headers=auth_headers).json()
    return uuid.UUID(me["id"])


def _insert_quiz(doc_id, user_id, questions=None, title="Test Quiz"):
    db = TestingSessionLocal()
    quiz = Quiz(
        document_id=uuid.UUID(doc_id),
        user_id=user_id,
        title=title,
        questions=questions if questions is not None else MIXED_QUESTIONS,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    db.close()
    return quiz.id


def _insert_attempt(quiz_id, user_id, score, total, completed_at):
    db = TestingSessionLocal()
    attempt = QuizAttempt(
        quiz_id=quiz_id,
        user_id=user_id,
        score=score,
        total=total,
        answers=[],
        completed_at=completed_at,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    db.close()
    return attempt.id


def test_generate_requires_auth(client):
    resp = client.post(
        f"/api/v1/documents/{uuid.uuid4()}/quizzes/generate",
        json={"num_questions": 5},
    )
    assert resp.status_code == 401


def test_generate_quiz(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    user_id = _user_id(client, auth_headers)
    seen = {}

    def fake_generate(
        db,
        user,
        document_id,
        num_questions=10,
        difficulty=None,
        title=None,
        question_types=None,
    ):
        seen["num_questions"] = num_questions
        seen["question_types"] = question_types
        return Quiz(
            id=uuid.uuid4(),
            document_id=document_id,
            user_id=user.id,
            title=title or "Quiz",
            questions=MIXED_QUESTIONS,
            created_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(
        "api.v1.quizzes.quiz_service.generate_quiz", fake_generate
    )
    resp = client.post(
        f"/api/v1/documents/{doc_id}/quizzes/generate",
        json={"num_questions": 3, "question_types": ["multiple_choice", "true_false"]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert seen["num_questions"] == 3
    assert seen["question_types"] == ["multiple_choice", "true_false"]
    body = resp.json()
    assert [q["type"] for q in body["questions"]] == [
        "multiple_choice",
        "true_false",
        "short_answer",
    ]
    assert body["questions"][1]["options"] == ["True", "False"]
    assert body["questions"][2]["options"] is None
    assert "correct_index" not in resp.text
    assert "photosynthesis" not in resp.text


def test_generate_invalid_num_questions(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    for bad in (0, 21):
        resp = client.post(
            f"/api/v1/documents/{doc_id}/quizzes/generate",
            json={"num_questions": bad},
            headers=auth_headers,
        )
        assert resp.status_code == 422


def test_generate_invalid_question_types(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    resp = client.post(
        f"/api/v1/documents/{doc_id}/quizzes/generate",
        json={"num_questions": 5, "question_types": ["essay"]},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_generate_invalid_difficulty(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    resp = client.post(
        f"/api/v1/documents/{doc_id}/quizzes/generate",
        json={"num_questions": 5, "difficulty": "poetic"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_get_quiz(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    user_id = _user_id(client, auth_headers)
    quiz_id = _insert_quiz(doc_id, user_id)
    resp = client.get(f"/api/v1/quizzes/{quiz_id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Test Quiz"
    assert len(body["questions"]) == 3
    assert "correct_index" not in resp.text
    assert "photosynthesis" not in resp.text


def test_get_quiz_not_found(client, auth_headers, monkeypatch):
    resp = client.get(f"/api/v1/quizzes/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
    # Another user's quiz is not visible either.
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    other_user_id = uuid.uuid4()
    quiz_id = _insert_quiz(doc_id, other_user_id)
    resp = client.get(f"/api/v1/quizzes/{quiz_id}", headers=auth_headers)
    assert resp.status_code == 404


def test_submit_quiz(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    user_id = _user_id(client, auth_headers)
    quiz_id = _insert_quiz(doc_id, user_id)
    resp = client.post(
        f"/api/v1/quizzes/{quiz_id}/submit",
        json={"answers": [1, 1, "photosynthesis"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["score"] == 3
    assert body["total"] == 3
    assert [r["type"] for r in body["results"]] == [
        "multiple_choice",
        "true_false",
        "short_answer",
    ]
    assert body["results"][0]["explanation"] == "Paris is the capital."
    # Attempt recorded.
    attempts = client.get(
        f"/api/v1/quizzes/{quiz_id}/attempts", headers=auth_headers
    )
    assert attempts.status_code == 200
    assert len(attempts.json()) == 1
    assert attempts.json()[0]["score"] == 3


def test_submit_wrong_length(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    user_id = _user_id(client, auth_headers)
    quiz_id = _insert_quiz(doc_id, user_id)
    resp = client.post(
        f"/api/v1/quizzes/{quiz_id}/submit",
        json={"answers": [1, 1]},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_list_attempts_empty(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    user_id = _user_id(client, auth_headers)
    quiz_id = _insert_quiz(doc_id, user_id)
    resp = client.get(f"/api/v1/quizzes/{quiz_id}/attempts", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_recent_attempts_requires_auth(client):
    resp = client.get("/api/v1/quizzes/attempts/recent")
    assert resp.status_code == 401


def test_recent_attempts(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    user_id = _user_id(client, auth_headers)
    now = datetime.now(timezone.utc)
    quiz_a = _insert_quiz(doc_id, user_id, title="Quiz A")
    quiz_b = _insert_quiz(doc_id, user_id, title="Quiz B")
    _insert_attempt(quiz_a, user_id, 2, 4, now)
    _insert_attempt(quiz_b, user_id, 3, 4, now + timedelta(seconds=1))
    resp = client.get("/api/v1/quizzes/attempts/recent", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    # Newest first.
    assert body[0]["quiz_title"] == "Quiz B"
    assert body[0]["score"] == 3
    assert body[0]["total"] == 4
    assert body[0]["percentage"] == 75
    assert body[1]["quiz_title"] == "Quiz A"
    assert body[1]["percentage"] == 50


def test_recent_attempts_limit(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    user_id = _user_id(client, auth_headers)
    now = datetime.now(timezone.utc)
    quiz_id = _insert_quiz(doc_id, user_id)
    _insert_attempt(quiz_id, user_id, 1, 3, now)
    _insert_attempt(quiz_id, user_id, 2, 3, now + timedelta(seconds=1))
    resp = client.get(
        "/api/v1/quizzes/attempts/recent?limit=1", headers=auth_headers
    )
    assert len(resp.json()) == 1


def test_recent_attempts_only_own(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    user_id = _user_id(client, auth_headers)
    quiz_id = _insert_quiz(doc_id, user_id)
    _insert_attempt(
        quiz_id, uuid.uuid4(), 3, 3, datetime.now(timezone.utc)
    )
    resp = client.get("/api/v1/quizzes/attempts/recent", headers=auth_headers)
    assert resp.json() == []


def test_recent_attempts_empty(client, auth_headers):
    resp = client.get("/api/v1/quizzes/attempts/recent", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []
