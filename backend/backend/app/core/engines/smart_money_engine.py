"""
SmartMoneyEngine — Order Blocks, Fair Value Gaps (FVGs), Mitigation Blocks, Breakers.

Order Block (OB):
  Bullish OB: the last bearish candle (close < open) before a significant bullish
  impulse move (3+ consecutive bullish candles, move > 1x ATR).
  Bearish OB: the last bullish candle before a significant bearish impulse.

Fair Value Gap (FVG):
  A 3-candle imbalance where candle[1].low > candle[-1].high (bullish FVG) or
  candle[1].high < candle[-1].low (bearish FVG).

Mitigation Block: a previously tested Order Block.
Breaker: an Order Block that price has closed through, flipping its polarity.
"""

from typing import Any

import numpy as np

from app.core.engines.base import BaseEngine, EngineResult


def _atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
    tr_list = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        tr_list.append(tr)
    if not tr_list:
        return 0.0
    return float(np.mean(tr_list[-period:]))


class SmartMoneyEngine(BaseEngine):
    name = "SmartMoneyEngine"
    default_weight = 1.6
    impulse_candles: int = 3

    def analyze(self, bars: list[dict], **kwargs) -> EngineResult:
        df = self._to_df(bars)
        if len(df) < 20:
            return EngineResult(
                engine_name=self.name,
                signal="NEUTRAL",
                confidence=0.0,
                details={"error": "Not enough bars"},
                weight=self.default_weight,
            )

        opens = df["open"].values.astype(float)
        highs = df["high"].values.astype(float)
        lows = df["low"].values.astype(float)
        closes = df["close"].values.astype(float)

        atr = _atr(highs, lows, closes, 14)
        current_price = closes[-1]

        order_blocks = self._find_order_blocks(opens, highs, lows, closes, atr)
        fvgs = self._find_fvgs(highs, lows, closes)
        breakers = self._find_breakers(order_blocks, current_price)

        # Check if current price is near an order block
        near_bullish_ob = self._price_near_level(
            current_price,
            [(ob["low"], ob["high"]) for ob in order_blocks if ob["type"] == "BULLISH"],
        )
        near_bearish_ob = self._price_near_level(
            current_price,
            [(ob["low"], ob["high"]) for ob in order_blocks if ob["type"] == "BEARISH"],
        )
        inside_bullish_fvg = self._price_in_fvg(
            current_price, [fvg for fvg in fvgs if fvg["type"] == "BULLISH"]
        )
        inside_bearish_fvg = self._price_in_fvg(
            current_price, [fvg for fvg in fvgs if fvg["type"] == "BEARISH"]
        )

        bullish_score = int(near_bullish_ob) * 2 + int(inside_bullish_fvg)
        bearish_score = int(near_bearish_ob) * 2 + int(inside_bearish_fvg)

        if bullish_score > bearish_score:
            signal = "BULLISH_POI"  # Point of Interest
            confidence = min(0.5 + bullish_score * 0.15, 1.0)
        elif bearish_score > bullish_score:
            signal = "BEARISH_POI"
            confidence = min(0.5 + bearish_score * 0.15, 1.0)
        else:
            signal = "NEUTRAL"
            confidence = 0.3

        details: dict[str, Any] = {
            "order_blocks": order_blocks[-5:],
            "fair_value_gaps": fvgs[-5:],
            "breakers": breakers,
            "near_bullish_ob": near_bullish_ob,
            "near_bearish_ob": near_bearish_ob,
            "inside_bullish_fvg": inside_bullish_fvg,
            "inside_bearish_fvg": inside_bearish_fvg,
            "atr": round(atr, 6),
        }

        return EngineResult(
            engine_name=self.name,
            signal=signal,
            confidence=round(confidence, 4),
            details=details,
            weight=self.default_weight,
        )

    def _find_order_blocks(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        atr: float,
    ) -> list[dict[str, Any]]:
        obs: list[dict[str, Any]] = []
        n = self.impulse_candles
        for i in range(1, len(closes) - n):
            # Bullish OB: bearish candle before bullish impulse
            if closes[i] < opens[i]:  # bearish candle at i
                # Check next `n` candles are bullish and total move > 1x ATR
                impulse_move = closes[i + n] - closes[i]
                all_bullish = all(closes[i + j] > opens[i + j] for j in range(1, n + 1))
                if all_bullish and impulse_move > atr:
                    obs.append({
                        "type": "BULLISH",
                        "index": int(i),
                        "high": round(float(highs[i]), 6),
                        "low": round(float(lows[i]), 6),
                        "open": round(float(opens[i]), 6),
                        "close": round(float(closes[i]), 6),
                        "mitigated": False,
                    })
            # Bearish OB: bullish candle before bearish impulse
            elif closes[i] > opens[i]:
                impulse_move = closes[i] - closes[i + n]
                all_bearish = all(closes[i + j] < opens[i + j] for j in range(1, n + 1))
                if all_bearish and impulse_move > atr:
                    obs.append({
                        "type": "BEARISH",
                        "index": int(i),
                        "high": round(float(highs[i]), 6),
                        "low": round(float(lows[i]), 6),
                        "open": round(float(opens[i]), 6),
                        "close": round(float(closes[i]), 6),
                        "mitigated": False,
                    })
        # Mark mitigated OBs
        current_price = closes[-1]
        for ob in obs:
            if ob["type"] == "BULLISH" and current_price > ob["high"]:
                ob["mitigated"] = True
            elif ob["type"] == "BEARISH" and current_price < ob["low"]:
                ob["mitigated"] = True
        return obs

    def _find_fvgs(
        self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray
    ) -> list[dict[str, Any]]:
        fvgs: list[dict[str, Any]] = []
        for i in range(1, len(closes) - 1):
            # Bullish FVG: gap between candle[i-1].high and candle[i+1].low
            if lows[i + 1] > highs[i - 1]:
                fvgs.append({
                    "type": "BULLISH",
                    "index": int(i),
                    "top": round(float(lows[i + 1]), 6),
                    "bottom": round(float(highs[i - 1]), 6),
                    "filled": False,
                })
            # Bearish FVG: gap between candle[i-1].low and candle[i+1].high
            elif highs[i + 1] < lows[i - 1]:
                fvgs.append({
                    "type": "BEARISH",
                    "index": int(i),
                    "top": round(float(lows[i - 1]), 6),
                    "bottom": round(float(highs[i + 1]), 6),
                    "filled": False,
                })
        # Mark filled
        current_price = closes[-1]
        for fvg in fvgs:
            if fvg["type"] == "BULLISH" and current_price >= fvg["bottom"]:
                fvg["filled"] = current_price >= fvg["top"]
            elif fvg["type"] == "BEARISH" and current_price <= fvg["top"]:
                fvg["filled"] = current_price <= fvg["bottom"]
        return fvgs

    def _find_breakers(self, order_blocks: list[dict], current_price: float) -> list[dict]:
        """OBs that price has closed through (flipped polarity)."""
        breakers = []
        for ob in order_blocks:
            if ob["type"] == "BULLISH" and current_price < ob["low"]:
                breakers.append({**ob, "breaker_type": "BEARISH_BREAKER"})
            elif ob["type"] == "BEARISH" and current_price > ob["high"]:
                breakers.append({**ob, "breaker_type": "BULLISH_BREAKER"})
        return breakers

    def _price_near_level(self, price: float, zones: list[tuple[float, float]]) -> bool:
        for low, high in zones:
            if low <= price <= high:
                return True
        return False

    def _price_in_fvg(self, price: float, fvgs: list[dict]) -> bool:
        for fvg in fvgs:
            if not fvg["filled"] and fvg["bottom"] <= price <= fvg["top"]:
                return True
        return False
