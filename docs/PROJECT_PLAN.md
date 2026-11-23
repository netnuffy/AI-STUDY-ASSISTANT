# AI Study Assistant — Project Plan

**Version:** 1.0 · **Date:** 22 November 2026
**Stack:** Next.js · Tailwind CSS · FastAPI · PostgreSQL · ChromaDB · Gemini API
**Status:** Backend built and verified on 22 Nov 2026 — 130/130 tests passing, Alembic migrations verified (0001 creates 9 tables, 0002 adds summary fields, 0003 adds weekly_goals + revision_schedule to study_plans; up and down), server boots with 27 routes. Step 4 (22 Nov): `Document` model renamed to `StudyDocument` to match spec; re-verified. Step 5 (22 Nov): upload size limit changed 50 MB → 25 MB to match spec; 2 new upload tests added. Step 6 (22 Nov): password-protected PDF check added to extraction; 7 real PyMuPDF extraction tests added. Step 7 (22 Nov): summarizer extended with key_concepts + important_questions (new migration 0002); 11 new summary tests added. Step 8 (22 Nov): RAG verified end-to-end with real ChromaDB; no-results fallback + empty-chunks guard added; 17 new RAG tests added. Step 9 (22 Nov): flashcard generation hardened (defensive normalization + dedupe vs response and DB); list orders unknown cards first; 20 new flashcard tests added. Step 10 (22 Nov): quiz system extended from MCQ-only to three types (multiple-choice, true/false, short answer with fuzzy grading); 26 new quiz tests added. Step 11 (22 Nov): study planner extended with weekly goals + revision schedule (new migration 0003); past exam dates rejected; prompt now includes real document IDs; 21 new planner tests added. Step 12 (22 Nov): Next.js 14 frontend built — 9 pages (landing, login, register, dashboard, upload, chat, flashcards, quiz, planner), Tailwind + shadcn/ui; production build passes (type-check + lint), smoke-tested; no backend changes needed (CORS already allowed localhost:3000). Step 13 (22 Nov): modern dashboard — added GET /summaries/recent and GET /quizzes/attempts/recent endpoints (no migration) + redesigned dashboard page (greeting, 4 stat cards incl. flashcards known/total, recent summaries with previews, colour-coded quiz scores, documents, activity); 11 new tests added; responsive (2-col stats on phones, stacked sections below lg). Step 14 (22 Nov): Railway deployment prep — Dockerfile rewritten ($PORT, migrations on startup via start.sh, non-root user, healthcheck, .dockerignore), railway.json added, requirements.txt re-pinned to the verified versions (FastAPI 0.165, ChromaDB 1.5.9, PyMuPDF 2.1) with test deps split into requirements-dev.txt, DATABASE_URL normalized to postgresql+psycopg:// in config (Railway's Postgres URL has no driver); fresh-venv install + full suite 130/130 passing, start.sh verified end to end (migrations 0001→0003, 9 tables, /health 200 on $PORT). Step 15 (22 Nov): Vercel deployment prep — production next.config.mjs (reactStrictMode, poweredByHeader off, 5 security headers), minimal vercel.json, engines node >=18.18, .env.production.example + .gitignore hardened (.env, .env.production), api.ts console guard when a deployed page talks to localhost; verified: build with a test API URL bakes it into the bundle, default build passes, production server smoke-tested (/, /login, /register, /dashboard all 200, headers present, x-powered-by absent). Step 16 (22 Nov): GitHub repository setup — professional root README.md (7 badges, features, screenshots, installation guide, config table), docs/API.md (all 27 endpoints, from the live OpenAPI spec), MIT LICENSE (2026 lixiy), CONTRIBUTING.md, root .gitignore, docs/ copies of the deployment guides + this plan, and 8 real screenshots in docs/screenshots/ taken with Playwright + Firefox from the running app (Chromium's download from storage.googleapis.com kept failing; Firefox came from Playwright's CDN with no approval). First screenshot tour failed on CORS — the preview frontend ran on port 3100 but the backend only allows localhost:3000, so the frontend now runs on port 3000 (scripts/screenshot_tour.py documents this). Git repo initialized (main, author lixiy <lixiyindia@gmail.com>), first commit 158 files; full-project zip made with git archive. Guide: GITHUB_SETUP.md.

---

## 1. Project Overview

An AI-powered study platform where users upload PDF study material (textbooks, notes, research papers) and get:

