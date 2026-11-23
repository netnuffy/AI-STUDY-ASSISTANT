# Step 14: Railway Deployment — FastAPI Backend

**Project:** AI Study Assistant · **Date:** 22 November 2026
**Status:** Prepared and verified — fresh install from the new `requirements.txt`
passes **130/130 tests**, and the exact Railway startup path (`start.sh` →
migrations → uvicorn on `$PORT`) was run end to end.

> What this step does NOT do: deploy anything. Railway needs your account and
> your repo, so the deploy itself is a few clicks in the Railway dashboard —
> Section 5 is the exact checklist.

---

## 1. What changed and why

The backend already had a Dockerfile from Step 2, but it was a local-dev
image. Five things had to change for Railway:

| Gap | Fix |
|---|---|
| Port hardcoded to 8000 — Railway injects `$PORT` | `start.sh` starts uvicorn on `${PORT:-8000}` |
| No migrations on startup — a fresh Railway database would have no tables | `start.sh` runs `alembic upgrade head` (with retries while Postgres starts) before the server |
| `COPY . .` with no `.dockerignore` — could copy `.env`, uploads, and local Chroma data into the image | New `.dockerignore` excludes secrets and data |
| Container ran as root | New `appuser` (uid 10001) |
| Railway's Postgres URL has no driver (`postgresql://...`) — SQLAlchemy would default to psycopg2, which isn't installed | `DATABASE_URL` is normalized to `postgresql+psycopg://` in `core/config.py` (see §4) |

## 2. Files

### `Dockerfile` (rewritten)

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads chroma_data

RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health')"

CMD ["sh", "start.sh"]
```

Notes:

- Dependencies install before the source copy, so rebuilds are cached unless
  `requirements.txt` changes.
- No build tools are installed: every package ships a prebuilt wheel for
  linux x86_64 (verified by the fresh install in §6).
- The healthcheck reads `$PORT` from the environment in Python rather than
  relying on shell expansion inside quotes.

### `start.sh` (new — the production entrypoint)

```sh
#!/bin/sh
set -e

echo "Running database migrations..."
for i in 1 2 3 4 5 6; do
  alembic upgrade head && break
  echo "Migration attempt $i/6 failed, retrying in 5s..."
  sleep 5
done
alembic upgrade head
echo "Migrations done."

echo "Starting server on port ${PORT:-8000}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
```

Why the retry loop: on the first deploy, Railway starts the API and Postgres
at the same time, so the first migration attempt can fail because the
database isn't accepting connections yet. The loop waits up to ~30s. The
final `alembic upgrade head` runs under `set -e`, so a genuinely broken
migration still fails the deploy instead of starting a server against a
half-migrated database. (A repeat run is a no-op — Alembic sees it's already
at head.)

### `railway.json` (new)

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile" },
  "deploy": {
    "healthcheckPath": "/health",
    "healthcheckTimeout": 300,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

This file lives in `backend/`, and the Railway service's **Root Directory**
must be set to `backend` (the repo also contains `frontend/`). Railway reads
`railway.json` from the service root, so putting it anywhere else won't work.

### `.dockerignore` (new)

```
.git
.env
.venv
__pycache__/
*.pyc
.pytest_cache/
uploads/
chroma_data/
tests/
```

The important line is `.env`: without it, a local `.env` with real secrets
would be baked into the image.

### `requirements.txt` (re-pinned) + `requirements-dev.txt` (new)

The old pins were from Step 2 (e.g. FastAPI 0.115.6, ChromaDB 0.5.23). The
code has evolved since, and the test suite actually runs against newer
versions — so the pins now match the verified set:

```text
fastapi==0.165.0
uvicorn[standard]==0.54.0
pydantic==2.14.4
pydantic-settings==2.16.3
python-multipart==0.0.34
email-validator==2.4.0
SQLAlchemy==2.1.9
alembic==1.20.1
psycopg[binary]==3.3.9
python-jose[cryptography]==3.5.0
bcrypt==5.0.0
google-genai==3.6.1
chromadb==1.5.9
PyMuPDF==2.1
```

> 2026-11-23: the Gemini SDK was migrated from `google-generativeai==0.8.6`
> to `google-genai==3.6.1`. The old SDK talks to the Gemini v1beta API,
> where the `text-embedding-004` model does not exist — live document
> processing and chat failed with 404 "models/text-embedding-004 is not
> found for API version v1beta". The new SDK uses the v1 API, where the
> model works. `core/gemini.py` was rewritten for the new SDK; its four
> public functions keep the same signatures.

Test-only packages moved to `requirements-dev.txt`, which includes the
runtime file and adds `pytest==9.2.0` + `httpx==0.28.1` (TestClient needs
httpx; nothing at runtime imports it — verified by grep). The Docker image
installs only `requirements.txt`, so it's smaller and faster to build.

### `.env.example` (updated)

Now documents the Railway values inline: `DATABASE_URL=${{Postgres.DATABASE_URL}}`,
`ENVIRONMENT=production`, the volume paths for uploads/Chroma, and how to
generate `JWT_SECRET_KEY` (`openssl rand -hex 32`).

## 3. Environment variables (Railway service → Variables tab)

| Variable | Value | Required |
|---|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (reference variable — see §5 step 2) | Yes |
| `GEMINI_API_KEY` | Your key from [Google AI Studio](https://aistudio.google.com/app/apikey) | Yes (AI features 502 without it) |
| `JWT_SECRET_KEY` | `openssl rand -hex 32` output | Yes |
| `ENVIRONMENT` | `production` | Recommended |
| `CORS_ORIGINS` | `["https://your-app.vercel.app"]` — your frontend URL, once deployed | Yes, after frontend deploy |
| `UPLOAD_DIR` | `/app/data/uploads` | With a Volume (§5 step 4) |
| `CHROMA_PERSIST_DIR` | `/app/data/chroma_data` | With a Volume (§5 step 4) |
| `GEMINI_MODEL` | `gemini-3.5-flash` (default) | No |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-2` (default) | No |
| `MAX_UPLOAD_MB` | `25` (default) | No |

