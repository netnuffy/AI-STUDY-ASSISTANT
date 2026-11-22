"""Summary API tests (mocked AI pipeline)."""

import uuid
from datetime import datetime, timedelta, timezone

from tests.conftest import TestingSessionLocal
from models.study_document import DocumentStatus, StudyDocument
from models.summary import Summary

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


def _upload_doc(client, auth_headers, monkeypatch, filename="notes.pdf"):
    monkeypatch.setattr(
        "api.v1.documents.process_document_background", lambda document_id: None
    )
    resp = client.post(
        "/api/v1/documents/upload",
        files={"file": (filename, MINIMAL_PDF, "application/pdf")},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _insert_summary(doc_id, **overrides):
    data = {
        "content": "Summary content.",
        "key_points": ["Point one"],
        "key_concepts": [{"term": "Term", "definition": "Def"}],
        "important_questions": ["What is this?"],
    }
    data.update(overrides)
    db = TestingSessionLocal()
    db.add(Summary(document_id=uuid.UUID(doc_id), **data))
    db.commit()
    db.close()


def test_get_summary_requires_auth(client):
    resp = client.get(f"/api/v1/documents/{uuid.uuid4()}/summary")
    assert resp.status_code == 401


def test_get_summary_not_ready(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    resp = client.get(f"/api/v1/documents/{doc_id}/summary", headers=auth_headers)
    assert resp.status_code == 404


def test_get_summary_success(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    _insert_summary(doc_id)
    resp = client.get(f"/api/v1/documents/{doc_id}/summary", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["content"] == "Summary content."
    assert body["key_points"] == ["Point one"]
    assert body["key_concepts"] == [{"term": "Term", "definition": "Def"}]
    assert body["important_questions"] == ["What is this?"]


def test_regenerate_summary(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    monkeypatch.setattr(
        "api.v1.summaries.embedding_service.get_document_text",
        lambda user_id, doc_id: "Some document text.",
    )
    monkeypatch.setattr(
        "api.v1.summaries.summary_service.generate_summary",
        lambda text, style="standard": {
            "content": f"Regenerated ({style}).",
            "key_points": ["New point"],
            "key_concepts": [{"term": "New", "definition": "New def"}],
            "important_questions": ["New question?"],
        },
    )
    resp = client.post(
        f"/api/v1/documents/{doc_id}/summary/regenerate",
        json={"style": "short"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["content"] == "Regenerated (short)."
    assert body["key_points"] == ["New point"]
    assert body["key_concepts"] == [{"term": "New", "definition": "New def"}]
    assert body["important_questions"] == ["New question?"]
    # Persisted: a plain GET returns the regenerated summary.
    again = client.get(f"/api/v1/documents/{doc_id}/summary", headers=auth_headers)
    assert again.status_code == 200
    assert again.json()["content"] == "Regenerated (short)."


def test_regenerate_invalid_style(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    resp = client.post(
        f"/api/v1/documents/{doc_id}/summary/regenerate",
        json={"style": "poetic"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_recent_summaries_requires_auth(client):
    resp = client.get("/api/v1/summaries/recent")
    assert resp.status_code == 401


def test_recent_summaries(client, auth_headers, monkeypatch):
    now = datetime.now(timezone.utc)
    bio_id = _upload_doc(client, auth_headers, monkeypatch, filename="bio.pdf")
    chem_id = _upload_doc(client, auth_headers, monkeypatch, filename="chem.pdf")
    _insert_summary(bio_id, updated_at=now)
    _insert_summary(
        chem_id,
        content="Chemistry summary content.",
        key_points=["P1", "P2", "P3"],
        updated_at=now + timedelta(seconds=1),
    )
    resp = client.get("/api/v1/summaries/recent", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    # Newest first.
    assert body[0]["document_title"] == "chem"
    assert body[0]["document_id"] == chem_id
    assert body[0]["content_preview"] == "Chemistry summary content."
    assert body[0]["key_points_count"] == 3
    assert body[1]["document_title"] == "bio"
    assert body[1]["key_points_count"] == 1


def test_recent_summaries_preview_truncated(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    _insert_summary(doc_id, content="x" * 300)
    resp = client.get("/api/v1/summaries/recent", headers=auth_headers)
    assert len(resp.json()[0]["content_preview"]) == 200


def test_recent_summaries_limit(client, auth_headers, monkeypatch):
    doc_id = _upload_doc(client, auth_headers, monkeypatch)
    _insert_summary(doc_id)
    doc_id2 = _upload_doc(client, auth_headers, monkeypatch, filename="two.pdf")
    _insert_summary(doc_id2)
    resp = client.get("/api/v1/summaries/recent?limit=1", headers=auth_headers)
    assert len(resp.json()) == 1


def test_recent_summaries_only_own(client, auth_headers, monkeypatch):
    # Another user's document + summary must not appear.
    db = TestingSessionLocal()
    other_doc = StudyDocument(
        user_id=uuid.uuid4(),
        title="Other",
        filename="other.pdf",
        file_path="/tmp/other.pdf",
        file_size_bytes=1,
        status=DocumentStatus.READY,
    )
    db.add(other_doc)
    db.commit()
    db.refresh(other_doc)
    db.add(
        Summary(
            document_id=other_doc.id,
            content="Other summary",
            key_points=[],
            key_concepts=[],
            important_questions=[],
        )
    )
    db.commit()
    db.close()
    resp = client.get("/api/v1/summaries/recent", headers=auth_headers)
    assert resp.json() == []


def test_recent_summaries_empty(client, auth_headers):
    resp = client.get("/api/v1/summaries/recent", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []
