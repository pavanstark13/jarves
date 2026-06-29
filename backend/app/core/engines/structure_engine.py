"""
MarketStructureEngine — Detects swing highs/lows, HH/HL/LH/LL, BOS, CHoCH.

Swing detection uses a simple N-bar lookback: a swing high is a candle whose
high is the highest of the surrounding `swing_period` bars on each side.

Break of Structure (BOS): price closes beyond the last significant swing in
trend direction.
Change of Character (CHoCH): the structure sequence flips from bullish to
bearish or vice versa.
"""

from typing import Any

import numpy as np
import pandas as pd

from app.core.engines.base import BaseEngine, EngineResult


class MarketStructureEngine(BaseEngine):
    name = "MarketStructureEngine"
    default_weight = 1.4
    swing_period: int = 5  # bars each side for swing detection

    def analyze(self, bars: list[dict], **kwargs) -> EngineResult:
        df = self._to_df(bars)
        min_bars = self.swing_period * 2 + 5
        if len(df) < min_bars:
            return EngineResult(
                engine_name=self.name,
                signal="NEUTRAL",
                confidence=0.0,
                details={"error": f"Not enough bars: {len(df)}"},
                weight=self.default_weight,
            )

        highs = df["high"].values.astype(float)
        lows = df["low"].values.astype(float)
        closes = df["close"].values.astype(float)

        swing_highs = self._find_swing_highs(highs, self.swing_period)
        swing_lows = self._find_swing_lows(lows, self.swing_period)

        # Determine recent structure sequence (last 6 swings)
        structure = self._classify_structure(swing_highs, swing_lows, highs, lows)

        bos = self._detect_bos(structure, closes)
        choch = self._detect_choch(structure)

        # Score bullishness
        bullish_points = 0
        bearish_points = 0

        seq = structure.get("sequence", [])
        for item in seq[-4:]:
            if item in ("HH", "HL"):
                bullish_points += 1
            elif item in ("LH", "LL"):
                bearish_points += 1

        if bos == "BULLISH_BOS":
            bullish_points += 2
        elif bos == "BEARISH_BOS":
            bearish_points += 2

        total = bullish_points + bearish_points or 1
        if bullish_points > bearish_points:
            signal = "BULLISH_STRUCTURE"
            confidence = bullish_points / (total + 2)
        elif bearish_points > bullish_points:
            signal = "BEARISH_STRUCTURE"
            confidence = bearish_points / (total + 2)
        else:
            signal = "RANGING"
            confidence = 0.3

        if choch:
            # CHoCH is a powerful signal — boost confidence
            confidence = min(confidence + 0.2, 1.0)
            signal = choch

        details: dict[str, Any] = {
            "structure_sequence": seq,
            "bos": bos,
            "choch": choch,
            "last_swing_high": float(swing_highs[-1][1]) if swing_highs else None,
            "last_swing_low": float(swing_lows[-1][1]) if swing_lows else None,
            "bullish_points": bullish_points,
            "bearish_points": bearish_points,
        }

        return EngineResult(
            engine_name=self.name,
            signal=signal,
            confidence=round(min(confidence, 1.0), 4),
            details=details,
            weight=self.default_weight,
        )

    def _find_swing_highs(self, highs: np.ndarray, n: int) -> list[tuple[int, float]]:
        result = []
        for i in range(n, len(highs) - n):
            window = highs[i - n: i + n + 1]
            if highs[i] == max(window):
                result.append((i, highs[i]))
        return result

    def _find_swing_lows(self, lows: np.ndarray, n: int) -> list[tuple[int, float]]:
        result = []
        for i in range(n, len(lows) - n):
            window = lows[i - n: i + n + 1]
            if lows[i] == min(window):
                result.append((i, lows[i]))
        return result

    def _classify_structure(
        self,
        swing_highs: list[tuple[int, float]],
        swing_lows: list[tuple[int, float]],
        highs: np.ndarray,
        lows: np.ndarray,
    ) -> dict[str, Any]:
        # Build chronological list of swings
        all_swings: list[tuple[int, str, float]] = []
        for idx, val in swing_highs:
            all_swings.append((idx, "H", val))
        for idx, val in swing_lows:
            all_swings.append((idx, "L", val))
        all_swings.sort(key=lambda x: x[0])

        sequence: list[str] = []
        prev_high: float | None = None
        prev_low: float | None = None

        for _, kind, val in all_swings[-12:]:
            if kind == "H":
                if prev_high is not None:
                    sequence.append("HH" if val > prev_high else "LH")
                prev_high = val
            else:
                if prev_low is not None:
                    sequence.append("HL" if val > prev_low else "LL")
                prev_low = val

        return {
            "sequence": sequence,
            "last_high": prev_high,
            "last_low": prev_low,
        }

    def _detect_bos(self, structure: dict[str, Any], closes: np.ndarray) -> str | None:
        last_high = structure.get("last_high")
        last_low = structure.get("last_low")
        if last_high is None or last_low is None:
            return None
        last_close = closes[-1]
        if last_close > last_high:
            return "BULLISH_BOS"
        if last_close < last_low:
            return "BEARISH_BOS"
        return None

    def _detect_choch(self, structure: dict[str, Any]) -> str | None:
        seq = structure.get("sequence", [])
        if len(seq) < 3:
            return None
        recent = seq[-3:]
        # Bearish CHoCH: was making HH/HL now makes LL
        if "HH" in recent[:-1] and recent[-1] == "LL":
            return "BEARISH_CHOCH"
        # Bullish CHoCH: was making LL/LH now makes HH
        if "LL" in recent[:-1] and recent[-1] == "HH":
            return "BULLISH_CHOCH"
        return None
