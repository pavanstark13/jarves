from typing import Any, Optional

from pydantic import BaseModel

from app.schemas.market_data import OHLCVBar, NewsItemRead


class EngineOutput(BaseModel):
    engine_name: str
    signal: str
    confidence: float
    details: dict[str, Any]
    weight: float = 1.0


class AnalysisRequest(BaseModel):
    symbol: str
    timeframe: str
    bars: list[OHLCVBar]
    current_spread: Optional[float] = None
    news_items: Optional[list[NewsItemRead]] = None


class AnalysisResult(BaseModel):
    symbol: str
    timeframe: str
    setup_quality: float  # 0-100
    overall_signal: str   # LONG / SHORT / NEUTRAL
    engines: list[EngineOutput]
    aligned_signals: list[str]
    conflicting_signals: list[str]
    ai_explanation: Optional[str] = None
