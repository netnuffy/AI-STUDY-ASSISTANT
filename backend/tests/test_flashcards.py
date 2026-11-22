"""Flashcard API tests."""

import uuid

from models.flashcard import Difficulty, Flashcard
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


def _insert_card(
    doc_id,
    user_id,
    front="Q?",
    back="A.",
    known=False,
    difficulty=Difficulty.MEDIUM,
):
    db = TestingSessionLocal()
    card = Flashcard(
        document_id=uuid.UUID(doc_id),
        user_id=user_id,
        front=front,
        back=back,
        difficulty=difficulty,
        known=known,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    db.close()
    return card.id


def test_generate_requires_auth(client):
    resp = client.post(
        f"/api/v1/documents/{uuid.uuid4()}/flashcards/generate",
        json={"count": 5},
    )
    assert resp.status_code == 401


def test_generate_flashcards(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    seen = {}

    def fake_generate(db, user, document_id, count=10, difficulty=None):
        seen["count"] = count
        seen["difficulty"] = difficulty
        return [
            Flashcard(
                id=uuid.uuid4(),
                document_id=document_id,
                user_id=user.id,
                front="Q1",
                back="A1",
                difficulty=Difficulty.EASY,
                known=False,
                review_count=0,
                last_reviewed_at=None,
            ),
            Flashcard(
                id=uuid.uuid4(),
                document_id=document_id,
                user_id=user.id,
                front="Q2",
                back="A2",
                difficulty=Difficulty.HARD,
                known=False,
                review_count=0,
                last_reviewed_at=None,
            ),
        ]

    monkeypatch.setattr(
        "api.v1.flashcards.flashcard_service.generate_flashcards", fake_generate
    )
    resp = client.post(
        f"/api/v1/documents/{doc_id}/flashcards/generate",
        json={"count": 2, "difficulty": "easy"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert seen == {"count": 2, "difficulty": "easy"}
    body = resp.json()
    assert [c["front"] for c in body] == ["Q1", "Q2"]
    assert body[0]["difficulty"] == "easy"


def test_generate_invalid_count(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    for bad_count in (0, 51):
        resp = client.post(
            f"/api/v1/documents/{doc_id}/flashcards/generate",
            json={"count": bad_count},
            headers=auth_headers,
        )
        assert resp.status_code == 422


def test_generate_invalid_difficulty(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    resp = client.post(
        f"/api/v1/documents/{doc_id}/flashcards/generate",
        json={"count": 5, "difficulty": "poetic"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_list_flashcards_unknown_first(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    user_id = _user_id(client, auth_headers)
    _insert_card(doc_id, user_id, front="Known Q", known=True)
    _insert_card(doc_id, user_id, front="Unknown Q", known=False)
    resp = client.get(
        f"/api/v1/documents/{doc_id}/flashcards", headers=auth_headers
    )
    assert resp.status_code == 200
    assert [c["front"] for c in resp.json()] == ["Unknown Q", "Known Q"]


def test_list_flashcards_filter_by_known(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    user_id = _user_id(client, auth_headers)
    _insert_card(doc_id, user_id, front="Known Q", known=True)
    _insert_card(doc_id, user_id, front="Unknown Q", known=False)
    known = client.get(
        f"/api/v1/documents/{doc_id}/flashcards?known=true", headers=auth_headers
    )
    assert [c["front"] for c in known.json()] == ["Known Q"]
    unknown = client.get(
        f"/api/v1/documents/{doc_id}/flashcards?known=false", headers=auth_headers
    )
    assert [c["front"] for c in unknown.json()] == ["Unknown Q"]


def test_list_flashcards_document_not_found(client, auth_headers):
    resp = client.get(
        f"/api/v1/documents/{uuid.uuid4()}/flashcards", headers=auth_headers
    )
    assert resp.status_code == 404


def test_review_flashcard(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    user_id = _user_id(client, auth_headers)
    card_id = _insert_card(doc_id, user_id, front="Q?", back="A.")
    resp = client.patch(
        f"/api/v1/flashcards/{card_id}/review",
        json={"known": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["known"] is True
    assert body["review_count"] == 1
    assert body["last_reviewed_at"] is not None


def test_review_flashcard_not_found(client, auth_headers):
    resp = client.patch(
        f"/api/v1/flashcards/{uuid.uuid4()}/review",
        json={"known": True},
        headers=auth_headers,
    )
    assert resp.status_code == 404
