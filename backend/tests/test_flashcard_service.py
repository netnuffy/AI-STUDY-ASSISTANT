"""Flashcard service tests with a mocked Gemini client."""

import uuid

import pytest

from core.exceptions import BadRequestError, NotFoundError
from models.flashcard import Difficulty, Flashcard
from models.study_document import DocumentStatus, StudyDocument
from models.user import User
from services import flashcard_service
from tests.conftest import TestingSessionLocal


@pytest.fixture()
def user_and_doc():
    db = TestingSessionLocal()
    user = User(
        email=f"fc-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Flash Tester",
        hashed_password="hashed",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    doc = StudyDocument(
        user_id=user.id,
        title="notes.pdf",
        filename="notes.pdf",
        file_path="/tmp/notes.pdf",
        file_size_bytes=1234,
        status=DocumentStatus.READY,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    yield db, user, doc
    db.close()


@pytest.fixture(autouse=True)
def _mock_document_text(monkeypatch):
    monkeypatch.setattr(
        "services.flashcard_service.get_document_text",
        lambda user_id, doc_id: "Some study material about plants.",
    )


def _mock_gemini(monkeypatch, items):
    monkeypatch.setattr(
        "services.flashcard_service.gemini.generate_json",
        lambda *a, **k: items,
    )


def test_generate_flashcards_creates_cards(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    _mock_gemini(
        monkeypatch,
        [
            {
                "front": "What is photosynthesis?",
                "back": "Plants making food from light.",
                "difficulty": "easy",
            },
            {
                "front": "What is chlorophyll?",
                "back": "Green pigment in leaves.",
                "difficulty": "hard",
            },
            {
                "front": "Why are leaves green?",
                "back": "Because of chlorophyll.",
                "difficulty": "medium",
            },
        ],
    )
    cards = flashcard_service.generate_flashcards(db, user, doc.id, count=2)
    assert len(cards) == 2  # count respected even when Gemini returns more
    assert cards[0].front == "What is photosynthesis?"
    assert cards[0].difficulty == Difficulty.EASY
    assert cards[1].difficulty == Difficulty.HARD
    assert cards[0].known is False
    assert cards[0].review_count == 0
    # Persisted: a fresh query finds them.
    assert db.query(Flashcard).filter(Flashcard.document_id == doc.id).count() == 2


def test_generate_flashcards_skips_invalid_items(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    _mock_gemini(
        monkeypatch,
        [
            {"front": "Good question?", "back": "Good answer."},
            {"front": "No back"},  # missing back
            {"back": "No front"},  # missing front
            {"front": "   ", "back": "Blank front"},  # empty front
            {"front": "Blank back", "back": ""},  # empty back
            "not a dict",  # wrong type
            None,  # wrong type
        ],
    )
    cards = flashcard_service.generate_flashcards(db, user, doc.id, count=10)
    assert [c.front for c in cards] == ["Good question?"]


def test_generate_flashcards_normalises_difficulty(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    _mock_gemini(
        monkeypatch,
        [
            {"front": "Q1", "back": "A1", "difficulty": "Easy"},
            {"front": "Q2", "back": "A2", "difficulty": "impossible"},
            {"front": "Q3", "back": "A3"},  # missing → medium
            {"front": "Q4", "back": "A4", "difficulty": " HARD "},
        ],
    )
    cards = flashcard_service.generate_flashcards(db, user, doc.id, count=10)
    assert [c.difficulty for c in cards] == [
        Difficulty.EASY,
        Difficulty.MEDIUM,
        Difficulty.MEDIUM,
        Difficulty.HARD,
    ]


def test_generate_flashcards_dedupes_within_response(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    _mock_gemini(
        monkeypatch,
        [
            {"front": "What is X?", "back": "First answer."},
            {"front": "what is x?", "back": "Duplicate with different case."},
            {"front": "What is Y?", "back": "Other answer."},
        ],
    )
    cards = flashcard_service.generate_flashcards(db, user, doc.id, count=10)
    assert [c.front for c in cards] == ["What is X?", "What is Y?"]


def test_generate_flashcards_skips_existing_cards(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    db.add(
        Flashcard(
            document_id=doc.id, user_id=user.id, front="What is X?", back="Old answer."
        )
    )
    db.commit()
    _mock_gemini(
        monkeypatch,
        [
            {"front": "What is X?", "back": "Regenerated duplicate."},
            {"front": "What is Z?", "back": "Brand new."},
        ],
    )
    cards = flashcard_service.generate_flashcards(db, user, doc.id, count=10)
    assert [c.front for c in cards] == ["What is Z?"]


def test_generate_flashcards_handles_dict_response(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    _mock_gemini(monkeypatch, {"flashcards": [{"front": "Q?", "back": "A."}]})
    cards = flashcard_service.generate_flashcards(db, user, doc.id, count=10)
    assert [c.front for c in cards] == ["Q?"]


def test_generate_flashcards_handles_garbage_response(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    _mock_gemini(monkeypatch, "not json at all")
    cards = flashcard_service.generate_flashcards(db, user, doc.id, count=10)
    assert cards == []


def test_generate_flashcards_document_not_found(user_and_doc):
    db, user, _ = user_and_doc
    with pytest.raises(NotFoundError):
        flashcard_service.generate_flashcards(db, user, uuid.uuid4())


def test_generate_flashcards_no_text(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    monkeypatch.setattr(
        "services.flashcard_service.get_document_text",
        lambda user_id, doc_id: "   ",
    )
    with pytest.raises(BadRequestError):
        flashcard_service.generate_flashcards(db, user, doc.id)


def test_review_flashcard_marks_known(user_and_doc):
    db, user, doc = user_and_doc
    card = Flashcard(document_id=doc.id, user_id=user.id, front="Q?", back="A.")
    db.add(card)
    db.commit()
    db.refresh(card)
    reviewed = flashcard_service.review_flashcard(db, user, card.id, True)
    assert reviewed.known is True
    assert reviewed.review_count == 1
    assert reviewed.last_reviewed_at is not None
    reviewed = flashcard_service.review_flashcard(db, user, card.id, False)
    assert reviewed.known is False
    assert reviewed.review_count == 2


def test_review_flashcard_not_found(user_and_doc):
    db, user, doc = user_and_doc
    with pytest.raises(NotFoundError):
        flashcard_service.review_flashcard(db, user, uuid.uuid4(), True)
    # Another user's card is not visible either.
    other = User(
        email=f"fc-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Other",
        hashed_password="x",
    )
    db.add(other)
    db.commit()
    db.refresh(other)
    card = Flashcard(document_id=doc.id, user_id=other.id, front="Q?", back="A.")
    db.add(card)
    db.commit()
    db.refresh(card)
    with pytest.raises(NotFoundError):
        flashcard_service.review_flashcard(db, user, card.id, True)
