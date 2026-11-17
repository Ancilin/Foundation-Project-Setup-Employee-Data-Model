#!/bin/bash
# start.sh — Run migrations, seed data (if empty), then start the API server.
set -e

echo "=== Running Alembic migrations ==="
python -m alembic upgrade head

echo "=== Seeding database (if empty) ==="
python -m scripts.seed --limit 100 2>&1 || echo "Seed skipped (data may already exist)"

echo "=== Starting LedgerForge API ==="
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