- Automatic AI summaries of each document
- A chat interface that answers questions **only from the uploaded PDFs** (RAG)
- Auto-generated flashcards and quizzes from the document content
- A personalised study plan based on the user's goals and deadlines
- A dashboard with progress tracking (study streaks, quiz scores, time spent)

### Target users

Students and self-learners who study from PDFs and want an AI tutor grounded in their own material.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                          │
│              Next.js 14+ (App Router) + Tailwind CSS             │
│   Pages: Auth · Dashboard · Library · Reader · Chat · Quiz ·     │
│          Flashcards · Study Plan · Progress                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │  REST API (JSON) + JWT
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND — FastAPI (Python)                    │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  Auth Module │  │  PDF Module  │  │     AI Services        │  │
│  │  JWT + bcrypt│  │  Upload ·    │  │  · Summariser          │  │
│  │  Register /  │  │  Extract     │  │  · RAG QA Engine       │  │
│  │  Login /     │  │  (PyMuPDF)   │  │  · Flashcard Generator │  │
│  │  Refresh     │  │  Chunking    │  │  · Quiz Generator      │  │
│  └──────────────┘  └──────┬───────┘  │  · Study Plan Generator│  │
│                          │          └───────┬────────────────┘  │
│  ┌──────────────┐        │                  │                    │
│  │ Study Module │        │                  │                    │
│  │ Plans · Quiz │        │                  │                    │
│  │ Attempts ·   │        │                  │                    │
│  │ Progress     │        │                  │                    │
│  └──────────────┘        │                  │                    │
└────────────┬─────────────┼──────────────────┼────────────────────┘
             │             │                  │
      ┌──────▼──────┐ ┌────▼───────┐  ┌──────▼───────────────────┐
      │ PostgreSQL  │ │ ChromaDB   │  │  Google Gemini API       │
      │ (SQLAlchemy)│ │ (Vector    │  │  · gemini-3.5-flash      │
      │ Users · Docs│ │  Store)    │  │    (generation)          │
      │ Summaries · │ │ Embeddings │  │  · gemini-embedding-2    │
      │ Flashcards ·│ │ + metadata │  │    (embeddings)          │
      │ Quizzes ·   │ │ per user / │  │                          │
      │ Plans ·     │ │ per doc    │  │                          │
      │ Progress    │ │            │  │                          │
      └─────────────┘ └────────────┘  └──────────────────────────┘
