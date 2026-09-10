"""
Indicator maths — pure functions over plain float sequences.

No pandas, no state, no I/O. Every function here is deterministic: the same
candles always produce the same number, which is what makes the strategy
reproducible between the live agent and the backtest.
"""

from __future__ import annotations

import numpy as np


def _arr(values) -> np.ndarray:
    return np.asarray(values, dtype=float)


def ema(values, period: int) -> np.ndarray:
    """Exponential moving average, seeded with the first value."""
    data = _arr(values)
    if data.size == 0:
        return data
    alpha = 2.0 / (period + 1.0)
    out = np.empty_like(data)
    out[0] = data[0]
    for i in range(1, data.size):
        out[i] = alpha * data[i] + (1.0 - alpha) * out[i - 1]
    return out


def sma(values, period: int) -> np.ndarray:
    data = _arr(values)
    if data.size < period or period <= 0:
        return np.full(data.size, np.nan)
    cumulative = np.cumsum(np.insert(data, 0, 0.0))
    out = np.full(data.size, np.nan)
    out[period - 1:] = (cumulative[period:] - cumulative[:-period]) / period
    return out


def true_range(highs, lows, closes) -> np.ndarray:
    """True range per bar. The first bar uses high-low (no prior close)."""
    h, l, c = _arr(highs), _arr(lows), _arr(closes)
    if h.size == 0:
        return h
    tr = np.empty(h.size)
    tr[0] = h[0] - l[0]
    if h.size > 1:
        tr[1:] = np.maximum(
            h[1:] - l[1:],
            np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])),
        )
    return tr


def atr(highs, lows, closes, period: int = 14) -> float:
    """Wilder's smoothed Average True Range. Returns 0.0 when data is short."""
    tr = true_range(highs, lows, closes)
    if tr.size <= period:
        return float(np.mean(tr)) if tr.size else 0.0
    value = float(np.mean(tr[1:period + 1]))
    for x in tr[period + 1:]:
        value = (value * (period - 1) + float(x)) / period
    return value


def rsi(closes, period: int = 14) -> float:
    """Wilder's RSI of the final bar. Returns 50.0 when data is short."""
    c = _arr(closes)
    if c.size <= period:
        return 50.0
    deltas = np.diff(c)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))
    for g, l in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + float(g)) / period
        avg_loss = (avg_loss * (period - 1) + float(l)) / period
    if avg_loss == 0.0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def rsi_series(closes, period: int = 14) -> np.ndarray:
    """RSI at every bar (NaN until enough history). Used for pullback lookbacks."""
    c = _arr(closes)
    out = np.full(c.size, np.nan)
    for i in range(period + 1, c.size + 1):
        out[i - 1] = rsi(c[:i], period)
    return out


def swing_highs(highs, left: int = 2, right: int = 2) -> list[int]:
    """Indices of bars whose high is the strict maximum of their neighbourhood."""
    h = _arr(highs)
    out: list[int] = []
    for i in range(left, h.size - right):
        window = h[i - left: i + right + 1]
        if h[i] == window.max() and (window == h[i]).sum() == 1:
            out.append(i)
    return out


def swing_lows(lows, left: int = 2, right: int = 2) -> list[int]:
    l = _arr(lows)
    out: list[int] = []
    for i in range(left, l.size - right):
        window = l[i - left: i + right + 1]
        if l[i] == window.min() and (window == l[i]).sum() == 1:
            out.append(i)
    return out


def last_swing_low(lows, left: int = 2, right: int = 2, lookback: int = 40) -> float | None:
    """Most recent confirmed swing low within `lookback` bars, or None."""
    l = _arr(lows)[-lookback:] if lookback else _arr(lows)
    idx = swing_lows(l, left, right)
    return float(l[idx[-1]]) if idx else None


def last_swing_high(highs, left: int = 2, right: int = 2, lookback: int = 40) -> float | None:
    h = _arr(highs)[-lookback:] if lookback else _arr(highs)
    idx = swing_highs(h, left, right)
    return float(h[idx[-1]]) if idx else None


