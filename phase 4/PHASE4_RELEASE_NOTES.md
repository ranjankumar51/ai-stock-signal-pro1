# Phase 4 — Risk Management Engine

## Summary
Adds a deterministic, point-in-time **risk management engine** that turns an
actionable signal into a complete, validated trade plan: entry, ATR-based
stop-loss, risk-reward-based target (clamped to the nearest support/resistance),
risk-reward validation against a configurable minimum, and position sizing.
Runs identically in LIVE and BACKTEST modes and inherits the Phase 2
no-look-ahead guarantee unchanged (it reads only the Clock + point-in-time
DataFeed via the technical engine and consumes existing technical outputs).

## What it does
- **Stop-loss:** `entry ∓ ATR × atr_stop_multiplier` (default multiplier 1.5,
  configurable). ATR is reused from the Phase 2 technical analysis — **not
  recomputed**.
- **Target:** placed at `target_rr × risk`, then clamped to the nearest
  resistance (long) / support (short) from the Phase 2 S&R indicator.
- **Risk-reward validation:** accepts only when achievable RR ≥ `min_risk_reward`
  (default 2.0 → the 1:2 floor, also enforced at the DB level).
- **Position sizing:** `floor(account_size × risk_per_trade_pct / risk_per_unit)`.
- **risk_confidence:** blends fusion confidence with RR headroom.
- **Rejection policy:** on validation failure the **original classification is
  preserved**, status becomes **`RISK_REJECTED`**, the reason is stored in
  `rationale.risk`, and entry / stop_loss / target / risk_reward / position_size
  / risk_confidence are left **NULL**.
- **HOLD** signals skip risk evaluation entirely (no risk fields, status ACTIVE).

## Configuration (environment-driven)
```
ACCOUNT_SIZE=1000000
RISK_PER_TRADE_PCT=0.01
MIN_RISK_REWARD=2.0
ATR_STOP_MULTIPLIER=1.5
TARGET_RR=2.0
```

## Schema changes (migration 0006)
- `signal_status` enum gains the **`RISK_REJECTED`** label.
- `signals` gains dedicated columns **`position_size`** NUMERIC(18,4) and
  **`risk_confidence`** NUMERIC(5,4) (entry/stop_loss/target/risk_reward already
  existed from Phase 0).
- Check constraints: `ck_signals_risk_confidence_range`,
  `ck_signals_position_size_positive`. The existing
  `ck_signals_min_risk_reward` (≥ 2) continues to hold (rejected signals keep
  `risk_reward` NULL; accepted signals are gated at ≥ `min_risk_reward`).
- Additive and reversible. Downgrade drops the columns/constraints; the enum
  label remains (PostgreSQL cannot remove enum values).

## Reuse (no duplication)
Reuses the Phase 2 Clock, DataFeed, OHLCV series, **ATR** and **Support &
Resistance** outputs, the repository/service/strategy patterns, and the Phase 3
fusion → classification pipeline. The technical engine now carries the last
`close` through its details so the entry price needs no extra DB read.

## Validation
- 10 risk-engine unit tests **pass** (executed): long/short accept, resistance/
  support caps causing rejection, invalid ATR, zero position size, partial-cap
  acceptance with reduced RR + headroom-based confidence.
- 6 pipeline integration tests provided: valid plan persisted ACTIVE, risk
  rejection preserves classification + NULLs the plan, HOLD skips risk,
  short-side plan, LIVE/BACKTEST parity, and real-engine no-look-ahead (risk
  entry == bounded last close, snapshot n_candles == 101).

## Not in scope (later phases)
Trade execution/tracking, sentiment, fundamental and volatility analysis logic,
the backtest *runner*, and the Electron client.

## Upgrade
```bash
cd backend && alembic upgrade head   # applies 0006
```
