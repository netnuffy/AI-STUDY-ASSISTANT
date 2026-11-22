# AI Study Assistant

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
![Node 18+](https://img.shields.io/badge/node-%3E%3D18.18-green.svg)
![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.165-009688.svg)
![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791.svg)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)

Upload your PDFs and study smarter — AI summaries, chat with your documents,
flashcards, quizzes, and a study planner, in one place.

Turn a 200-page textbook into a 2-minute summary, ask it questions and get
answers with page citations, drill yourself with flashcards and quizzes, and
follow a day-by-day plan up to your exam.

## Features

### Documents & AI

- **PDF upload** — drag in a PDF (up to 25 MB); text is extracted with
  PyMuPDF, chunked, and embedded into ChromaDB automatically.
- **AI summaries** — short, standard, or detailed summaries with key points,
  key concepts, and important questions, generated with Google Gemini.
- **Chat with your PDF (RAG)** — ask questions in plain language and get
  grounded answers with page citations. Ask one document or all of them at
  once. If the answer isn't in your documents, it says so instead of guessing.

### Study tools

- **Flashcards** — generate question/answer cards from any document, study
  them with click-to-flip cards, and mark what you know. Unknown cards
  resurface first.
- **Quizzes** — multiple-choice, true/false, and short-answer questions
  (short answers are graded with fuzzy matching). Full attempt history and
  per-question review.

### Planning & progress

- **AI study planner** — give it a subject, exam date, and hours per day;
  get a daily plan, weekly goals, and a revision schedule.
- **Dashboard** — study streak, documents, flashcards known, quiz average,
  recent summaries, and recent quiz scores at a glance.
- **Progress tracking** — log study sessions (including offline ones) and
  see your activity over the last 14 days.

### Accounts & security

- **JWT auth** — register/login with 15-minute access tokens and 7-day
  refresh tokens. Your documents, chats, and plans belong to you only.

## Screenshots

| | |
|---|---|
| ![Landing page](docs/screenshots/landing.png) | ![Dashboard](docs/screenshots/dashboard.png) |
| *Landing page* | *Dashboard — streak, stats, recent summaries & quiz scores* |
| ![Upload](docs/screenshots/upload.png) | ![Chat](docs/screenshots/chat.png) |
| *Upload a PDF and read its AI summary* | *Chat with your PDF — answers with page citations* |
| ![Flashcards](docs/screenshots/flashcards.png) | ![Quiz](docs/screenshots/quiz.png) |
| *Flashcards — click to flip, mark what you know* | *Quiz — multiple-choice, true/false, short answer* |
| ![Planner](docs/screenshots/planner.png) | ![Login](docs/screenshots/login.png) |
| *Study planner — daily tasks, weekly goals, revision* | *Login* |

Screenshots are generated from a running app with demo data — see
[`scripts/screenshot_tour.py`](scripts/screenshot_tour.py) to regenerate them.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router, TypeScript), Tailwind CSS, shadcn/ui |
| Backend | FastAPI, SQLAlchemy, Alembic, Pydantic |
| Database | PostgreSQL 16 |
| Vector store | ChromaDB |
| AI | Google Gemini (`gemini-1.5-flash`, `text-embedding-004`) |
| PDF | PyMuPDF |
| Auth | JWT (access + refresh), bcrypt |
| Deployment | Railway (backend), Vercel (frontend) |

## Project structure

```
ai-study-assistant/
├── backend/                 # FastAPI app
│   ├── main.py              # Entry point (uvicorn main:app)
│   ├── api/v1/              # Routers: auth, documents, summaries, chat,
│   │                        #   flashcards, quizzes, study_plans, progress
│   ├── core/                # Config, security, Gemini + Chroma clients
│   ├── database/            # Engine, session, base + TimestampMixin
│   ├── models/              # SQLAlchemy models (9 tables)
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # PDF, summary, RAG, flashcard, quiz, planner
│   ├── alembic/             # Migrations (0001–0003)
│   ├── tests/               # pytest suite (130 tests)
│   ├── Dockerfile           # Railway build (migrations + uvicorn on $PORT)
│   ├── railway.json         # Railway build/deploy config
│   └── requirements.txt     # Pinned runtime dependencies
├── frontend/                # Next.js 14 app
│   ├── src/app/             # Pages: landing, login, register, dashboard,
│   │                        #   upload, chat, flashcards, quiz, planner
│   ├── src/components/      # Navbar, shadcn/ui primitives
│   ├── src/lib/             # API client, auth context, types
│   ├── next.config.mjs      # Strict mode, security headers
│   └── vercel.json          # Vercel config
├── docs/                    # API reference, deployment guides, screenshots
└── scripts/                 # Screenshot tour generator
```

