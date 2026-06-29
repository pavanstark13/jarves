"""
VolatilityEngine — ATR-based volatility assessment and spread analysis.

Computes:
- ATR (14-period True Range average)
- ATR ratio: current candle range vs ATR (1.0 = normal, >2.0 = high volatility)
- Spread vs ATR ratio: if spread > 20% of ATR, conditions are expensive
- VIX proxy: rolling standard deviation of returns normalised to daily equivalent

Signal:
  NORMAL     — ATR ratio 0.5-1.5, spread acceptable
  HIGH_VOL   — ATR ratio > 2.0 (trend-following friendly but risky)
  LOW_VOL    — ATR ratio < 0.5 (ranging, avoid breakout trades)
  WIDE_SPREAD — spread > 2x expected spread
"""

from typing import Any

import numpy as np

from app.core.engines.base import BaseEngine, EngineResult


class VolatilityEngine(BaseEngine):
    name = "VolatilityEngine"
    default_weight = 1.1
    atr_period: int = 14

    def analyze(self, bars: list[dict], **kwargs) -> EngineResult:
        df = self._to_df(bars)
        spread: float = kwargs.get("spread", 0.0)  # current spread in price units

        if len(df) < self.atr_period + 1:
            return EngineResult(
                engine_name=self.name,
                signal="NORMAL",
                confidence=0.5,
                details={"error": "Not enough bars for ATR"},
                weight=self.default_weight,
            )

        highs = df["high"].values.astype(float)
        lows = df["low"].values.astype(float)
        closes = df["close"].values.astype(float)

        atr = self._compute_atr(highs, lows, closes, self.atr_period)
        current_range = highs[-1] - lows[-1]
        atr_ratio = current_range / atr if atr > 0 else 1.0

        spread_atr_ratio = spread / atr if atr > 0 and spread > 0 else 0.0

        # VIX proxy: 14-bar rolling std of log returns, annualised
        log_returns = np.diff(np.log(closes[-30:])) if len(closes) >= 30 else np.diff(np.log(closes))
        vix_proxy = float(np.std(log_returns) * np.sqrt(252 * 24))  # hourly bars

        # Determine signal
        if spread_atr_ratio > 2.0:
            signal = "WIDE_SPREAD"
            confidence = 0.2
        elif atr_ratio > 2.0:
            signal = "HIGH_VOL"
            confidence = 0.6
        elif atr_ratio < 0.5:
            signal = "LOW_VOL"
            confidence = 0.4
        else:
            signal = "NORMAL"
            confidence = 0.85

        details: dict[str, Any] = {
            "atr": round(float(atr), 6),
            "current_range": round(float(current_range), 6),
            "atr_ratio": round(float(atr_ratio), 4),
            "spread": round(float(spread), 6),
            "spread_atr_ratio": round(float(spread_atr_ratio), 4),
            "vix_proxy": round(float(vix_proxy), 4),
        }

        return EngineResult(
            engine_name=self.name,
            signal=signal,
            confidence=round(confidence, 4),
            details=details,
            weight=self.default_weight,
        )

    def _compute_atr(
        self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int
    ) -> float:
        tr_values = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            tr_values.append(tr)
        if not tr_values:
            return 0.0
        # Wilder's smoothed ATR
        atr = float(np.mean(tr_values[:period]))
        for tr in tr_values[period:]:
            atr = (atr * (period - 1) + tr) / period
        return atr