```

### How the pieces fit together

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | Next.js 14 (App Router), Tailwind CSS, shadcn/ui | UI, routing, file upload, chat UI, quiz/flashcard UI, charts |
| Backend | FastAPI, SQLAlchemy, Alembic, Pydantic | REST API, business logic, background jobs (Celery or FastAPI BackgroundTasks) |
| Relational DB | PostgreSQL | Users, documents, summaries, flashcards, quizzes, attempts, plans, progress |
| Vector DB | ChromaDB | PDF text chunks + embeddings, filtered per user and per document |
| LLM | Google Gemini API | Summaries, RAG answers, flashcards, quizzes, study plans |
| File storage | Local disk (dev) → S3 / Cloudflare R2 (prod) | Uploaded PDF files |
| Auth | JWT access + refresh tokens, bcrypt password hashing | Secure login, protected routes |

---

## 3. Folder Structure

```
ai-study-assistant/
├── README.md
├── docker-compose.yml              # Postgres + ChromaDB + backend + frontend
├── .env.example
│
├── frontend/                       # ── Next.js app ──
│   ├── package.json
│   ├── next.config.mjs
│   ├── tailwind.config.ts          # shadcn theme (CSS-variable colors)
│   ├── tsconfig.json
│   ├── components.json             # shadcn config
│   ├── .env.local.example          # NEXT_PUBLIC_API_URL
│   ├── README.md
│   ├── public/
│   └── src/
│       ├── app/
│       │   ├── layout.tsx          # AuthProvider + navbar + toaster
│       │   ├── globals.css         # shadcn light/dark tokens
│       │   ├── page.tsx            # Landing
│       │   ├── login/page.tsx
│       │   ├── register/page.tsx
│       │   ├── dashboard/page.tsx  # Stats, activity, log session, recent docs
│       │   ├── upload/page.tsx     # Upload + documents + summary viewer
│       │   ├── chat/page.tsx       # RAG Q&A chat with page sources
│       │   ├── flashcards/page.tsx
│       │   ├── quiz/page.tsx       # Generate, take, results, attempts
│       │   └── planner/page.tsx    # Create plans, daily checklist, goals
│       ├── components/
│       │   ├── ui/                 # shadcn/ui primitives (button, card, dialog…)
│       │   ├── navbar.tsx
│       │   ├── protected.tsx       # Auth guard for app pages
│       │   └── document-picker.tsx # Shared doc dropdown
│       └── lib/
│           ├── api.ts              # fetch client + token refresh + login
│           ├── auth.tsx            # AuthProvider / useAuth
│           ├── types.ts            # Types mirroring backend schemas
│           └── utils.ts            # cn()
│       │   ├── authStore.ts
│       │   └── chatStore.ts
│       └── types/
│           └── index.ts                # Shared TypeScript types
│
├── backend/                        # ── FastAPI app (BUILT 22 Nov 2026) ──
│   ├── main.py                     # Entry point: uvicorn main:app
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── Dockerfile
│   ├── docker-compose.yml          # postgres + chromadb + api
│   ├── .env.example
│   ├── README.md
│   │
│   ├── app/
│   │   └── application.py          # create_app(): middleware, handlers, routers
│   │
│   ├── api/
│   │   └── v1/                     # Versioned REST API
│   │       ├── router.py           # Aggregates all routers
│   │       ├── deps.py             # get_current_user, auth dependencies
│   │       ├── auth.py             # POST /register, /login, /refresh; GET /me
│   │       ├── documents.py        # Upload, list, delete, status
│   │       ├── summaries.py        # Get / regenerate summary
│   │       ├── chat.py             # POST /chat (RAG Q&A), GET /chat/history
│   │       ├── flashcards.py       # Generate, list, review
│   │       ├── quizzes.py          # Generate, submit, results
│   │       ├── study_plans.py      # Generate, list, update
│   │       └── progress.py         # Stats, streaks, activity
│   │
│   ├── core/                       # Cross-cutting infrastructure
│   │   ├── config.py               # Settings (env vars, Pydantic Settings)
│   │   ├── security.py             # bcrypt hashing, JWT encode/decode
│   │   ├── logging.py              # Logging configuration
│   │   ├── exceptions.py           # AppException hierarchy + handlers
│   │   ├── chroma.py               # ChromaDB client (local or HTTP mode)
│   │   └── gemini.py               # Gemini API client wrapper
│   │
│   ├── database/
│   │   ├── base.py                 # DeclarativeBase + TimestampMixin
│   │   └── session.py              # Engine, SessionLocal, get_db
│   │
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── study_document.py
│   │   ├── summary.py
│   │   ├── flashcard.py
│   │   ├── quiz.py                 # Quiz + QuizAttempt
│   │   ├── study_plan.py
│   │   ├── progress.py             # StudySession
│   │   └── chat_message.py
│   │
│   ├── schemas/                    # Pydantic request/response schemas
│   │   ├── common.py               # Paginated[T]
│   │   ├── user.py
│   │   ├── document.py
│   │   ├── chat.py
│   │   ├── flashcard.py
│   │   ├── quiz.py
│   │   ├── study_plan.py
│   │   └── progress.py
│   │
│   ├── services/                   # Business logic (one module per feature)
│   │   ├── auth_service.py
│   │   ├── document_service.py     # Upload pipeline orchestration + background processing
│   │   ├── pdf_service.py          # Text extraction (PyMuPDF), chunking
│   │   ├── embedding_service.py    # Gemini embeddings → ChromaDB
│   │   ├── rag_service.py          # Retrieval + grounded answering
│   │   ├── summary_service.py      # Map-reduce summarisation
│   │   ├── flashcard_service.py    # Flashcard generation prompts
│   │   ├── quiz_service.py         # Quiz generation prompts + grading
│   │   ├── plan_service.py         # Study plan generation
│   │   └── progress_service.py     # Streaks, stats aggregation
│   │
│   ├── utils/
│   │   ├── helpers.py              # slugify, safe_filename
│   │   └── pagination.py
│   │
│   ├── alembic/                    # DB migrations
│   │   ├── env.py
│   │   └── versions/
│   │       ├── 0001_initial.py     # Creates all 9 tables
│   │       └── 0002_add_summary_fields.py  # key_concepts + important_questions on summaries
│   │
│   └── tests/                      # pytest (SQLite, AI pipeline mocked)
│       ├── conftest.py
│       ├── test_health.py
│       ├── test_auth.py
│       ├── test_documents.py
│       ├── test_pdf_service.py
│       ├── test_summary_service.py
│       ├── test_summaries.py
│       ├── test_embedding_service.py
│       ├── test_rag_service.py
│       ├── test_chat.py
│       ├── test_flashcard_service.py
│       ├── test_flashcards.py
│       ├── test_quiz_service.py
│       ├── test_quizzes.py
│       ├── test_plan_service.py
│       └── test_study_plans.py
│
└── uploads/                            # Dev-only local PDF storage (gitignored)
```

---

## 4. Database Schema (PostgreSQL)

### `users`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| email | VARCHAR, unique | Login identifier |
| hashed_password | VARCHAR | bcrypt |
| full_name | VARCHAR | |
| created_at / updated_at | TIMESTAMP | |

### `documents`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | Owner |
| title | VARCHAR | From filename or metadata |
| filename | VARCHAR | Stored file name |
| file_path | VARCHAR | Storage path |
| page_count | INT | |
| status | ENUM | `uploading`, `processing`, `ready`, `failed` |
| created_at | TIMESTAMP | |

### `summaries`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| document_id | UUID FK → documents, unique | One summary per document |
| content | TEXT | Markdown summary |
| key_points | JSONB | Bullet list of key points |
| key_concepts | JSONB | Key terms with one-line definitions `[{term, definition}]` |
| important_questions | JSONB | Exam-style questions (list of strings) |
| created_at | TIMESTAMP | |

### `flashcards`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| document_id | UUID FK → documents | |
| user_id | UUID FK → users | |
| front | TEXT | Question / term |
| back | TEXT | Answer / definition |
| difficulty | ENUM | `easy`, `medium`, `hard` |
| last_reviewed_at | TIMESTAMP, nullable | Spaced repetition |
| review_count | INT, default 0 | |
| known | BOOLEAN, default false | |

### `quizzes`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| document_id | UUID FK → documents | |
| user_id | UUID FK → users | |
| title | VARCHAR | |
| questions | JSONB | Array of questions, each with a `type`: multiple_choice {question, options[2-4], correct_index, explanation}, true_false {question, correct, explanation}, short_answer {question, answer, explanation} |
| created_at | TIMESTAMP | |

### `quiz_attempts`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| quiz_id | UUID FK → quizzes | |
| user_id | UUID FK → users | |
| score | INT | Correct answers |
| total | INT | Total questions |
| answers | JSONB | User's selected options |
| completed_at | TIMESTAMP | |

### `study_plans`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| title | VARCHAR | e.g. "Biology Final — 2 Weeks" |
| goal | TEXT | User's goal text |
| exam_date | DATE, nullable | |
| daily_minutes | INT | Target minutes per day |
| tasks | JSONB | Array of {date, topic, document_id, minutes, done} |
| weekly_goals | JSONB | Array of {week, goal, start_date, end_date} |
| revision_schedule | JSONB | Array of {date, topic, minutes} |
| created_at | TIMESTAMP | |

### `study_sessions` (progress tracking)
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| document_id | UUID FK → documents, nullable | |
| activity_type | ENUM | `reading`, `chat`, `flashcards`, `quiz` |
| duration_minutes | INT | |
| date | DATE | For streaks and charts |

---

## 5. ChromaDB Design (Vector Store)

- **One collection:** `pdf_chunks`
- **Embedding model:** `gemini-embedding-2` (Gemini, 3072 dims)
- **Chunking:** ~1,000 characters per chunk, 200-character overlap, split on sentence boundaries
- **Metadata stored per chunk:**

```json
{
  "user_id": "uuid",
  "document_id": "uuid",
  "page": 12,
  "chunk_index": 3,
  "source_title": "Biology Chapter 5"
}
```

- **Isolation:** every query filters by `user_id` (and `document_id` when chatting about one PDF), so users can never retrieve each other's content.
- **Deletion:** deleting a document deletes its chunks from ChromaDB and its rows from PostgreSQL.

---

## 6. RAG Pipeline (Question Answering)

```
User question
      │
      ▼
