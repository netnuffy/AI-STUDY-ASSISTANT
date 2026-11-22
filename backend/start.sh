#!/bin/sh
# Production entrypoint (Railway): run migrations, then start the server.
# Migrations retry while the database starts up; a genuinely broken
# migration still fails the deploy (the final attempt runs under `set -e`).
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
