#!/usr/bin/env bash
# Applies database migrations, then starts the API server.
# Migrations are idempotent; running on every boot is safe and keeps the
# schema in lockstep with the deployed image.
set -euo pipefail

echo "[entrypoint] running database migrations..."
alembic upgrade head

echo "[entrypoint] starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
