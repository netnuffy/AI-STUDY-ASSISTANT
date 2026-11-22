# API Documentation

Base URL (local development): `http://localhost:8000`

All API routes live under `/api/v1`, except `/health`. Interactive docs are
available at `http://localhost:8000/docs` (Swagger UI) and
`http://localhost:8000/redoc`.

## Authentication

The API uses JWT Bearer tokens. There are two tokens:

| Token | Lifetime | Use |
|---|---|---|
| Access token | 15 minutes | Send as `Authorization: Bearer <token>` on every request |
| Refresh token | 7 days | Exchange for a new token pair via `POST /auth/refresh` |

Register, then log in to get a token pair. **Login uses OAuth2 form data**
(`username` = email), not JSON.

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"password123","full_name":"You"}'

# Log in (form data!)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=you@example.com&password=password123"
```

## Errors

Errors are JSON: `{"detail": "..."}`. Validation errors return
`{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`.

| Status | Meaning |
|---|---|
| 400 | Bad request (e.g. invalid file, past exam date, no valid questions) |
| 401 | Missing, expired, or invalid token |
| 404 | Resource not found (or summary not ready yet) |
| 422 | Request validation failed |
| 502 | The AI service (Gemini) is unavailable or not configured |

## Auth

### `POST /api/v1/auth/register` — Register

Body: `{ "email": "...", "password": "...", "full_name": "..." }`
(password 8–128 characters). Returns `201` with the user
`{ "id", "email", "full_name", "created_at" }`. Does not return tokens —
log in after registering.

### `POST /api/v1/auth/login` — Log in

OAuth2 form data: `username` (the email) + `password`. Returns
`{ "access_token", "refresh_token", "token_type": "bearer" }`.

### `POST /api/v1/auth/refresh` — Refresh tokens

Body: `{ "refresh_token": "..." }`. Returns a new token pair.

### `GET /api/v1/auth/me` — Current user

Returns the authenticated user's `{ "id", "email", "full_name", "created_at" }`.

## Documents

### `POST /api/v1/documents/upload` — Upload a PDF

Multipart form with a `file` field. PDF only (extension + `%PDF-` magic
bytes checked), max 25 MB. Returns `201` with the document metadata; the
file is processed in the background (text extraction → chunks → embeddings
→ summary), so `status` starts as `uploading` and becomes `ready` (or
`failed`, with `error_message`).

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@notes.pdf;type=application/pdf"
```

### `GET /api/v1/documents` — List documents

Query: `page` (default 1), `page_size`. Returns
`{ "items": [...], "total", "page", "page_size" }`. Each item:
`{ "id", "title", "filename", "file_size_bytes", "page_count", "status",
"error_message", "created_at" }`, where `status` is `uploading` |
`processing` | `ready` | `failed`.

### `GET /api/v1/documents/{document_id}` — Get one document

### `DELETE /api/v1/documents/{document_id}` — Delete a document

Returns `204`. Removes the file, its vector embeddings, and all related
rows (summary, flashcards, quizzes, chat messages).

## Summaries

### `GET /api/v1/documents/{document_id}/summary` — Get summary

Returns `{ "document_id", "content", "key_points", "key_concepts",
"important_questions" }`. `key_concepts` is a list of
`{ "term", "definition" }`. Returns `404` with "Summary is not ready yet"
while processing.

### `POST /api/v1/documents/{document_id}/summary/regenerate` — Regenerate

Body: `{ "style": "short" | "standard" | "detailed" }`. Regenerates the
summary (and its key points, concepts, and questions) in the new style.

### `GET /api/v1/summaries/recent` — Recent summaries (dashboard)

Query: `limit` (1–20, default 5). The user's most recently updated
summaries, newest first: `[{ "document_id", "document_title",
"content_preview", "key_points_count", "updated_at" }]`. The preview is the
first 200 characters of the summary.

## Chat (RAG)

### `POST /api/v1/chat` — Ask a question

Body: `{ "question": "...", "document_id": "..." }` — `document_id` is
optional; omit it to ask across all documents. The question is 1–2000
characters. Returns `{ "answer", "sources", "document_id" }`, where
`sources` is a list of `{ "page", "excerpt" }` citations. Answers are
grounded in the retrieved chunks; if nothing relevant is found, the answer
says so instead of guessing. Both messages are saved to history.

### `GET /api/v1/chat/history` — Chat history

Query: `document_id` (optional), `limit` (1–200, default 50). Returns the
newest messages first: `[{ "id", "role": "user" | "assistant", "content",
"document_id", "created_at" }]`.

## Flashcards

### `POST /api/v1/documents/{document_id}/flashcards/generate` — Generate

Body: `{ "count": 10, "difficulty": "medium" }` — `count` 1–50 (default
10), `difficulty` optional (`easy` | `medium` | `hard`). Returns `201`
with the created cards. Cards are de-duplicated against existing ones.

### `GET /api/v1/documents/{document_id}/flashcards` — List flashcards

Query: `known` (optional filter, `true` | `false`). Unknown cards come
first, then oldest first. Each card: `{ "id", "document_id", "front",
"back", "difficulty", "known", "review_count", "last_reviewed_at" }`.

### `PATCH /api/v1/flashcards/{flashcard_id}/review` — Review a card

Body: `{ "known": true }`. Marks the card known/unknown and bumps
`review_count`.

## Quizzes

### `POST /api/v1/documents/{document_id}/quizzes/generate` — Generate a quiz

Body:

```json
{
  "num_questions": 10,
  "difficulty": "medium",
  "title": "Biology — Quiz 1",
  "question_types": ["multiple_choice", "true_false", "short_answer"]
}
```

`num_questions` 1–20 (default 10); `difficulty` and `title` optional;
`question_types` optional — omit it for a mix of all three types. Returns
`201` with the quiz (questions without answers).

### `GET /api/v1/quizzes/{quiz_id}` — Get a quiz

The public view: questions with their type and options, but no answers.
True/false questions get options `["True", "False"]`; short-answer
questions have `options: null`.

### `POST /api/v1/quizzes/{quiz_id}/submit` — Submit answers

Body: `{ "answers": [...] }` — one entry per question: a number (option
index) for multiple-choice and true/false, a string for short answers.
Short answers are graded by exact match or ≥ 80% similarity. Returns the
score, total, and per-question results (your answer vs the correct answer).
Unanswered or wrong-typed answers count as incorrect, never as errors.

### `GET /api/v1/quizzes/{quiz_id}/attempts` — Attempt history

All attempts for one quiz, newest first.

### `GET /api/v1/quizzes/attempts/recent` — Recent attempts (dashboard)

Query: `limit` (1–20, default 5). Attempts across all quizzes, newest
first: `[{ "id", "quiz_id", "quiz_title", "score", "total", "percentage",
"completed_at" }]`.

## Study plans

### `POST /api/v1/study-plans` — Create a plan

Body:

```json
{
  "title": "Biology",
  "goal": "Score 85%+ in the final",
  "exam_date": "2026-12-06",
  "daily_minutes": 45,
  "document_ids": ["..."]
}
```

`title` and `goal` are required; `exam_date` is optional (defaults to 14
days out for planning); `daily_minutes` 5–480 (default 30). A past exam
date is rejected. Returns `201` with the plan: daily `tasks`
`[{ "date", "topic", "document_id", "minutes", "done" }]`, `weekly_goals`,
and a `revision_schedule`.

### `GET /api/v1/study-plans` — List plans

Newest first.

### `GET /api/v1/study-plans/{plan_id}` — Get one plan

### `PATCH /api/v1/study-plans/{plan_id}/tasks/{task_index}` — Update a task

Body: `{ "done": true }`. Marks a daily task done (or not done).

### `DELETE /api/v1/study-plans/{plan_id}` — Delete a plan

Returns `204`.

## Progress

### `POST /api/v1/progress/sessions` — Log a study session

Body: `{ "activity_type": "reading", "duration_minutes": 30,
"document_id": "...", "date": "2026-11-22" }`. `activity_type` is
`reading` | `chat` | `flashcards` | `quiz`; `duration_minutes` 1–1440;
`document_id` and `date` optional (defaults to today). Returns `201`.

### `GET /api/v1/progress/stats` — Statistics

Returns `{ "total_minutes", "streak_days", "total_documents",
"total_quizzes_taken", "average_quiz_score", "flashcards_known",
"flashcards_total" }`. `average_quiz_score` is a percentage (0–100) or
`null` when no quiz has been taken.

### `GET /api/v1/progress/activity` — Daily activity

Query: `days` (default 30). Returns `[{ "date", "minutes" }]`,
oldest first, for activity charts.

## Health

### `GET /health` — Health check

No auth. Returns `{ "status": "ok", "app": "AI Study Assistant",
"version": "1.0.0" }`.
