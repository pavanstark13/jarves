"""
TrendEngine — EMA20/50/200 crossover + price position.

Signal:
  BULLISH  — price > EMA20 > EMA50 > EMA200, all EMAs sloping up
  BEARISH  — price < EMA20 < EMA50 < EMA200, all EMAs sloping down
  NEUTRAL  — mixed conditions

Confidence is derived from how many of the 4 conditions above are met (0-4 → 0-1).
"""

import numpy as np
import pandas as pd

from app.core.engines.base import BaseEngine, EngineResult


class TrendEngine(BaseEngine):
    name = "TrendEngine"
    default_weight = 1.5

    def analyze(self, bars: list[dict], **kwargs) -> EngineResult:
        df = self._to_df(bars)

        if len(df) < 200:
            return EngineResult(
                engine_name=self.name,
                signal="NEUTRAL",
                confidence=0.0,
                details={"error": f"Not enough bars: {len(df)} (need 200)"},
                weight=self.default_weight,
            )

        close = df["close"].values.astype(float)

        ema20 = self._ema(close, 20)
        ema50 = self._ema(close, 50)
        ema200 = self._ema(close, 200)

        current_close = close[-1]
        current_ema20 = ema20[-1]
        current_ema50 = ema50[-1]
        current_ema200 = ema200[-1]

        # Slope: compare last value vs 5 bars ago
        slope_ema20 = ema20[-1] - ema20[-6] if len(ema20) >= 6 else 0
        slope_ema50 = ema50[-1] - ema50[-6] if len(ema50) >= 6 else 0
        slope_ema200 = ema200[-1] - ema200[-6] if len(ema200) >= 6 else 0

        bullish_conditions = [
            current_close > current_ema20,
            current_ema20 > current_ema50,
            current_ema50 > current_ema200,
            slope_ema20 > 0 and slope_ema50 > 0,
        ]
        bearish_conditions = [
            current_close < current_ema20,
            current_ema20 < current_ema50,
            current_ema50 < current_ema200,
            slope_ema20 < 0 and slope_ema50 < 0,
        ]

        bull_score = sum(bullish_conditions)
        bear_score = sum(bearish_conditions)

        if bull_score > bear_score:
            signal = "BULLISH"
            confidence = bull_score / 4.0
        elif bear_score > bull_score:
            signal = "BEARISH"
            confidence = bear_score / 4.0
        else:
            signal = "NEUTRAL"
            confidence = 0.3

        details = {
            "close": round(current_close, 5),
            "ema20": round(current_ema20, 5),
            "ema50": round(current_ema50, 5),
            "ema200": round(current_ema200, 5),
            "slope_ema20": round(slope_ema20, 6),
            "slope_ema50": round(slope_ema50, 6),
            "slope_ema200": round(slope_ema200, 6),
            "bullish_conditions_met": bull_score,
            "bearish_conditions_met": bear_score,
        }

        return EngineResult(
            engine_name=self.name,
            signal=signal,
            confidence=round(confidence, 4),
            details=details,
            weight=self.default_weight,
        )

    @staticmethod
    def _ema(data: np.ndarray, period: int) -> np.ndarray:
        """Compute EMA using pandas for accuracy."""
        s = pd.Series(data)
        return s.ewm(span=period, adjust=False).mean().values
