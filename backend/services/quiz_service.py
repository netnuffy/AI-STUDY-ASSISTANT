"""Quiz generation (Gemini) and grading.

Three question types:
- multiple_choice: 2-4 options, one correct_index
- true_false: a statement, correct is true/false
- short_answer: a question, correct is a short expected answer (fuzzy-graded)
"""

import difflib
import re
import uuid

from sqlalchemy.orm import Session

from core import gemini
from core.exceptions import BadRequestError, NotFoundError
from models.study_document import StudyDocument
from models.quiz import Quiz, QuizAttempt
from models.user import User
from schemas.quiz import (
    QuizQuestionPublic,
    QuizResponse,
    QuizResultItem,
    QuizSubmitResponse,
)
from services.embedding_service import get_document_text

QUESTION_TYPES = ("multiple_choice", "true_false", "short_answer")
SHORT_ANSWER_SIMILARITY = 0.8

_TYPE_DESCRIPTIONS = {
    "multiple_choice": (
        'multiple-choice: {"type": "multiple_choice", "question": "...", '
        '"options": ["...", "...", "...", "..."], "correct_index": 0, '
        '"explanation": "..."}'
    ),
    "true_false": (
        'true/false: {"type": "true_false", "question": "...", '
        '"correct": true, "explanation": "..."}'
    ),
    "short_answer": (
        'short answer: {"type": "short_answer", "question": "...", '
        '"answer": "short expected answer", "explanation": "..."}'
    ),
}


def _normalise_question(item) -> dict | None:
    """Validate one Gemini question item. Returns a stored question dict, or
    None if the item is unusable. Infers the type when Gemini omits it."""
    if not isinstance(item, dict):
        return None
    question = str(item.get("question", "")).strip()
    if not question:
        return None
    qtype = str(item.get("type", "")).strip().lower()
    if qtype not in QUESTION_TYPES:
        # Infer from shape (the old prompt returned MCQ items without a type).
        if isinstance(item.get("options"), list) and "correct_index" in item:
            qtype = "multiple_choice"
        elif isinstance(item.get("correct"), bool):
            qtype = "true_false"
        elif item.get("answer"):
            qtype = "short_answer"
        else:
            return None
    explanation = str(item.get("explanation", "")).strip()

    if qtype == "multiple_choice":
        raw_options = item.get("options")
        if not isinstance(raw_options, list):
            return None
        options = [str(o).strip() for o in raw_options if str(o).strip()][:4]
        if len(options) < 2:
            return None
        try:
            correct_index = int(item["correct_index"])
        except (KeyError, TypeError, ValueError):
            return None
        if not 0 <= correct_index < len(options):
            return None
        return {
            "type": "multiple_choice",
            "question": question,
            "options": options,
            "correct_index": correct_index,
            "explanation": explanation,
        }

    if qtype == "true_false":
        correct = item.get("correct")
        if isinstance(correct, str):
            correct = correct.strip().lower()
            if correct in ("true", "t", "yes"):
                correct = True
            elif correct in ("false", "f", "no"):
                correct = False
            else:
                return None
        if not isinstance(correct, bool):
            return None
        return {
            "type": "true_false",
            "question": question,
            "correct": correct,
            "explanation": explanation,
        }

    # short_answer
    answer = str(item.get("answer", "")).strip()
    if not answer:
        return None
    return {
        "type": "short_answer",
        "question": question,
        "answer": answer,
        "explanation": explanation,
    }