## Installation

### Prerequisites

- **Python 3.12+**
- **Node.js 18.18+** (and npm)
- **Docker + Docker Compose** — for PostgreSQL and ChromaDB
  (or run your own Postgres 16 + Chroma server)
- **A Google Gemini API key** — free at
  [Google AI Studio](https://aistudio.google.com/app/apikey).
  Without it the app runs, but AI features (summaries, chat, flashcards,
  quizzes, planner) return a 502.

### Quick start (Docker — recommended)

```bash
git clone https://github.com/netnuffy/ai-study-assistant.git
cd ai-study-assistant/backend

cp .env.example .env        # fill in GEMINI_API_KEY and JWT_SECRET_KEY
docker compose up --build   # postgres + chromadb + api on :8000
```

Database migrations run automatically on container start. The API is then
at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`.

### Quick start (local Python + Docker services)

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt               # runtime + test deps
cp .env.example .env        # fill in GEMINI_API_KEY and JWT_SECRET_KEY

docker compose up -d postgres chromadb   # database + vector store only

alembic upgrade head        # create tables
uvicorn main:app --reload   # http://localhost:8000
```

For this setup, set `CHROMA_MODE=http` and `CHROMA_PORT=8001` in `.env`
(the Chroma container maps to port 8001 on the host).

### Frontend

```bash
cd frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
npm install
npm run dev                        # http://localhost:3000
```

The backend's default CORS config already allows `http://localhost:3000`.

### Demo data

To explore with sample content instead of an empty account:

1. Register an account with the email `demo@demo.com` (any name, password
   `demo1234`) — or any email, then edit the address in the script.
2. From `backend/`, with the API's database configured:

```bash
DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/study_assistant" \
  python seed_demo.py
```

This adds two documents, a summary, flashcards, a quiz with an attempt,
five days of study sessions, and a study plan.

## Configuration

Backend environment variables (see `backend/.env.example` for the full
list):

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/study_assistant` | Postgres connection string |
| `GEMINI_API_KEY` | _(empty)_ | Google Gemini API key |
| `JWT_SECRET_KEY` | `change-me-in-production` | Secret for signing JWTs — generate one with `openssl rand -hex 32` |
| `CHROMA_MODE` | `local` | `local` (embedded) or `http` (Chroma server) |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | Where the embedded index lives |
| `UPLOAD_DIR` | `./uploads` | Where uploaded PDFs are stored |
| `MAX_UPLOAD_MB` | `25` | Max PDF size |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed frontend origins (JSON list) |

Frontend: `NEXT_PUBLIC_API_URL` (default `http://localhost:8000/api/v1`).
Note that `NEXT_PUBLIC_` variables are baked into the bundle at build
time — changing one requires a rebuild.

## Usage

1. **Register** an account and log in.
2. **Upload** a PDF from the Upload page. Processing takes a few seconds
   per document; the status changes to `ready` when the summary is done.
3. **Read the summary**, or **chat** with the document — ask anything and
   check the page citations.
4. **Generate flashcards** and drill them; **take a quiz** to test yourself.
5. **Create a study plan** for your exam and tick off daily tasks.
6. **Watch the dashboard** — your streak, quiz scores, and recent summaries
   all show up there.

## API documentation

Full reference: [`docs/API.md`](docs/API.md) — every endpoint with request
and response shapes and curl examples. Interactive Swagger UI runs at
`/docs` when the backend is up.

## Testing

```bash
cd backend
python -m pytest tests/ -q     # 130 tests, no API key needed (Gemini is mocked)
```

```bash
cd frontend
npm run build                  # type-check + lint + production build
```

## Deployment

- **Backend → Railway:** [`docs/DEPLOYMENT_RAILWAY.md`](docs/DEPLOYMENT_RAILWAY.md)
  — Dockerfile, `railway.json`, Postgres plugin, persistent volume.
- **Frontend → Vercel:** [`docs/DEPLOYMENT_VERCEL.md`](docs/DEPLOYMENT_VERCEL.md)
  — root directory, `NEXT_PUBLIC_API_URL`, CORS follow-up.

Architecture and build history: [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md).

## Contributing

Contributions are welcome! See [`CONTRIBUTING.md`](CONTRIBUTING.md) for
setup, branch naming, tests, and the PR process.

## License

MIT — see [`LICENSE`](LICENSE).
