# A minimal valid one-page PDF (created by hand so tests don't need PyMuPDF).
MINIMAL_PDF = (
    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
    b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 24 Tf 100 700 Td (Hello World) Tj ET\nendstream\nendobj\n"
    b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    b"trailer\n<< /Root 1 0 R /Size 6 >>\n%%EOF\n"
)


def test_upload_requires_auth(client):
    resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("notes.pdf", MINIMAL_PDF, "application/pdf")},
    )
    assert resp.status_code == 401


def test_upload_rejects_non_pdf(client, auth_headers):
    resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_upload_list_get_delete(client, auth_headers, monkeypatch):
    # Skip real PDF processing (needs PyMuPDF + Gemini + ChromaDB).
    monkeypatch.setattr(
        "api.v1.documents.process_document_background", lambda document_id: None
    )

    upload = client.post(
        "/api/v1/documents/upload",
        files={"file": ("notes.pdf", MINIMAL_PDF, "application/pdf")},
        headers=auth_headers,
    )
    assert upload.status_code == 201
    doc = upload.json()
    assert doc["title"] == "notes"
    assert doc["status"] == "uploading"
    doc_id = doc["id"]

    listing = client.get("/api/v1/documents", headers=auth_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1
    assert any(d["id"] == doc_id for d in listing.json()["items"])

    fetched = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["filename"] == "notes.pdf"

    deleted = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert deleted.status_code == 204

    gone = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert gone.status_code == 404


def test_upload_rejects_pdf_extension_with_invalid_content(client, auth_headers):
    """A .pdf filename with non-PDF bytes must be rejected (magic-byte check)."""
    resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("fake.pdf", b"this is not a pdf file", "application/pdf")},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_upload_rejects_oversized_file(client, auth_headers):
    """Files over the 25 MB limit must be rejected."""
    oversized = b"%PDF-" + b"0" * (25 * 1024 * 1024)  # 25 MB + 5 bytes
    resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("big.pdf", oversized, "application/pdf")},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "25 MB" in resp.json()["detail"]