Railway injects `PORT` automatically — do not set it yourself.

## 4. The one code change: `DATABASE_URL` normalization

Railway's Postgres plugin provides a URL like
`postgresql://postgres:xxx@host:5432/railway`. SQLAlchemy interprets a bare
`postgresql://` scheme as "psycopg2 driver", which is not installed (this
project uses psycopg 3) — the app would crash on startup with
`Can't load plugin: sqlalchemy.dialects:driver`. Rather than asking you to
hand-edit the URL in Railway, the setting normalizes it on load:

```python
@field_validator("DATABASE_URL", mode="before")
@classmethod
def _normalize_database_url(cls, value: str) -> str:
    if not isinstance(value, str):
        return value
    if value.startswith("postgres://"):
        value = "postgresql://" + value[len("postgres://"):]
    if value.startswith("postgresql://"):
        value = "postgresql+psycopg://" + value[len("postgresql://"):]
    return value
```

`postgresql+psycopg://` and `sqlite://` URLs pass through unchanged. The
validator lives in `core/config.py`, so it also covers Alembic (which reads
the URL from settings). Covered by 4 new tests in `tests/test_config.py`.

## 5. Deploy checklist (Railway dashboard)

1. **Push the repo to GitHub** (backend + frontend in one repo is fine).
2. **New Project → Deploy from GitHub repo.** Select the repo.
3. **Set the Root Directory:** service → Settings → Root Directory → `backend`.
   (Without this, Railway builds from the repo root and the Dockerfile's
   `COPY requirements.txt .` fails.)
4. **Add PostgreSQL:** project canvas → **+ New → Database → PostgreSQL**.
   Then in the API service's Variables tab, add
   `DATABASE_URL` = `${{Postgres.DATABASE_URL}}` (type it exactly like that;
   Railway resolves the reference).
5. **Add the variables** from §3 (`GEMINI_API_KEY`, `JWT_SECRET_KEY`,
   `ENVIRONMENT=production`).
6. **Attach a Volume** (service → Settings → Volumes): mount path `/app/data`,
   then set `UPLOAD_DIR=/app/data/uploads` and
   `CHROMA_PERSIST_DIR=/app/data/chroma_data`. Without this, uploaded PDFs
   and the Chroma vector index live on Railway's ephemeral filesystem and
   are **lost on every redeploy**. The database is unaffected (it's the
   Postgres plugin, not the filesystem).
7. **Deploy** (automatic on push). Watch the logs for:
   `Running database migrations...` → `Migrations done.` →
   `Starting server on port ...` → `Application startup complete.`
8. **Generate a public domain:** service → Settings → Networking →
   **Generate Domain**. Your API is then at
   `https://<your-service>.up.railway.app`, and the frontend will use
   `NEXT_PUBLIC_API_URL=https://<your-service>.up.railway.app/api/v1`.
9. **Smoke test:**
   ```bash
   curl https://<your-service>.up.railway.app/health
   # {"status":"ok","app":"AI Study Assistant","version":"1.0.0"}
   curl https://<your-service>.up.railway.app/api/v1/docs  # Swagger UI
   ```

## 6. Verification

Docker is not installed on this machine, so the image build itself happens
on Railway (that's the normal flow — Railway builds from the Dockerfile on
deploy). Everything else was verified here:

- **Fresh install:** a clean venv (`~/.venv-deploy`) installed
  `requirements-dev.txt` from scratch — every pin resolved, including
  PyMuPDF 2.1 and google-generativeai 0.8.6 — then ran the full suite:
  **130/130 tests passing** (126 existing + 4 new `DATABASE_URL`
  normalization tests).
- **Startup path:** ran `start.sh` exactly as the container does
  (`PORT=8124`, SQLite as the database): migrations 0001 → 0002 → 0003 ran,
  all 9 tables + `alembic_version` were created, the server started on port
  8124, `/health` returned 200, and the OpenAPI schema listed 27 paths.
- **Retry loop:** during that test, the first run had `alembic` missing from
  PATH — the loop logged "Migration attempt 1/6 failed, retrying in 5s..."
  exactly as designed, then the corrected run succeeded.

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Build fails: `COPY requirements.txt .` not found | Root Directory not set to `backend` | Settings → Root Directory → `backend` |
| `Can't load plugin: sqlalchemy.dialects:driver` | Old code without the URL validator | Pull the latest backend (validator added in this step) |
| Deploy loops: migrations keep failing | Postgres not ready yet, or `DATABASE_URL` wrong | Check the Postgres service is running; verify the `${{...}}` reference |
| Healthcheck fails / 502 | Server didn't start | Read the deploy logs — the last lines say whether migrations or uvicorn failed |
| App works but AI endpoints return 502 | `GEMINI_API_KEY` missing/invalid | Set it in Variables and redeploy |
| CORS errors from the frontend | `CORS_ORIGINS` still localhost | Add the frontend's production URL |
| Uploaded PDFs / chat answers disappear after redeploy | No Volume attached | Attach the Volume (§5 step 6) and redeploy |
| `relation "users" does not exist` | Migrations never ran | Check logs for "Migrations done."; if missing, the container exited before start.sh finished |
