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

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health')"

# start.sh runs database migrations (with retries while Postgres starts),
# then starts uvicorn on Railway's $PORT.
CMD ["sh", "start.sh"]