def generate_quiz(
    db: Session,
    user: User,
    document_id: uuid.UUID,
    num_questions: int = 10,
    difficulty: str | None = None,
    title: str | None = None,
    question_types: list[str] | None = None,
) -> Quiz:
    doc = (
        db.query(StudyDocument)
        .filter(StudyDocument.id == document_id, StudyDocument.user_id == user.id)
        .first()
    )
    if not doc:
        raise NotFoundError("StudyDocument not found")
    text = get_document_text(user.id, document_id)
    if not text.strip():
        raise BadRequestError("This document has no processed text yet")

    types = question_types or list(QUESTION_TYPES)
    difficulty_note = (
        f"All questions should be {difficulty} difficulty."
        if difficulty
        else "Mix easy, medium and hard questions."
    )
    type_lines = "\n".join(f"- {_TYPE_DESCRIPTIONS[t]}" for t in types)
    prompt = (
        f"Create {num_questions} quiz questions from the study material below. "
        f"{difficulty_note}\n"
        f"Use these question types: {', '.join(types)}.\n"
        "Return a JSON array of objects, one per question, in these shapes:\n"
        f"{type_lines}\n\n"
        f"Material:\n{text}"
    )
    items = gemini.generate_json(
        prompt, system_instruction="You create fair, accurate quiz questions."
    )
    if isinstance(items, dict):
        items = items.get("questions", [])
    if not isinstance(items, list):
        items = []

    questions = []
    seen = set()
    for item in items:
        if len(questions) >= num_questions:
            break
        q = _normalise_question(item)
        if q is None:
            continue
        if q["question"].strip().lower() in seen:
            continue
        seen.add(q["question"].strip().lower())
        questions.append(q)
    if not questions:
        raise BadRequestError(
            "Could not generate any valid questions from this document. "
            "Please try again."
        )
    quiz = Quiz(
        document_id=doc.id,
        user_id=user.id,
        title=title or f"Quiz: {doc.title}",
        questions=questions,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


def to_public_quiz(quiz: Quiz) -> QuizResponse:
    """Strip answers/explanations before sending a quiz to the client."""
    public = []
    for q in quiz.questions:
        qtype = q.get("type", "multiple_choice")  # pre-Step-10 quizzes are MCQ
        if qtype == "multiple_choice":
            options = q["options"]
        elif qtype == "true_false":
            options = ["True", "False"]
        else:
            options = None
        public.append(
            QuizQuestionPublic(type=qtype, question=q["question"], options=options)
        )
    return QuizResponse(
        id=quiz.id,
        document_id=quiz.document_id,
        title=quiz.title,
        questions=public,
        created_at=quiz.created_at,
    )


def _normalise_answer(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _short_answer_correct(expected: str, given: str) -> bool:
    """Exact match after normalisation, or close enough (typos, word order)."""
    expected = _normalise_answer(expected)
    given = _normalise_answer(given)
    if not given:
        return False
    if given == expected:
        return True
    return (
        difflib.SequenceMatcher(None, given, expected).ratio()
        >= SHORT_ANSWER_SIMILARITY
    )


def submit_quiz(
    db: Session, user: User, quiz_id: uuid.UUID, answers: list[int | str]
) -> QuizSubmitResponse:
    quiz = (
        db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.user_id == user.id).first()
    )
    if not quiz:
        raise NotFoundError("Quiz not found")
    questions = quiz.questions
    if len(answers) != len(questions):
        raise BadRequestError(f"Expected {len(questions)} answers, got {len(answers)}")

    results: list[QuizResultItem] = []
    score = 0
    for q, selected in zip(questions, answers):
        qtype = q.get("type", "multiple_choice")
        if qtype == "multiple_choice":
            correct = q["correct_index"]
            is_correct = isinstance(selected, int) and selected == correct
        elif qtype == "true_false":
            correct = 0 if q["correct"] else 1  # index into ["True", "False"]
            is_correct = isinstance(selected, int) and selected == correct
        else:  # short_answer
            correct = q["answer"]
            is_correct = isinstance(selected, str) and _short_answer_correct(
                correct, selected
            )
        score += int(is_correct)
        results.append(
            QuizResultItem(
                type=qtype,
                question=q["question"],
                selected=selected,
                correct=correct,
                is_correct=is_correct,
                explanation=q.get("explanation", ""),
            )
        )

    db.add(
        QuizAttempt(
            quiz_id=quiz.id,
            user_id=user.id,
            score=score,
            total=len(questions),
            answers=answers,
        )
    )
    db.commit()
    return QuizSubmitResponse(score=score, total=len(questions), results=results)
