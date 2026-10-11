#!/usr/bin/env sh
set -e

echo "Ensuring object storage bucket exists..."
python -m app.core.bootstrap_storage

echo "Running database migrations..."
alembic upgrade head

echo "Starting API..."
exec uvicorn app.main:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8000}"
