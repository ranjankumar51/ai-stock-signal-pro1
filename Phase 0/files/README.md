# AI Stock Signal Pro — Backend (Phase 0)

Foundational backend infrastructure. **No UI, no broker integration, no
sentiment/indicator/signal logic** — those arrive in later phases. This phase
delivers a runnable, production-shaped skeleton: config, logging, database
layer + migrations, Redis, and a health-checked FastAPI app.

## Stack
FastAPI · async SQLAlchemy 2.0 (asyncpg) · Alembic · PostgreSQL 16 · Redis 7 ·
structlog · Docker Compose.

## Quick start (Docker)
```bash
cp .env.example .env
docker compose up --build
# API:        http://localhost:8000
# Swagger UI: http://localhost:8000/docs
# Liveness:   http://localhost:8000/api/v1/health
# Readiness:  http://localhost:8000/api/v1/ready   (checks DB + Redis)
```
The backend container runs `alembic upgrade head` on boot, then serves the API.

## Local (without Docker)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# point .env at a local Postgres + Redis, then:
alembic upgrade head
uvicorn app.main:app --reload
```

## Layout
```
ai-stock-signal-pro/
├── docker-compose.yml
├── .env.example
└── backend/
    ├── Dockerfile / entrypoint.sh / requirements.txt
    ├── alembic.ini
    ├── alembic/                 # env.py (async) + versions/0001_initial_schema.py
    └── app/
        ├── main.py              # app factory + lifespan
        ├── core/                # config, logging, redis
        ├── db/                  # base (metadata), session (engine/get_db)
        ├── models/              # 12 SQLAlchemy models (all approved tables)
        ├── schemas/             # pydantic DTOs (health)
        └── api/v1/              # router + health/ready endpoints
```

## Migrations
```bash
cd backend
alembic upgrade head            # apply
alembic downgrade -1            # roll back one
alembic revision --autogenerate -m "msg"   # later phases; metadata is wired
```
The initial migration creates all enum types, 11 tables, constraints (incl. the
DB-level 1:2 risk-reward guard), partial/GIN indexes, and the updated_at
trigger. Constraint names follow the metadata naming convention so autogenerate
stays drift-free.

## Notes
- All timestamps are UTC (`TIMESTAMPTZ`); IST conversion + market-hours logic
  live in the application layer (later phase).
- `price_data` is plain Postgres here; choose TimescaleDB vs. native
  partitioning before first data load (see the earlier DB README).
- Secrets come only from the environment; `.env` is git-ignored.

## What's intentionally absent (later phases)
Broker adapters, ingestion workers, technical indicators, FinBERT/sentiment,
scoring/fusion, signal generation, trade tracking, and the Electron client.
