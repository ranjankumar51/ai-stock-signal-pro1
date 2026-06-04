"""Cross-dimension fusion scoring and signal generation (Phase 3).

Layering (kept strictly separate, per docs/architecture.md):
  * analysis layer  -> per-dimension scores  (technical reuses Phase 2 engine)
  * scoring layer   -> FusionScoringEngine    (weighted, confidence-aware fuse)
  * signal layer    -> SignalClassifier        (composite -> SignalType)
The orchestration that wires these together lives in
``app.services.signal_generation`` so this package stays free of DB/session
concerns and remains pure/unit-testable.
"""