1. Embed question (Gemini gemini-embedding-2)
      │
      ▼
2. ChromaDB similarity search
   · top_k = 5 chunks
   · filter: user_id (+ document_id if selected)
      │
      ▼
3. Build prompt: system instruction + retrieved chunks + question
   · "Answer ONLY from the provided context. If the answer is not
      in the context, say you don't know."
      │
      ▼
4. Gemini gemini-3.5-flash generates the answer
      │
      ▼
5. Return answer + source citations (page numbers)
```

**Why this design:** grounding answers in retrieved chunks prevents hallucination and lets the user verify every answer against the source page.

---

## 7. PDF Processing Pipeline (on upload)

```
Upload PDF
    │
    ▼
1. Save file → storage, create `documents` row (status: uploading)
    │
    ▼
2. Background task starts (status: processing)
    │   a. Extract text per page — PyMuPDF (fitz)
    │   b. Clean text (remove headers/footers, fix hyphenation)
    │   c. Chunk text (1,000 chars, 200 overlap)
    │   d. Embed chunks (Gemini) → upsert into ChromaDB
    │   e. Generate summary (map-reduce: summarise each chunk,
    │      then summarise the summaries) → `summaries` row
    │
    ▼
3. status: ready → user can chat, generate flashcards & quizzes
```

Processing runs in the background so uploads return immediately; the frontend polls `GET /documents/{id}` for status.

---

## 8. API Endpoints (FastAPI, prefix `/api/v1`)

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Returns access + refresh JWT |
| POST | `/auth/refresh` | Rotate access token |
| GET | `/auth/me` | Current user profile |

### Documents
| Method | Endpoint | Description |
|---|---|---|
| POST | `/documents/upload` | Upload PDF (multipart), starts processing |
| GET | `/documents` | List user's documents |
| GET | `/documents/{id}` | Document detail + processing status |
| DELETE | `/documents/{id}` | Delete doc, chunks, summary, flashcards, quizzes |

### Summaries
| Method | Endpoint | Description |
|---|---|---|
| GET | `/documents/{id}/summary` | Get summary |
| GET | `/summaries/recent` | Recent summaries for the dashboard |
| POST | `/documents/{id}/summary/regenerate` | Regenerate with different style (short / detailed) |

### Chat (RAG)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/chat` | `{ document_id?, question }` → answer + sources |
| GET | `/chat/history` | Past Q&A for a document |

