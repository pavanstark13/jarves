"""
NewsEngine — Returns confidence=0 if high-impact news is within 30 minutes
of current time (before or after).

High-impact events: CPI, NFP, FOMC, GDP, PPI, PMI, Retail Sales, Interest Rate.
"""

import datetime
from typing import Any

from app.core.engines.base import BaseEngine, EngineResult

HIGH_IMPACT_KEYWORDS = {
    "CPI", "NFP", "FOMC", "GDP", "PPI", "PMI",
    "RETAIL SALES", "INTEREST RATE", "EMPLOYMENT",
    "NON-FARM", "FEDERAL RESERVE", "FED FUNDS",
    "UNEMPLOYMENT", "CONSUMER PRICE", "PRODUCER PRICE",
}

NEWS_WINDOW_MINUTES = 30


class NewsEngine(BaseEngine):
    name = "NewsEngine"
    default_weight = 2.0  # High weight — news can kill a trade

    def analyze(self, bars: list[dict], **kwargs) -> EngineResult:
        """
        kwargs:
          economic_events: list of dicts with keys: name, impact, scheduled_at (ISO str or datetime)
          current_time: datetime UTC (optional, defaults to utcnow)
        """
        events: list[dict] = kwargs.get("economic_events", [])
        now_utc: datetime.datetime = kwargs.get("current_time", datetime.datetime.utcnow())

        if not events:
            return EngineResult(
                engine_name=self.name,
                signal="CLEAR",
                confidence=0.8,
                details={"message": "No economic events provided — assuming clear"},
                weight=self.default_weight,
            )

        nearby_high_impact: list[dict[str, Any]] = []
        nearby_medium_impact: list[dict[str, Any]] = []

        for event in events:
            scheduled = event.get("scheduled_at")
            if scheduled is None:
                continue
            if isinstance(scheduled, str):
                try:
                    scheduled = datetime.datetime.fromisoformat(scheduled)
                except ValueError:
                    continue
            # Make timezone-naive for comparison
            if scheduled.tzinfo is not None:
                scheduled = scheduled.replace(tzinfo=None)
            now_naive = now_utc.replace(tzinfo=None) if now_utc.tzinfo else now_utc

            delta = abs((scheduled - now_naive).total_seconds()) / 60.0

            impact = str(event.get("impact", "")).lower()
            name = str(event.get("name", "")).upper()

            is_keyword_match = any(kw in name for kw in HIGH_IMPACT_KEYWORDS)
            is_high = impact == "high" or is_keyword_match

            if delta <= NEWS_WINDOW_MINUTES:
                entry: dict[str, Any] = {
                    "name": event.get("name"),
                    "impact": impact,
                    "scheduled_at": scheduled.isoformat(),
                    "minutes_away": round(delta, 1),
                }
                if is_high:
                    nearby_high_impact.append(entry)
                elif impact == "medium":
                    nearby_medium_impact.append(entry)

        details: dict[str, Any] = {
            "high_impact_nearby": nearby_high_impact,
            "medium_impact_nearby": nearby_medium_impact,
            "window_minutes": NEWS_WINDOW_MINUTES,
        }

        if nearby_high_impact:
            return EngineResult(
                engine_name=self.name,
                signal="HIGH_IMPACT_NEWS",
                confidence=0.0,  # Must block trade
                details=details,
                weight=self.default_weight,
            )

        if nearby_medium_impact:
            return EngineResult(
                engine_name=self.name,
                signal="MEDIUM_IMPACT_NEWS",
                confidence=0.5,
                details=details,
                weight=self.default_weight,
            )

        return EngineResult(
            engine_name=self.name,
            signal="CLEAR",
            confidence=1.0,
            details=details,
            weight=self.default_weight,
        )
