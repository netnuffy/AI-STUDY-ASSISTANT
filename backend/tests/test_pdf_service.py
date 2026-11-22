"""Real extraction tests using PyMuPDF."""

import fitz
import pytest

from core.exceptions import BadRequestError
from services.pdf_service import chunk_pages, clean_text, extract_text_per_page


def _make_pdf(path, pages_text):
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def test_clean_text_removes_hyphenation_and_collapses_whitespace():
    assert clean_text("exam-\nple   with\n\n  spaces") == "example with spaces"
    assert clean_text("  padded  ") == "padded"


def test_extract_text_per_page(tmp_path):
    pdf = tmp_path / "two_pages.pdf"
    _make_pdf(pdf, ["Hello world. This is page one.", "Second page content here."])
    pages = extract_text_per_page(str(pdf))
    assert len(pages) == 2
    assert pages[0]["page"] == 1
    assert "Hello world" in pages[0]["text"]
    assert pages[1]["page"] == 2
    assert "Second page" in pages[1]["text"]


def test_extract_text_per_page_rejects_non_pdf(tmp_path):
    bad = tmp_path / "not_a_pdf.pdf"
    bad.write_text("this is just text, not a pdf")
    with pytest.raises(BadRequestError, match="Could not open PDF"):
        extract_text_per_page(str(bad))


def test_extract_text_per_page_rejects_empty_pdf(tmp_path):
    pdf = tmp_path / "blank.pdf"
    doc = fitz.open()
    doc.new_page()  # no text at all
    doc.save(str(pdf))
    doc.close()
    with pytest.raises(BadRequestError, match="No readable text"):
        extract_text_per_page(str(pdf))


def test_extract_text_per_page_rejects_encrypted_pdf(tmp_path):
    pdf = tmp_path / "locked.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Secret content")
    doc.save(
        str(pdf),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner",
        user_pw="user",
    )
    doc.close()
    with pytest.raises(BadRequestError, match="password-protected"):
        extract_text_per_page(str(pdf))


def test_chunk_pages_splits_long_text():
    text = "Sentence one. " * 200  # 2800 chars
    chunks = chunk_pages([{"page": 3, "text": text}])
    assert len(chunks) >= 2
    assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))
    assert all(c["page"] == 3 for c in chunks)
    assert all(c["text"] for c in chunks)


def test_chunk_pages_skips_empty_pages():
    chunks = chunk_pages([{"page": 1, "text": ""}, {"page": 2, "text": "Some text."}])
    assert len(chunks) == 1
    assert chunks[0]["page"] == 2
