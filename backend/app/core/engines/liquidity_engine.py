"""
LiquidityEngine — Detects equal highs/lows, stop hunts, and liquidity sweeps.

Equal highs/lows: two swing points within `tolerance_pct` of each other.
Stop hunt / liquidity sweep: price wicks beyond an equal high/low then closes
back inside — indicating a sweep of resting orders.
"""

from typing import Any

import numpy as np

from app.core.engines.base import BaseEngine, EngineResult

TOLERANCE_PCT = 0.001  # 0.1%


class LiquidityEngine(BaseEngine):
    name = "LiquidityEngine"
    default_weight = 1.2

    def analyze(self, bars: list[dict], **kwargs) -> EngineResult:
        df = self._to_df(bars)
        if len(df) < 20:
            return EngineResult(
                engine_name=self.name,
                signal="CLEAR",
                confidence=0.3,
                details={"error": "Not enough bars"},
                weight=self.default_weight,
            )

        highs = df["high"].values.astype(float)
        lows = df["low"].values.astype(float)
        closes = df["close"].values.astype(float)

        # Find swing points (simple 3-bar swing)
        swing_highs = self._swing_highs(highs, n=3)
        swing_lows = self._swing_lows(lows, n=3)

        eq_highs = self._find_equal_levels(swing_highs, highs[-1])
        eq_lows = self._find_equal_levels(swing_lows, lows[-1])

        sweep_high = self._detect_sweep(highs, closes, eq_highs, direction="high")
        sweep_low = self._detect_sweep(lows, closes, eq_lows, direction="low")

        details: dict[str, Any] = {
            "equal_highs": [round(v, 5) for v in eq_highs],
            "equal_lows": [round(v, 5) for v in eq_lows],
            "sweep_of_highs": sweep_high,
            "sweep_of_lows": sweep_low,
        }

        # Sweeping highs = bearish (liquidity grabbed above, likely reversal down)
        # Sweeping lows  = bullish (liquidity grabbed below, likely reversal up)
        if sweep_low and not sweep_high:
            signal = "BULLISH_SWEEP"
            confidence = 0.75
        elif sweep_high and not sweep_low:
            signal = "BEARISH_SWEEP"
            confidence = 0.75
        elif eq_lows and not sweep_low:
            signal = "LIQUIDITY_BELOW"  # potential target
            confidence = 0.5
        elif eq_highs and not sweep_high:
            signal = "LIQUIDITY_ABOVE"
            confidence = 0.5
        else:
            signal = "CLEAR"
            confidence = 0.3

        return EngineResult(
            engine_name=self.name,
            signal=signal,
            confidence=round(confidence, 4),
            details=details,
            weight=self.default_weight,
        )

    def _swing_highs(self, highs: np.ndarray, n: int = 3) -> list[float]:
        result = []
        for i in range(n, len(highs) - n):
            if highs[i] == max(highs[i - n: i + n + 1]):
                result.append(highs[i])
        return result

    def _swing_lows(self, lows: np.ndarray, n: int = 3) -> list[float]:
        result = []
        for i in range(n, len(lows) - n):
            if lows[i] == min(lows[i - n: i + n + 1]):
                result.append(lows[i])
        return result

    def _find_equal_levels(self, levels: list[float], current_price: float) -> list[float]:
        """Find clusters of equal price levels (within tolerance)."""
        if not levels:
            return []
        equal: list[float] = []
        seen: list[float] = []
        for lvl in levels:
            close_to_existing = any(
                abs(lvl - s) / s < TOLERANCE_PCT for s in seen
            )
            if close_to_existing:
                # Mark as equal level
                equal.append(lvl)
            else:
                seen.append(lvl)
        return equal

    def _detect_sweep(
        self,
        price_series: np.ndarray,
        closes: np.ndarray,
        levels: list[float],
        direction: str,
    ) -> bool:
        """Detect if recent price action swept a level and closed back."""
        if not levels or len(price_series) < 3:
            return False
        last_price = price_series[-1]
        last_close = closes[-1]
        second_last_close = closes[-2]

        for lvl in levels:
            if direction == "high":
                # Swept above and closed back below
                if last_price > lvl and last_close < lvl and second_last_close < lvl:
                    return True
            else:
                # Swept below and closed back above
                if last_price < lvl and last_close > lvl and second_last_close > lvl:
                    return True
        return False