### Flashcards
| Method | Endpoint | Description |
|---|---|---|
| POST | `/documents/{id}/flashcards/generate` | Generate N flashcards |
| GET | `/documents/{id}/flashcards` | List flashcards |
| PATCH | `/flashcards/{id}/review` | Mark known/unknown, update spaced repetition |

### Quizzes
| Method | Endpoint | Description |
|---|---|---|
| POST | `/documents/{id}/quizzes/generate` | Generate quiz (N questions, difficulty, question types) |
| GET | `/quizzes/{id}` | Get quiz questions (without answers) |
| POST | `/quizzes/{id}/submit` | Submit answers → score + explanations |
| GET | `/quizzes/{id}/attempts` | Attempt history |
| GET | `/quizzes/attempts/recent` | Recent attempts across quizzes (dashboard) |

### Study Plans
| Method | Endpoint | Description |
|---|---|---|
| POST | `/study-plans` | Generate plan (daily tasks, weekly goals, revision schedule) from goal + exam date + docs |
| GET | `/study-plans` | List plans |
| PATCH | `/study-plans/{id}/tasks/{index}` | Mark a task done |

### Progress
| Method | Endpoint | Description |
|---|---|---|
| POST | `/progress/sessions` | Log a study session |
| GET | `/progress/stats` | Streak, total minutes, quiz averages, per-doc progress |
| GET | `/progress/activity` | Daily activity for charts (last 30 days) |

---

## 9. Feature Breakdown

### 9.1 User Authentication
- Email + password registration and login
- JWT access token (15 min) + refresh token (7 days, httpOnly cookie)
- bcrypt password hashing, protected routes via `get_current_user` dependency
- (Later) Google OAuth via NextAuth or a FastAPI OAuth flow

### 9.2 PDF Upload
- Drag-and-drop, max 25 MB per file, PDF only (validated by MIME + magic bytes)
- Upload progress bar, processing status indicator
- Stored locally in dev, S3/R2 in production

### 9.3 PDF Text Extraction
- PyMuPDF (`fitz`) for fast, accurate extraction
- Fallback: `pdfplumber` for tables, `pytesseract` OCR for scanned pages (Phase 2)