def slope(values, lookback: int = 5) -> float:
    """Change in a series over `lookback` bars — the sign is what matters."""
    data = _arr(values)
    if data.size <= lookback:
        return 0.0
    return float(data[-1] - data[-1 - lookback])


def swing_structure(highs, lows, direction: str, lookback: int = 40) -> tuple[bool, str]:
    """
    Is the chart still building the structure of a trend?

    Uptrend structure is higher highs and higher lows; downtrend is the mirror.
    Both are statements about swings that have already formed and been
    confirmed — nothing here is an extrapolation.
    """
    h = _arr(highs)[-lookback:]
    l = _arr(lows)[-lookback:]
    high_idx = swing_highs(h)
    low_idx = swing_lows(l)
    if len(high_idx) < 2 or len(low_idx) < 2:
        return False, f"only {len(high_idx)} swing highs and {len(low_idx)} swing lows in {lookback} bars"

    prev_high, last_high = float(h[high_idx[-2]]), float(h[high_idx[-1]])
    prev_low, last_low = float(l[low_idx[-2]]), float(l[low_idx[-1]])

    if direction == "LONG":
        ok = last_high > prev_high and last_low > prev_low
        shape = "higher high + higher low" if ok else (
            f"high {last_high:.2f} vs {prev_high:.2f}, low {last_low:.2f} vs {prev_low:.2f}"
        )
    else:
        ok = last_high < prev_high and last_low < prev_low
        shape = "lower high + lower low" if ok else (
            f"high {last_high:.2f} vs {prev_high:.2f}, low {last_low:.2f} vs {prev_low:.2f}"
        )
    return ok, shape


def broke_structure(highs, lows, closes, direction: str, lookback: int = 20) -> bool:
    """
    Break of structure: after a swing was confirmed, did a later bar close
    beyond it? The ordering matters — a close that happened *before* the swing
    formed is not a break of it.
    """
    h, l, c = _arr(highs), _arr(lows), _arr(closes)
    if c.size < lookback + 5:
        return False
    offset = max(0, c.size - lookback)
    window_h, window_l, window_c = h[offset:], l[offset:], c[offset:]
    right = 2
    if direction == "LONG":
        for i in reversed(swing_highs(window_h)):
            confirmed_at = i + right
            if np.any(window_c[confirmed_at + 1:] > window_h[i]):
                return True
        return False
    if direction == "SHORT":
        for i in reversed(swing_lows(window_l)):
            confirmed_at = i + right
            if np.any(window_c[confirmed_at + 1:] < window_l[i]):
                return True
        return False
    return False


def touched_level(highs, lows, level_series, direction: str, bars: int = 10) -> bool:
    """
    Did price trade back to its moving-average value in the recent window?
    For a long that means a bar's low reached the average; for a short, a
    bar's high did.
    """
    h, l, m = _arr(highs), _arr(lows), _arr(level_series)
    n = min(bars, h.size, m.size)
    if n == 0:
        return False
    if direction == "LONG":
        return bool(np.any(l[-n:] <= m[-n:]))
    return bool(np.any(h[-n:] >= m[-n:]))


def fair_value_gaps(highs, lows, direction: str, lookback: int = 30) -> list[tuple[float, float]]:
    """
    Three-bar imbalances left behind by an impulsive move, newest last.
    Bullish: bar[i+1].low > bar[i-1].high. Bearish: bar[i+1].high < bar[i-1].low.
    """
    h, l = _arr(highs), _arr(lows)
    if h.size < 3:
        return []
    start = max(1, h.size - lookback)
    gaps: list[tuple[float, float]] = []
    for i in range(start, h.size - 1):
        if direction == "LONG" and l[i + 1] > h[i - 1]:
            gaps.append((float(h[i - 1]), float(l[i + 1])))
        elif direction == "SHORT" and h[i + 1] < l[i - 1]:
            gaps.append((float(h[i + 1]), float(l[i - 1])))
    return gaps
