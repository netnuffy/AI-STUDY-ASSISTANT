# Railway deployment: this Dockerfile is the build for the backend service.
# Set the Railway service's Root Directory to `backend` (the repo also holds
# the frontend), or build from this directory locally:
#   docker build -t study-assistant-api .
#   docker run -p 8000:8000 --env-file .env study-assistant-api
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first (cached unless requirements.txt changes).
# All packages ship prebuilt wheels for linux x86_64, so no build tools
# are needed.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Data directories. In production these live on a Railway Volume mounted at
# /app/data — set UPLOAD_DIR=/app/data/uploads and
# CHROMA_PERSIST_DIR=/app/data/chroma_data (see .env.example). Without a
# volume, uploads and the vector index are lost on redeploy.
RUN mkdir -p uploads chroma_data

# NOTE: the container intentionally runs as root. Railway mounts volumes
# root-owned, and the app creates its upload/chroma directories inside the
# volume at startup (see app/application.py lifespan). An earlier version
# ran as a non-root appuser and crashed on Railway with
# "PermissionError: [Errno 13] Permission denied: '/app/data/uploads'"
# (2026-11-23). Do not re-add a USER directive without also handling
# volume ownership.

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health')"

# start.sh runs database migrations (with retries while Postgres starts),
# then starts uvicorn on Railway's $PORT.
CMD ["sh", "start.sh"]
