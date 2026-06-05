"""Risk management engine.

Given a side, an entry price, the ATR, and (optionally) the nearest support /
resistance, it computes a complete risk plan:

    stop_loss   = entry ∓ ATR * atr_stop_multiplier        (∓ by side)
    risk/unit   = |entry - stop_loss|                       (= ATR * multiplier)
    ideal_tgt   = entry ± target_rr * risk/unit
    target      = ideal_tgt, clamped to the nearest S/R level in its path
    risk_reward = reward / risk/unit
    position_sz = floor(account_size * risk_per_trade_pct / risk/unit)

The plan is *accepted* only when ``risk_reward >= min_risk_reward`` and the
position size is at least one unit; otherwise it is *rejected* with a reason and
all derived fields are left None (the caller persists the original signal with
status RISK_REJECTED). Pure and side-effect-free.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.core.config import settings
from app.models.enums import TradeSide

EPS = 1e-12


@dataclass(slots=True)
class RiskParameters:
    """Environment-driven risk configuration (see core.config / .env)."""

    account_size: float
    risk_per_trade_pct: float
    min_risk_reward: float
    atr_stop_multiplier: float
    target_rr: float

    @classmethod
    def from_settings(cls, s=None) -> "RiskParameters":
        s = s or settings
        return cls(
            account_size=float(s.account_size),
            risk_per_trade_pct=float(s.risk_per_trade_pct),
            min_risk_reward=float(s.min_risk_reward),
            atr_stop_multiplier=float(s.atr_stop_multiplier),
            target_rr=float(s.target_rr),
        )


@dataclass(slots=True)
class RiskResult:
    accepted: bool
    reason: str | None
    entry: float | None
    stop_loss: float | None
    target: float | None
    risk_reward: float | None
    position_size: int | None
    risk_confidence: float | None
    detail: dict = field(default_factory=dict)


class RiskManagementEngine:
    def __init__(self, params: RiskParameters | None = None) -> None:
        self.params = params or RiskParameters.from_settings()

    def evaluate(
        self,
        *,
        side: TradeSide | None,
        entry: float | None,
        atr: float | None,
        signal_confidence: float,
        resistance: float | None = None,
        support: float | None = None,
    ) -> RiskResult:
        p = self.params

        if side is None:
            return self._reject("no_side", {})
        if entry is None or atr is None or entry <= 0 or atr <= 0:
            return self._reject("invalid_inputs", {"entry": entry, "atr": atr})

        risk_per_unit = atr * p.atr_stop_multiplier
        if risk_per_unit <= 0:
            return self._reject("invalid_risk_per_unit", {"risk_per_unit": risk_per_unit})

        if side is TradeSide.LONG:
            stop = entry - risk_per_unit
            ideal_target = entry + p.target_rr * risk_per_unit
            cap = resistance if (resistance is not None and resistance > entry) else None
            target = min(ideal_target, cap) if cap is not None else ideal_target
            reward = target - entry
        else:  # SHORT
            stop = entry + risk_per_unit
            ideal_target = entry - p.target_rr * risk_per_unit
            floor_ = support if (support is not None and support < entry) else None
            target = max(ideal_target, floor_) if floor_ is not None else ideal_target
            reward = entry - target

        if stop <= 0:
            return self._reject("invalid_stop", {"stop": round(stop, 4)})

        rr = reward / risk_per_unit
        base = {
            "side": side.value,
            "entry": round(entry, 4),
            "atr": round(atr, 4),
            "atr_stop_multiplier": p.atr_stop_multiplier,
            "stop_loss": round(stop, 4),
            "target": round(target, 4),
            "risk_per_unit": round(risk_per_unit, 4),
            "risk_reward": round(rr, 4),
            "min_risk_reward": p.min_risk_reward,
            "target_rr": p.target_rr,
            "resistance": resistance,
            "support": support,
        }

        if rr + 1e-9 < p.min_risk_reward:
            return self._reject("risk_reward_below_minimum", base)

        capital_at_risk = p.account_size * p.risk_per_trade_pct
        qty = int(math.floor(capital_at_risk / risk_per_unit))
        base["capital_at_risk"] = round(capital_at_risk, 4)
        if qty < 1:
            return self._reject("position_size_below_one", base)

        headroom = max(
            0.0, min(1.0, (rr - p.min_risk_reward) / max(p.min_risk_reward, EPS))
        )
        risk_conf = max(0.0, min(1.0, 0.6 * float(signal_confidence) + 0.4 * headroom))

        return RiskResult(
            accepted=True,
            reason=None,
            entry=entry,
            stop_loss=stop,
            target=target,
            risk_reward=rr,
            position_size=qty,
            risk_confidence=risk_conf,
            detail={
                **base,
                "position_size": qty,
                "risk_confidence": round(risk_conf, 4),
                "accepted": True,
            },
        )

    @staticmethod
    def _reject(reason: str, detail: dict) -> RiskResult:
        return RiskResult(
            accepted=False,
            reason=reason,
            entry=None,
            stop_loss=None,
            target=None,
            risk_reward=None,
            position_size=None,
            risk_confidence=None,
            detail={**detail, "accepted": False, "reason": reason},
        )
