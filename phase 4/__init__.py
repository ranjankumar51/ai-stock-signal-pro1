"""Risk management engine (Phase 4).

Pure, deterministic risk planning kept free of DB/session/clock concerns so it
is unit-testable in isolation and runs identically in LIVE and BACKTEST modes
(the orchestration layer supplies point-in-time inputs via the Phase 2 Clock +
DataFeed). It consumes existing technical-analysis outputs (ATR, support /
resistance, last close) — it never recomputes indicators.
"""
