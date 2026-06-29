"""
FeatureEngineering — Computes technical indicators from OHLCV data.

All functions accept a list of OHLCV dicts and return computed values
or augmented dicts.
"""

from typing import Any

import numpy as np
import pandas as pd


def compute_ema(closes: list[float], period: int) -> list[float]:
    s = pd.Series(closes)
    return s.ewm(span=period, adjust=False).mean().tolist()


def compute_sma(closes: list[float], period: int) -> list[float]:
    s = pd.Series(closes)
    return s.rolling(period).mean().tolist()


def compute_rsi(closes: list[float], period: int = 14) -> list[float]:
    s = pd.Series(closes)
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50).tolist()


def compute_atr(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> list[float]:
    tr_list = [highs[0] - lows[0]]  # first bar no prev close
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        tr_list.append(tr)
    atr = pd.Series(tr_list).ewm(com=period - 1, adjust=False).mean()
    return atr.tolist()


def compute_macd(
    closes: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, list[float]]:
    s = pd.Series(closes)
    ema_fast = s.ewm(span=fast, adjust=False).mean()
    ema_slow = s.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        "macd": macd_line.tolist(),
        "signal": signal_line.tolist(),
        "histogram": histogram.tolist(),
    }


def compute_bollinger_bands(
    closes: list[float], period: int = 20, std_dev: float = 2.0
) -> dict[str, list[float]]:
    s = pd.Series(closes)
    middle = s.rolling(period).mean()
    std = s.rolling(period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return {
        "upper": upper.tolist(),
        "middle": middle.tolist(),
        "lower": lower.tolist(),
    }


def compute_stochastic(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    k_period: int = 14,
    d_period: int = 3,
) -> dict[str, list[float]]:
    df = pd.DataFrame({"high": highs, "low": lows, "close": closes})
    lowest_low = df["low"].rolling(k_period).min()
    highest_high = df["high"].rolling(k_period).max()
    k = 100 * (df["close"] - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    d = k.rolling(d_period).mean()
    return {"k": k.fillna(50).tolist(), "d": d.fillna(50).tolist()}


def enrich_bars(bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add EMA20, EMA50, RSI14, ATR14 columns to each bar dict."""
    if not bars:
        return bars

    closes = [b["close"] for b in bars]
    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]

    ema20 = compute_ema(closes, 20)
    ema50 = compute_ema(closes, 50)
    rsi = compute_rsi(closes, 14)
    atr = compute_atr(highs, lows, closes, 14)

    enriched = []
    for i, bar in enumerate(bars):
        enriched.append({
            **bar,
            "ema20": round(ema20[i], 6) if ema20[i] == ema20[i] else None,
            "ema50": round(ema50[i], 6) if ema50[i] == ema50[i] else None,
            "rsi14": round(rsi[i], 4),
            "atr14": round(atr[i], 6),
        })
    return enriched
