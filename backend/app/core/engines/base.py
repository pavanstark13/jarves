from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class EngineResult:
    engine_name: str
    signal: str        # e.g. "BULLISH", "BEARISH", "NEUTRAL", "DETECTED", "CLEAR"
    confidence: float  # 0.0 to 1.0
    details: dict[str, Any]
    weight: float = 1.0  # for strategy aggregation


class BaseEngine(ABC):
    """All market-understanding engines inherit from this base."""

    name: str = "BaseEngine"
    default_weight: float = 1.0

    def _to_df(self, bars: list[dict]) -> pd.DataFrame:
        """Convert list of OHLCV dicts to a DataFrame with a datetime index."""
        df = pd.DataFrame(bars)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    @abstractmethod
    def analyze(self, bars: list[dict], **kwargs) -> EngineResult:
        """Run the engine analysis and return an EngineResult."""
        ...
