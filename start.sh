#!/bin/bash
# start.sh — Run migrations, seed full dataset once if DB is empty, then start the API server.
set -e

echo "=== Running Alembic migrations ==="
python -m alembic upgrade head

echo "=== Checking database seed status ==="
USER_COUNT=$(python -c "from sqlalchemy import select, func; from sqlalchemy.orm import Session; from app.db.session import get_engine; from app.models.user import User; print(Session(get_engine()).scalar(select(func.count(User.user_id))) or 0)")
echo "Existing users in DB: $USER_COUNT"

if [ "$USER_COUNT" -eq "0" ]; then
  echo "=== Seeding full LedgerForge dataset (CSV mode, --no-export) ==="
  python -m scripts.seed --no-export
else
  echo "=== Database already seeded ($USER_COUNT users) — skipping seed ==="
fi

echo "=== Starting LedgerForge API ==="
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
