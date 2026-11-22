"""Quiz service tests with a mocked Gemini client."""

import uuid

import pytest

from core.exceptions import BadRequestError, NotFoundError
from models.quiz import Quiz, QuizAttempt
from models.study_document import DocumentStatus, StudyDocument
from models.user import User
from services import quiz_service
from tests.conftest import TestingSessionLocal

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


@pytest.fixture()
def user_and_doc():
    db = TestingSessionLocal()
    user = User(
        email=f"qz-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Quiz Tester",
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
        "services.quiz_service.get_document_text",
        lambda user_id, doc_id: "Some study material about plants.",
    )


def _mock_gemini(monkeypatch, items):
    monkeypatch.setattr(
        "services.quiz_service.gemini.generate_json",
        lambda *a, **k: items,
    )


def _insert_quiz(db, user, doc, questions):
    quiz = Quiz(
        document_id=doc.id, user_id=user.id, title="Test Quiz", questions=questions
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


def test_generate_quiz_mixed_types(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    _mock_gemini(monkeypatch, MIXED_QUESTIONS)
    quiz = quiz_service.generate_quiz(db, user, doc.id, num_questions=3)
    assert quiz.title == "Quiz: notes.pdf"
    assert [q["type"] for q in quiz.questions] == [
        "multiple_choice",
        "true_false",
        "short_answer",
    ]
    assert quiz.questions[0]["correct_index"] == 1
    assert quiz.questions[1]["correct"] is False
    assert quiz.questions[2]["answer"] == "photosynthesis"


def test_generate_quiz_question_types_filter(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    seen = {}

    def capture(prompt, system_instruction=None, temperature=0.3):
        seen["prompt"] = prompt
        return [MIXED_QUESTIONS[1]]

    monkeypatch.setattr("services.quiz_service.gemini.generate_json", capture)
    quiz = quiz_service.generate_quiz(
        db, user, doc.id, num_questions=1, question_types=["true_false"]
    )
    assert "true/false" in seen["prompt"].lower()
    assert "multiple-choice" not in seen["prompt"].lower()
    assert "short answer" not in seen["prompt"].lower()
    assert [q["type"] for q in quiz.questions] == ["true_false"]


def test_generate_quiz_skips_invalid_items(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    _mock_gemini(
        monkeypatch,
        [
            # Invalid: only 1 option.
            {
                "type": "multiple_choice",
                "question": "Bad MCQ 1",
                "options": ["Only one"],
                "correct_index": 0,
            },
            # Invalid: correct_index out of range.
            {
                "type": "multiple_choice",
                "question": "Bad MCQ 2",
                "options": ["A", "B"],
                "correct_index": 5,
            },
            # Invalid: correct_index not a number.
            {
                "type": "multiple_choice",
                "question": "Bad MCQ 3",
                "options": ["A", "B"],
                "correct_index": "two",
            },
            # Invalid: true/false with an unparseable correct value.
            {"type": "true_false", "question": "Bad TF", "correct": "maybe"},
            # Invalid: true/false missing correct.
            {"type": "true_false", "question": "Bad TF 2"},
            # Invalid: short answer missing answer.
            {"type": "short_answer", "question": "Bad SA"},
            # Invalid: not a dict / no question.
            "garbage",
            {"type": "multiple_choice", "options": ["A", "B"], "correct_index": 0},
            # Valid.
            {
                "type": "multiple_choice",
                "question": "Good question?",
                "options": ["A", "B", "C", "D"],
                "correct_index": 2,
            },
        ],
    )
    quiz = quiz_service.generate_quiz(db, user, doc.id, num_questions=10)
    assert [q["question"] for q in quiz.questions] == ["Good question?"]


def test_generate_quiz_infers_type(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    _mock_gemini(
        monkeypatch,
        [
            # No type, but MCQ shape.
            {"question": "Q1", "options": ["A", "B"], "correct_index": 0},
            # No type, but true/false shape.
            {"question": "Q2", "correct": True},
            # No type, but short-answer shape.
            {"question": "Q3", "answer": "expected"},
        ],
    )
    quiz = quiz_service.generate_quiz(db, user, doc.id, num_questions=3)
    assert [q["type"] for q in quiz.questions] == [
        "multiple_choice",
        "true_false",
        "short_answer",
    ]


def test_generate_quiz_dedupes(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    _mock_gemini(
        monkeypatch,
        [
            {
                "type": "true_false",
                "question": "Same question?",
                "correct": True,
            },
            {
                "type": "true_false",
                "question": "same question?",
                "correct": True,
            },
        ],
    )
    quiz = quiz_service.generate_quiz(db, user, doc.id, num_questions=10)
    assert len(quiz.questions) == 1


def test_generate_quiz_no_valid_questions(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    _mock_gemini(monkeypatch, [{"type": "short_answer", "question": "No answer"}])
    with pytest.raises(BadRequestError, match="Could not generate"):
        quiz_service.generate_quiz(db, user, doc.id)


def test_generate_quiz_handles_dict_response(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    _mock_gemini(monkeypatch, {"questions": [MIXED_QUESTIONS[0]]})
    quiz = quiz_service.generate_quiz(db, user, doc.id, num_questions=1)
    assert len(quiz.questions) == 1


def test_generate_quiz_document_not_found(user_and_doc):
    db, user, _ = user_and_doc
    with pytest.raises(NotFoundError):
        quiz_service.generate_quiz(db, user, uuid.uuid4())


def test_generate_quiz_no_text(user_and_doc, monkeypatch):
    db, user, doc = user_and_doc
    monkeypatch.setattr(
        "services.quiz_service.get_document_text",
        lambda user_id, doc_id: "   ",
    )
    with pytest.raises(BadRequestError):
        quiz_service.generate_quiz(db, user, doc.id)


def test_to_public_quiz_strips_answers(user_and_doc):
    db, user, doc = user_and_doc
    quiz = _insert_quiz(db, user, doc, MIXED_QUESTIONS)
    public = quiz_service.to_public_quiz(quiz)
    assert [q.type for q in public.questions] == [
        "multiple_choice",
        "true_false",
        "short_answer",
    ]
    assert public.questions[0].options == ["London", "Paris", "Berlin", "Madrid"]
    assert public.questions[1].options == ["True", "False"]
    assert public.questions[2].options is None
    dumped = public.model_dump_json()
    assert "correct_index" not in dumped
    assert "photosynthesis" not in dumped  # the short-answer solution
    assert "Paris is the capital" not in dumped  # explanations hidden too


def test_to_public_quiz_backwards_compat(user_and_doc):
    db, user, doc = user_and_doc
    # Old format: no "type" key (pre-Step-10 quizzes are MCQ-only).
    old_question = {
        "question": "Old question?",
        "options": ["A", "B", "C", "D"],
        "correct_index": 0,
        "explanation": "Old explanation.",
    }
    quiz = _insert_quiz(db, user, doc, [old_question])
    public = quiz_service.to_public_quiz(quiz)
    assert public.questions[0].type == "multiple_choice"
    assert public.questions[0].options == ["A", "B", "C", "D"]


def test_submit_quiz_all_correct(user_and_doc):
    db, user, doc = user_and_doc
    quiz = _insert_quiz(db, user, doc, MIXED_QUESTIONS)
    result = quiz_service.submit_quiz(db, user, quiz.id, [1, 1, "photosynthesis"])
    assert result.score == 3
    assert result.total == 3
    assert [r.is_correct for r in result.results] == [True, True, True]
    assert result.results[1].correct == 1  # False = index 1 in ["True", "False"]
    assert result.results[2].correct == "photosynthesis"
    attempt = (
        db.query(QuizAttempt).filter(QuizAttempt.quiz_id == quiz.id).first()
    )
    assert attempt.score == 3
    assert attempt.total == 3
    assert attempt.answers == [1, 1, "photosynthesis"]


def test_submit_quiz_short_answer_fuzzy(user_and_doc):
    db, user, doc = user_and_doc
    questions = [
        {
            "type": "short_answer",
            "question": "Q1?",
            "answer": "photosynthesis",
            "explanation": "",
        },
        {
            "type": "short_answer",
            "question": "Q2?",
            "answer": "photosynthesis",
            "explanation": "",
        },
        {
            "type": "short_answer",
            "question": "Q3?",
            "answer": "photosynthesis",
            "explanation": "",
        },
        {
            "type": "short_answer",
            "question": "Q4?",
            "answer": "photosynthesis",
            "explanation": "",
        },
    ]
    quiz = _insert_quiz(db, user, doc, questions)
    result = quiz_service.submit_quiz(
        db, user, quiz.id, ["Photosynthesis ", "photo synthesis", "respiration", ""]
    )
    assert result.score == 2
    assert [r.is_correct for r in result.results] == [True, True, False, False]


def test_submit_quiz_wrong_answers_and_length(user_and_doc):
    db, user, doc = user_and_doc
    quiz = _insert_quiz(db, user, doc, MIXED_QUESTIONS)
    result = quiz_service.submit_quiz(db, user, quiz.id, [0, 0, "wrong"])
    assert result.score == 0
    assert [r.is_correct for r in result.results] == [False, False, False]
    with pytest.raises(BadRequestError, match="Expected 3 answers"):
        quiz_service.submit_quiz(db, user, quiz.id, [1, 1])


def test_submit_quiz_not_found(user_and_doc):
    db, user, _ = user_and_doc
    with pytest.raises(NotFoundError):
        quiz_service.submit_quiz(db, user, uuid.uuid4(), [1])


def test_submit_quiz_wrong_answer_type(user_and_doc):
    db, user, doc = user_and_doc
    quiz = _insert_quiz(db, user, doc, MIXED_QUESTIONS)
    # String where an index was expected, int where text was expected:
    # marked wrong, not a crash.
    result = quiz_service.submit_quiz(db, user, quiz.id, ["Paris", 1, 3])
    assert result.score == 1  # only the true/false answer was right
    assert [r.is_correct for r in result.results] == [False, True, False]
