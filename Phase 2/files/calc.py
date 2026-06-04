"""Pure, vectorized numerical primitives shared by indicators.

Kept dependency-free (numpy only) and side-effect-free so each is unit-testable
in isolation. All functions return arrays the same length as the input, with
``nan`` where a value is not yet defined (warm-up period). Recursive smoothers
are O(n); indicator computation fetches only a bounded lookback window, so these
stay cheap even over large histories.
"""
from __future__ import annotations

import numpy as np

EPS = 1e-12


def sma(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=np.float64)
    if len(x) < n:
        return out
    cs = np.cumsum(np.insert(x, 0, 0.0))
    out[n - 1 :] = (cs[n:] - cs[:-n]) / n
    return out


def ema(x: np.ndarray, n: int) -> np.ndarray:
    """Exponential MA, adjust=False (seeded with the first value)."""
    out = np.empty_like(x, dtype=np.float64)
    if len(x) == 0:
        return out
    alpha = 2.0 / (n + 1.0)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = alpha * x[i] + (1.0 - alpha) * out[i - 1]
    return out


def rma(x: np.ndarray, n: int) -> np.ndarray:
    """Wilder's smoothing (alpha = 1/n), seeded with the SMA of the first n."""
    out = np.full_like(x, np.nan, dtype=np.float64)
    if len(x) < n:
        return out
    out[n - 1] = np.mean(x[:n])
    for i in range(n, len(x)):
        out[i] = (out[i - 1] * (n - 1) + x[i]) / n
    return out


def rolling_std(x: np.ndarray, n: int, ddof: int = 0) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=np.float64)
    if len(x) < n:
        return out
    cs = np.cumsum(np.insert(x, 0, 0.0))
    cs2 = np.cumsum(np.insert(x * x, 0, 0.0))
    s = cs[n:] - cs[:-n]
    s2 = cs2[n:] - cs2[:-n]
    var = (s2 - (s * s) / n) / (n - ddof)
    out[n - 1 :] = np.sqrt(np.clip(var, 0.0, None))
    return out


def true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    tr = np.empty_like(high, dtype=np.float64)
    tr[0] = high[0] - low[0]
    prev_close = close[:-1]
    tr[1:] = np.maximum.reduce(
        [high[1:] - low[1:], np.abs(high[1:] - prev_close), np.abs(low[1:] - prev_close)]
    )
    return tr


def rolling_max(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=np.float64)
    for i in range(n - 1, len(x)):
        out[i] = np.max(x[i - n + 1 : i + 1])
    return out


def rolling_min(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=np.float64)
    for i in range(n - 1, len(x)):
        out[i] = np.min(x[i - n + 1 : i + 1])
    return out
