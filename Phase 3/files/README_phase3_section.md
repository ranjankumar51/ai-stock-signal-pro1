<!-- Splice this into README.md: append the section below after the Phase 2
     section, and update the top line + the "What's intentionally absent" list. -->

## Phase 3 — Fusion Scoring & Signal Generation

Combines the per-dimension scores into a single composite, classifies it into a
discrete signal, and persists it. **Technical is the only active input;
fundamental / news / social / volatility are plug-in placeholders (reported but
excluded from the fuse). No risk management, no entry/stop/target.**

**Layers (kept separate):**
```
analysis  -> ScoreProviders (technical reuses the Phase 2 engine; others are placeholders)
scoring   -> FusionScoringEngine   composite = Σ(w·c·s) / Σ(w·c)  over available dims
signal    -> SignalClassifier      composite (+ confidence gate) -> SignalType
pipeline  -> SignalGenerationService  providers -> snapshot -> fuse -> classify -> signal
```

**Weights** live in `config_weights` (versioned, one active row; migration 0005
seeds version 1). The fusion engine falls back to a code default if none exists.

**Modes.** Identical engine code runs LIVE or BACKTEST — pass a `SimulatedClock`
+ `ExecutionMode.BACKTEST` + `backtest_run_id`. All time access is via the
Clock and the point-in-time DataFeed, so no-look-ahead is inherited from Phase 2.
Signals are idempotent per `(instrument, tf, ts, mode, backtest_run_id)`.

**Endpoints (v1):**
```
POST /api/v1/signals/generate           # body: {symbol, tf} -> 201 generated signal
GET  /api/v1/signals/{symbol}/latest?tf=1d
```
Example:
```bash
curl -X POST localhost:8000/api/v1/signals/generate -H 'content-type: application/json' \
     -d '{"symbol":"RELIANCE","tf":"1d"}'
curl 'localhost:8000/api/v1/signals/RELIANCE/latest?tf=1d'
```

**Tests:** `cd backend && pip install -r requirements-dev.txt && pytest`
(adds fusion-engine, classifier, and analysis-to-signal pipeline tests incl.
LIVE/BACKTEST parity and no-look-ahead).

> Top-line note to update: "Phases 0–3".
> "What's intentionally absent" should drop signal generation and now read:
> Risk management (entry/stop/target/sizing), fundamentals, FinBERT/sentiment,
> OpenAI, news/social ingestion, volatility logic, the backtest *runner*, and
> the Electron client.
