<!-- Splice into README.md: append the section below after the Phase 3 section,
     change the top line to "Phases 0–4", and update "What's intentionally
     absent" (drop risk management). -->

## Phase 4 — Risk Management Engine

Turns an actionable signal into a validated trade plan. **Deterministic,
point-in-time, mode-agnostic. No trade execution/tracking yet.**

**Layer:** `app/risk/engine.py` — a pure `RiskManagementEngine` (+ `RiskParameters`,
`RiskResult`). The Phase 3 `SignalGenerationService` calls it after
classification; it consumes existing technical outputs (ATR, S&R, last close) —
ATR is **never recomputed**.

**Plan:**
```
stop_loss   = entry ∓ ATR × atr_stop_multiplier      (default mult 1.5)
risk/unit   = ATR × atr_stop_multiplier
target      = entry ± target_rr × risk/unit, clamped to nearest S/R
risk_reward = reward / risk/unit                     (accept iff ≥ min_risk_reward)
position    = floor(account_size × risk_per_trade_pct / risk/unit)
```

**Rejection policy.** If RR < `min_risk_reward` (or sizing < 1 unit, or inputs
invalid): the classification is kept, `status = RISK_REJECTED`, the reason is in
`rationale.risk`, and entry/stop_loss/target/risk_reward/position_size/
risk_confidence are NULL. HOLD signals skip risk entirely.

**Config (.env):**
```
ACCOUNT_SIZE=1000000
RISK_PER_TRADE_PCT=0.01
MIN_RISK_REWARD=2.0
ATR_STOP_MULTIPLIER=1.5
TARGET_RR=2.0
```

**Modes.** Same engine LIVE or BACKTEST; entry is the point-in-time last close,
so no-look-ahead is inherited from Phase 2.

**API:** unchanged endpoints, now returning the risk plan:
```
POST /api/v1/signals/generate            # -> signal + entry/stop/target/RR/size/risk_confidence
GET  /api/v1/signals/{symbol}/latest?tf=1d
```

**Tests:** `cd backend && pip install -r requirements-dev.txt && pytest`
(adds risk-engine unit tests + risk-pipeline integration tests incl.
LIVE/BACKTEST parity and no-look-ahead).

**Migration:** `0006` adds `RISK_REJECTED` to `signal_status` and the
`position_size` / `risk_confidence` columns to `signals`.

> Top-line note to update: "Phases 0–4".
> "What's intentionally absent" should drop risk management and now read:
> Trade execution/tracking, fundamentals, FinBERT/sentiment, OpenAI, news/social
> ingestion, volatility logic, the backtest *runner*, and the Electron client.