### 9.4 AI Summary Generation
- Map-reduce: summarise chunks in parallel, then combine into one structured summary
- Output: overview + key points + key concepts (term + definition) + important questions, in Markdown
- Styles: Short (5 bullets) / Standard / Detailed

### 9.5 RAG Question Answering
- Chat UI with conversation history per document
- Answers grounded in retrieved chunks, with page-number citations
- "I don't know" fallback when the answer is not in the PDFs
- Option to ask across **all** uploaded documents, not just one

### 9.6 Flashcard Generation
- Gemini generates Q/A pairs from the document's key concepts
- Deck view with flip animation, shuffle, mark known/unknown
- Simple spaced repetition: unknown cards resurface first

### 9.7 Quiz Generation
- Three question types: multiple-choice (2–4 options), true/false, short answer (fuzzy-graded); configurable count (1–20), difficulty, and type filter
- Instant grading with explanations for each answer; answers hidden until submit
- Attempts saved for progress tracking

### 9.8 Study Plan Generator
- Input: goal, exam date, daily available minutes, selected documents
- Gemini generates three outputs in one call: daily tasks, weekly goals, and a spaced revision schedule
- Checklist UI, tasks marked done, progress bar per plan

### 9.9 User Dashboard
- At a glance: study streak, documents count, flashcards known/total, average quiz score
- Recent summaries (with previews), recent quiz scores, recent documents, quick actions (upload, chat, quiz)
- 14-day activity chart + log-a-session form

### 9.10 Progress Tracking
- Study sessions logged automatically (time on page) and manually
- Streak calculation, weekly minutes chart, quiz score trend
- Per-document progress: % of flashcards known, best quiz score

---

## 10. Environment Variables

```bash
# Backend (.env)
DATABASE_URL=postgresql://user:password@localhost:5432/study_assistant
CHROMA_HOST=localhost
CHROMA_PORT=8000
GEMINI_API_KEY=your_gemini_api_key
JWT_SECRET_KEY=your_super_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
UPLOAD_DIR=./uploads
MAX_UPLOAD_MB=25
CORS_ORIGINS=http://localhost:3000

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## 11. Development Setup

```bash
# 1. Clone and start services
git clone <repo-url> ai-study-assistant
cd ai-study-assistant
docker compose up -d postgres chromadb   # databases only

# 2. Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in GEMINI_API_KEY etc.
alembic upgrade head        # run migrations
uvicorn main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
npm install
cp .env.example .env.local
npm run dev                 # http://localhost:3000
```

API docs available at `http://localhost:8000/docs` (Swagger UI).

---

## 12. Deployment

| Component | Suggested hosting |
|---|---|
| Frontend (Next.js) | Vercel — see DEPLOYMENT_VERCEL.md |
| Backend (FastAPI) | Railway (Docker) — see DEPLOYMENT_RAILWAY.md |
| PostgreSQL | Neon / Supabase / Railway |
| ChromaDB | Self-hosted Docker on the backend host, or Chroma Cloud |
| File storage | Cloudflare R2 / AWS S3 |
| Background jobs | Celery + Redis (when PDF volume grows) |

---

## 13. Build Order (Milestones)

| Phase | Deliverable |
|---|---|
| **1 — Foundation** | Repo setup, Docker Compose, auth (register/login/JWT), DB models + migrations |
| **2 — Documents** | PDF upload, text extraction, chunking, embeddings → ChromaDB |
| **3 — Summaries + RAG** | Summary generation, chat Q&A with citations |
| **4 — Learning tools** | Flashcards + quizzes (generate, review, grade) |
| **5 — Planning + Progress** | Study plan generator, dashboard, progress tracking, streaks |
| **6 — Polish** | OCR fallback, multi-document chat, Google OAuth, deployment |

---

## 14. Key Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Gemini API cost at scale | Cache summaries/flashcards/quizzes in Postgres; use `gemini-3.5-flash` (cheap) for generation; rate-limit per user |
| Large PDFs slow to process | Background jobs + status polling; chunk-level parallelism; 25 MB cap |
| Hallucinated answers | Strict RAG grounding prompt + citations; "I don't know" fallback |
| Scanned PDFs with no text layer | OCR fallback (Tesseract) in Phase 2; warn user if extraction yields little text |
| Vector DB growth | Per-user filtering; delete chunks with documents; consider persistent Chroma with backups |
