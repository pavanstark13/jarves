"""
PriceCollector — Fetches OHLCV price bars from a broker/data provider.

Currently implements a mock fetcher that returns synthetic data.
Replace `_fetch_from_broker` with real API calls (OANDA, Yahoo Finance, etc.).
"""

import datetime
import math
import random
from typing import Any

import httpx

from app.config import settings


class PriceCollector:
    """Collects OHLCV price bars for a given symbol and timeframe."""

    TIMEFRAME_SECONDS = {
        "M1": 60,
        "M5": 300,
        "M15": 900,
        "M30": 1800,
        "H1": 3600,
        "H4": 14400,
        "D1": 86400,
    }

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self._base_url = base_url or ""
        self._api_key = api_key or settings.BROKER_API_KEY

    async def fetch(
        self,
        symbol: str,
        timeframe: str = "H1",
        count: int = 300,
        end: datetime.datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch OHLCV bars.  Returns list of dicts:
          {timestamp, open, high, low, close, volume}
        """
        if self._base_url:
            return await self._fetch_from_broker(symbol, timeframe, count, end)
        return self._generate_synthetic(symbol, timeframe, count, end)

    async def _fetch_from_broker(
        self,
        symbol: str,
        timeframe: str,
        count: int,
        end: datetime.datetime | None,
    ) -> list[dict[str, Any]]:
        """Real broker fetch — implement per provider."""
        async with httpx.AsyncClient() as client:
            params: dict[str, Any] = {
                "symbol": symbol,
                "timeframe": timeframe,
                "count": count,
            }
            if end:
                params["end"] = end.isoformat()
            resp = await client.get(
                f"{self._base_url}/candles",
                params=params,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("candles", [])

    def _generate_synthetic(
        self,
        symbol: str,
        timeframe: str,
        count: int,
        end: datetime.datetime | None,
    ) -> list[dict[str, Any]]:
        """Deterministic synthetic OHLCV for testing / demo purposes."""
        rng = random.Random(hash(symbol) % (2**31))
        tf_seconds = self.TIMEFRAME_SECONDS.get(timeframe, 3600)
        end_ts = end or datetime.datetime.utcnow()

        # Seed price based on symbol
        price = 1.10000 if "EUR" in symbol else (1900.0 if "XAU" in symbol else 100.0)
        bars = []

        for i in range(count - 1, -1, -1):
            ts = end_ts - datetime.timedelta(seconds=tf_seconds * i)
            change_pct = rng.gauss(0, 0.0008)
            price *= 1 + change_pct

            candle_range = price * abs(rng.gauss(0, 0.001))
            high = price + candle_range * rng.random()
            low = price - candle_range * rng.random()
            open_ = price + (rng.random() - 0.5) * candle_range
            close = price

            bars.append({
                "timestamp": ts.isoformat(),
                "open": round(open_, 5),
                "high": round(max(open_, high, close), 5),
                "low": round(min(open_, low, close), 5),
                "close": round(close, 5),
                "volume": round(rng.uniform(500, 5000), 0),
            })

        return bars
