"""
StrategyEngine — Aggregates all engine outputs into a Setup Quality score (0-100).

Weighting scheme:
  Each engine has a `weight` attribute.  The weighted-average confidence is
  computed only for engines whose signals are directionally aligned with the
  majority vote.  Conflicting signals reduce the final score.

Setup Quality:
  weighted_avg_confidence × 100 × alignment_bonus

  alignment_bonus = aligned / total engines
  Minimum of 3 directional engines must agree for a score > 50.
"""

from typing import Any

from app.core.engines.base import EngineResult
from app.core.engines.liquidity_engine import LiquidityEngine
from app.core.engines.news_engine import NewsEngine
from app.core.engines.session_engine import SessionEngine
from app.core.engines.smart_money_engine import SmartMoneyEngine
from app.core.engines.structure_engine import MarketStructureEngine
from app.core.engines.trend_engine import TrendEngine
from app.core.engines.volatility_engine import VolatilityEngine
from app.schemas.analysis import AnalysisResult, EngineOutput

# Map engine signals to directional bias
BULLISH_SIGNALS = {
    "BULLISH", "BULLISH_STRUCTURE", "BULLISH_CHOCH", "BULLISH_BOS",
    "BULLISH_SWEEP", "BULLISH_POI", "KILL_ZONE", "HIGH_LIQUIDITY",
    "ACTIVE_SESSION", "CLEAR", "NORMAL",
}
BEARISH_SIGNALS = {
    "BEARISH", "BEARISH_STRUCTURE", "BEARISH_CHOCH", "BEARISH_BOS",
    "BEARISH_SWEEP", "BEARISH_POI",
}
NEUTRAL_SIGNALS = {
    "NEUTRAL", "RANGING", "SIDEWAYS", "LOW_ACTIVITY", "OFF_HOURS",
    "LOW_VOL", "CLEAR", "LIQUIDITY_ABOVE", "LIQUIDITY_BELOW",
}
BLOCKING_SIGNALS = {"HIGH_IMPACT_NEWS", "WIDE_SPREAD", "LOW_LIQUIDITY", "LUNCH_LOW_LIQUIDITY"}


class StrategyEngine:
    def __init__(self) -> None:
        self.engines = [
            TrendEngine(),
            MarketStructureEngine(),
            LiquidityEngine(),
            SmartMoneyEngine(),
            SessionEngine(),
            NewsEngine(),
            VolatilityEngine(),
        ]

    def run(
        self,
        bars: list[dict],
        symbol: str,
        timeframe: str,
        spread: float = 0.0,
        economic_events: list[dict] | None = None,
        current_time: Any = None,
    ) -> AnalysisResult:
        engine_results: list[EngineResult] = []
        kwargs: dict[str, Any] = {
            "spread": spread,
            "economic_events": economic_events or [],
        }
        if current_time is not None:
            kwargs["current_time"] = current_time

        for engine in self.engines:
            result = engine.analyze(bars, **kwargs)
            engine_results.append(result)

        # Check for blocking signals
        for r in engine_results:
            if r.signal in BLOCKING_SIGNALS:
                return AnalysisResult(
                    symbol=symbol,
                    timeframe=timeframe,
                    setup_quality=0.0,
                    overall_signal="BLOCKED",
                    engines=self._to_outputs(engine_results),
                    aligned_signals=[],
                    conflicting_signals=[r.signal],
                )

        # Count directional votes (weighted)
        bull_weight = 0.0
        bear_weight = 0.0
        aligned_bull: list[str] = []
        aligned_bear: list[str] = []
        neutral: list[str] = []

        for r in engine_results:
            if r.signal in BULLISH_SIGNALS:
                bull_weight += r.weight * r.confidence
                aligned_bull.append(r.engine_name)
            elif r.signal in BEARISH_SIGNALS:
                bear_weight += r.weight * r.confidence
                aligned_bear.append(r.engine_name)
            else:
                neutral.append(r.engine_name)

        if bull_weight >= bear_weight:
            overall_signal = "LONG"
            aligned = aligned_bull
            conflicting = aligned_bear
            total_bias_weight = bull_weight
        else:
            overall_signal = "SHORT"
            aligned = aligned_bear
            conflicting = aligned_bull
            total_bias_weight = bear_weight

        if total_bias_weight == 0:
            overall_signal = "NEUTRAL"
            setup_quality = 0.0
        else:
            total_possible = sum(e.weight for e in self.engines)
            alignment_ratio = len(aligned) / max(len(aligned) + len(conflicting), 1)
            raw_confidence = total_bias_weight / total_possible
            setup_quality = round(raw_confidence * alignment_ratio * 100, 2)

            # Penalty: if fewer than 3 engines aligned, cap at 50
            if len(aligned) < 3:
                setup_quality = min(setup_quality, 50.0)

        return AnalysisResult(
            symbol=symbol,
            timeframe=timeframe,
            setup_quality=setup_quality,
            overall_signal=overall_signal,
            engines=self._to_outputs(engine_results),
            aligned_signals=aligned,
            conflicting_signals=conflicting,
        )

    @staticmethod
    def _to_outputs(results: list[EngineResult]) -> list[EngineOutput]:
        return [
            EngineOutput(
                engine_name=r.engine_name,
                signal=r.signal,
                confidence=r.confidence,
                details=r.details,
                weight=r.weight,
            )
            for r in results
        ]
