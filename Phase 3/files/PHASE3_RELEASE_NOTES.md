# Phase 3 — Fusion Scoring Engine & Signal Generation

## Summary
Adds the cross-dimension **fusion scoring engine**, a deterministic **signal
classification engine**, fusion-level **confidence scoring**, **signal
persistence**, and the end-to-end **analysis-to-signal pipeline**. Technical is
the only active scoring input; fundamental / news / social / volatility ship as
inert plug-in placeholders. Works in LIVE and BACKTEST modes and preserves the
existing point-in-time / no-look-ahead guarantees by reusing the Phase 2 Clock,
DataFeed, and technical engine unchanged.

## What it does
- **Fusion:** `composite = Σ(wᵢ·cᵢ·sᵢ) / Σ(wᵢ·cᵢ)` over *available* dimensions
  (confidence-aware). Unavailable dimensions are excluded exactly like an
  insufficient indicator. Weights are versioned in `config_weights`; a default
  active set (version 1) is seeded by migration `0005`.
- **Classification:** composite → STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL
  with a confidence gate (low confidence ⇒ HOLD). Deterministic & reproducible.
- **Persistence:** writes `analysis_snapshots` (technical) and one idempotent
  `signals` row per `(instrument, tf, ts, mode, backtest_run_id)`.
- **API:** `POST /api/v1/signals/generate`, `GET /api/v1/signals/{symbol}/latest`.

## Not in scope (later phases)
Risk management, entry/stop/target, position sizing; news/social ingestion and
sentiment models; fundamental and volatility analysis logic; the backtest
*runner*.

## Schema changes (migration 0005)
- `signals.tf` (timeframe enum, NOT NULL) + read index `ix_signals_instr_tf_ts`.
- Partial-unique idempotency indexes `uq_signals_live_pit`, `uq_signals_bt_pit`.
- Seed `config_weights` version 1 (active).

## Validation
- 7 fusion-engine + 7 classifier unit tests **pass** (executed).
- 5 pipeline integration tests provided (LIVE/BACKTEST parity, no-look-ahead,
  snapshot↔signal linkage, placeholder exclusion, idempotent persistence).
- Migration `0005` is additive and reversible; the existing
  `ck_signals_min_risk_reward` guard is satisfied because `risk_reward` stays
  NULL in Phase 3.

## Upgrade
```bash
cd backend && alembic upgrade head   # applies 0005
```
