# AI Study Assistant — Backend

Production-ready FastAPI backend for the AI Study Assistant: upload PDFs, get AI
summaries, ask questions with RAG, generate flashcards and quizzes, build study
plans, and track progress.

## Tech Stack

- **FastAPI** + **Uvicorn** — API framework and server
- **PostgreSQL** + **SQLAlchemy 2.0** + **Alembic** — relational data and migrations
- **ChromaDB** — vector store for PDF chunks (RAG)
- **Google Gemini API** — summaries, Q&A, flashcards, quizzes, study plans
- **PyMuPDF** — PDF text extraction
- **JWT** (access + refresh) + **bcrypt** — authentication
- **Pydantic v2 / pydantic-settings** — validation and environment config

## Folder Structure

```
backend/
├── main.py                 # Entry point (uvicorn main:app)
├── requirements.txt
├── pyproject.toml
├── alembic.ini
├── docker-compose.yml      # postgres + chromadb + api
├── Dockerfile
├── .env.example
│
├── app/
│   └── application.py      # create_app(): middleware, handlers, routers
│
├── api/
│   └── v1/                 # Versioned REST API
│       ├── router.py       # Aggregates all v1 routers
│       ├── deps.py         # get_current_user, auth dependencies
│       ├── auth.py         # Register, login, refresh, /me
│       ├── documents.py    # Upload, list, get, delete PDFs
│       ├── summaries.py    # Get / regenerate summary
│       ├── chat.py         # RAG Q&A + history
│       ├── flashcards.py   # Generate, list, review
│       ├── quizzes.py      # Generate, take, submit, attempts
│       ├── study_plans.py  # Generate, list, update tasks
│       └── progress.py     # Sessions, stats, activity
│
├── core/                   # Cross-cutting infrastructure
│   ├── config.py           # Settings from environment variables
│   ├── security.py         # bcrypt hashing + JWT helpers
│   ├── logging.py          # Logging configuration
│   ├── exceptions.py       # AppException hierarchy + handlers
│   ├── gemini.py           # Gemini API client (lazy import)
│   └── chroma.py           # ChromaDB client (local or HTTP mode)
│
├── database/
│   ├── base.py             # DeclarativeBase + TimestampMixin
│   └── session.py          # Engine, SessionLocal, get_db
│
├── models/                 # SQLAlchemy ORM models
│   ├── user.py
│   ├── study_document.py         # + DocumentStatus enum
│   ├── summary.py
│   ├── flashcard.py        # + Difficulty enum
│   ├── quiz.py             # Quiz + QuizAttempt
│   ├── study_plan.py
│   ├── progress.py         # StudySession + ActivityType enum
│   └── chat_message.py     # + ChatRole enum
│
├── schemas/                # Pydantic request/response models
│   ├── common.py           # Paginated[T]
│   ├── user.py
│   ├── document.py
│   ├── chat.py
│   ├── flashcard.py
│   ├── quiz.py
│   ├── study_plan.py
│   └── progress.py
│
├── services/               # Business logic (one module per feature)
│   ├── auth_service.py
│   ├── document_service.py # Upload pipeline orchestration
│   ├── pdf_service.py      # Extraction + chunking
│   ├── embedding_service.py
│   ├── rag_service.py
│   ├── summary_service.py
│   ├── flashcard_service.py
│   ├── quiz_service.py
│   ├── plan_service.py
│   └── progress_service.py
│
├── utils/
│   ├── helpers.py          # slugify, safe_filename
│   └── pagination.py
│
├── alembic/                # DB migrations (0001 creates all tables, 0002 adds summary fields)
└── tests/                  # pytest: health, auth, documents, pdf extraction, summaries, RAG, flashcards, quizzes, study plans
```

## Quick Start

### Option A — Docker (recommended)

```bash
cp .env.example .env        # fill in GEMINI_API_KEY and JWT_SECRET_KEY
docker compose up --build   # postgres + chromadb + api on :8000
docker compose exec api alembic upgrade head
```

### Option B — Local Python

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in GEMINI_API_KEY and JWT_SECRET_KEY

# Start Postgres + ChromaDB (or run only those two from compose):
docker compose up -d postgres chromadb

alembic upgrade head        # create tables
uvicorn main:app --reload   # http://localhost:8000
```

API docs: **http://localhost:8000/docs** (Swagger UI)

## Environment Variables

See `.env.example`. The important ones:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `GEMINI_API_KEY` | Google Gemini API key |
| `JWT_SECRET_KEY` | Secret for signing JWTs (use a long random value!) |
| `CHROMA_MODE` | `local` (embedded) or `http` (Chroma server) |
| `UPLOAD_DIR` | Where uploaded PDFs are stored |
| `MAX_UPLOAD_MB` | Max PDF size (default 25) |

## API Overview (prefix `/api/v1`)

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me` |
| Documents | `POST /documents/upload`, `GET /documents`, `GET /documents/{id}`, `DELETE /documents/{id}` |
| Summaries | `GET /documents/{id}/summary`, `POST /documents/{id}/summary/regenerate` |
| Chat | `POST /chat`, `GET /chat/history` |
| Flashcards | `POST /documents/{id}/flashcards/generate`, `GET /documents/{id}/flashcards`, `PATCH /flashcards/{id}/review` |
| Quizzes | `POST /documents/{id}/quizzes/generate`, `GET /quizzes/{id}`, `POST /quizzes/{id}/submit`, `GET /quizzes/{id}/attempts` |
| Study plans | `POST /study-plans`, `GET /study-plans`, `GET /study-plans/{id}`, `PATCH /study-plans/{id}/tasks/{index}`, `DELETE /study-plans/{id}` |
| Progress | `POST /progress/sessions`, `GET /progress/stats`, `GET /progress/activity` |

All endpoints except `/auth/*` and `/health` require a JWT:
`Authorization: Bearer <access_token>`

## How PDF Processing Works

1. Upload returns immediately with `status: uploading`.
2. A background task extracts text (PyMuPDF), chunks it (1,000 chars, 200 overlap),
   embeds chunks (Gemini `gemini-embedding-2`) into ChromaDB, and generates a
   summary (map-reduce with Gemini).
3. The document becomes `status: ready`. On failure it becomes `failed` with an
   `error_message`. The frontend polls `GET /documents/{id}` for status.

## Deployment (Railway)

The backend is ready to deploy on Railway from its Dockerfile. Set the
service's **Root Directory to `backend`**, add the PostgreSQL plugin, and set
`DATABASE_URL=${{Postgres.DATABASE_URL}}` plus `GEMINI_API_KEY` and
`JWT_SECRET_KEY`. `start.sh` runs migrations, then starts uvicorn on
Railway's `$PORT`. Attach a Volume at `/app/data` (with
`UPLOAD_DIR=/app/data/uploads` and `CHROMA_PERSIST_DIR=/app/data/chroma_data`)
or uploads and the vector index are lost on redeploy. Full checklist:
`~/workspace/your_files/DEPLOYMENT_RAILWAY.md`.

## Testing

```bash
pytest -q
```

Tests use an in-memory SQLite database and mock the AI pipeline, so no
Postgres, Gemini, or ChromaDB is needed to run them. PyMuPDF is needed for
the extraction tests (`pip install -r requirements.txt` covers it).

## Notes

- Gemini and ChromaDB are imported lazily: the app starts and serves auth /
  document endpoints even if those packages (or the API key) are missing.
  AI features return a clear `502` error until they are configured.
- Deleting a document removes its file, its ChromaDB chunks, and all related
  rows (summary, flashcards, quizzes, chat history) via cascade.
