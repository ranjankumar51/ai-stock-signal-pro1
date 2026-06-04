# AI Stock Signal Pro — Backend (Phases 0–2)

Foundational infrastructure (Phase 0), market-data ingestion (Phase 1), a
minimal backtest foundation, and the technical-analysis engine (Phase 2).
**No UI, no buy/sell signals, no risk management, no sentiment/OpenAI** — later
phases.

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

## Phase 1 — Market data ingestion

Adapter-pattern ingestion with Zerodha Kite Connect as the first provider.

**Architecture.** The **worker** is the *only* process that calls the broker
API, so its in-process rate limiters (historical 3/s, quote 1/s) are
authoritative. The **API** never touches the broker — it enqueues jobs onto a
Redis list and serves reads from cache/DB. Flow:

```
API  ──enqueue──►  Redis list (ingest:jobs)  ──consume──►  Worker
                                                              ├─ scheduler (APScheduler, IST)
                                                              ├─ ZerodhaProvider (rate-limit + retry + chunk)
                                                              └─ services → repositories → Postgres + Redis cache
```

**New layers:** `app/ingestion/` (DTOs, interval map, provider interfaces +
Zerodha adapter, constituent config), `app/repositories/`, `app/services/`,
`app/jobs/` (queue, scheduler, market-hours), and `app/worker.py`.

**Provider interfaces** (`app/ingestion/providers/base.py`): `MarketDataProvider`,
`FundamentalsProvider`, `NewsProvider`. Only `MarketDataProvider` is implemented
(Zerodha); the others are contracts for later vendors. Swap brokers by adding an
adapter + a branch in `providers/factory.py`.

**Endpoints (v1):**
```
POST /api/v1/ingest/instruments/sync     # enqueue master + constituent sync → 202 {job_id}
POST /api/v1/ingest/historical/sync      # body: {selector|symbols, timeframes, lookback_days} → 202
GET  /api/v1/market-data/{symbol}/latest?tf=1d   # latest candle (cache→DB)
GET  /api/v1/market-data/{symbol}/quote          # latest cached LTP (market hours)
```
Example:
```bash
curl -X POST localhost:8000/api/v1/ingest/instruments/sync -H 'content-type: application/json' -d '{}'
curl -X POST localhost:8000/api/v1/ingest/historical/sync  -H 'content-type: application/json' \
     -d '{"selector":"NIFTY50","timeframes":["1d","1h"],"lookback_days":90}'
curl 'localhost:8000/api/v1/market-data/RELIANCE/latest?tf=1d'
```

**Timeframes** (per Kite limits, auto-chunked): 1m→minute/60d, 5m→5minute/100d,
15m→15minute/200d, 1h→60minute/400d, 1d→day/2000d. Incremental syncs resume
from `data_sync_state` so only new candles are fetched.

**Scheduled jobs (IST):** instrument refresh 08:30; intraday 1m/5m/15m every 5 min
(market hours); hourly :01; EOD daily 16:00 weekdays; quote hot-cache every 5 s
(market hours).

### Two operational caveats (important)
1. **Zerodha access token is daily.** Kite requires an interactive login each
   morning to mint an access token. Set `ZERODHA_API_KEY` + `ZERODHA_ACCESS_TOKEN`
   in `.env`. **Without them the provider is unconfigured and all sync jobs
   safely no-op** (the app still runs). A token-refresh flow is a later add-on.
2. **Index constituents are configured, not fetched.** Kite doesn't expose
   index membership, so `app/ingestion/constituents.py` holds the Nifty 50 /
   Bank Nifty symbol lists. They are a **snapshot — verify against NSE's official
   index CSVs** and update periodically; the sync resolves them against the live
   instrument master and logs any symbols it can't find.

### Run the worker
`docker compose up --build` now starts `db`, `redis`, `backend`, and `worker`.
Locally: `python -m app.worker` (separate process from the API).

## Backtest foundation (minimal)

Not the backtest engine — just the bones so live and backtest output never mix
and future engines run in either mode unchanged:
- **`execution_mode` enum (LIVE/BACKTEST)** + a `mode` column and nullable
  `backtest_run_id` on `signals`, `trades`, and `analysis_snapshots`.
- **`backtest_runs`** table (params, period, weights version, metrics, status).
- **`Clock`** (`app/runtime/clock.py`): `LiveClock` (wall clock) and
  `SimulatedClock` (runner-advanced). Engines read "now" only from a Clock.
- **`DataFeed`** (`app/runtime/datafeed.py`): `DbDataFeed` returns candles with
  `ts <= clock.now()`. Same feed for both modes — the only difference is the
  clock. This is the structural no-look-ahead guarantee.

Migrations `0003` (backtest foundation) and `0004` (snapshot `tf` column).

## Phase 2 — Technical analysis engine

Strategy-pattern indicators feeding a scoring engine. **Outputs indicator
values, a technical trend, a technical score, and confidence only — no signals,
no risk.**

**Indicators** (`app/analysis/technical/indicators/`, each independently
testable): RSI, MACD, EMA20/50/200, VWAP (session-anchored), ATR
(non-directional), ADX (+DI/−DI), Bollinger Bands, SuperTrend, Volume analysis,
Support & Resistance. Swap/reweight in `indicators/__init__.py`.

**Engine** (`engine.py`): pulls a bounded candle window through the DataFeed
(as-of `clock.now()`), runs every indicator over one shared numpy series, and
hands the per-indicator reads to the scoring engine. Mode-agnostic by
construction.

**Scoring** (`scoring.py`): weighted fusion of directional indicators →
normalized composite in [-1, 1], a **0–100 technical score**, a trend label
(STRONG_BEARISH … STRONG_BULLISH), and a confidence that blends data
sufficiency, indicator agreement, and average per-indicator confidence.

**Storage:** `TechnicalAnalysisService.analyze_and_store()` writes
`analysis_snapshots`: the normalized score in `tech_score` (NUMERIC(5,4), the
fusion convention) and the full breakdown — **0–100 score, trend, confidence,
and every indicator's values** — in `details` (JSONB). Live or backtest via the
`mode`/`backtest_run_id` args.

**Performance for large histories:** the engine fetches only
`max(indicator.lookback)` candles (not full history) using the
`(instrument_id, tf, ts DESC)` index, builds the numpy series once, and shares
it across indicators; every indicator is O(window). Vectorized primitives live
in `calc.py`.

**Tests:** `cd backend && pip install -r requirements-dev.txt && pytest`
(28 tests: math primitives, every indicator, scoring engine, and engine-level
live/backtest parity + no-look-ahead).

## What's intentionally absent (later phases)
Buy/sell signal generation, risk management, fundamentals, FinBERT/sentiment,
OpenAI, scoring *fusion across dimensions*, the backtest *runner*, and the
Electron client.
