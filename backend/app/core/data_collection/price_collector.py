"""
PriceCollector — Fetches real OHLCV price bars from Twelve Data API.
Free tier: 800 calls/day, 8/min. No credit card required.
Sign up at https://twelvedata.com to get a free API key.

Symbol mapping:
  XAUUSD -> XAU/USD   EURUSD -> EUR/USD
  GBPUSD -> GBP/USD   US30   -> DJI (Dow Jones)
"""

import datetime
from typing import Any

import httpx

from app.config import settings

TWELVE_DATA_BASE = "https://api.twelvedata.com"

SYMBOL_MAP = {
    "XAUUSD": "XAU/USD",
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "GBPJPY": "GBP/JPY",
    "US30": "DJI",
    "US500": "SPX",
    "NAS100": "NDX",
    "UKOIL": "UKOIL",
    "USOIL": "WTI",
}

TIMEFRAME_MAP = {
    "M1": "1min", "M5": "5min", "M15": "15min", "M30": "30min",
    "H1": "1h", "H4": "4h", "D1": "1day", "W1": "1week",
}


class PriceCollector:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or getattr(settings, "TWELVE_DATA_API_KEY", "")

    async def fetch(
        self,
        symbol: str,
        timeframe: str = "H1",
        count: int = 300,
        end: datetime.datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch real OHLCV bars from Twelve Data.
        Falls back to a clear error if no API key is configured.
        """
        if not self._api_key:
            raise ValueError(
                "TWELVE_DATA_API_KEY is not set. "
                "Get a free key at https://twelvedata.com and add it to your .env file."
            )

        td_symbol = SYMBOL_MAP.get(symbol.upper(), symbol)
        td_interval = TIMEFRAME_MAP.get(timeframe.upper(), "1h")

        params: dict[str, Any] = {
            "symbol": td_symbol,
            "interval": td_interval,
            "outputsize": min(count, 5000),
            "apikey": self._api_key,
            "format": "JSON",
            "order": "ASC",
        }
        if end:
            params["end_date"] = end.strftime("%Y-%m-%d %H:%M:%S")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{TWELVE_DATA_BASE}/time_series", params=params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") == "error":
            raise ValueError(f"Twelve Data error: {data.get('message', 'Unknown error')}")

        raw_bars = data.get("values", [])
        if not raw_bars:
            raise ValueError(f"No data returned for {symbol} / {timeframe}")

        return [
            {
                "timestamp": bar["datetime"],
                "open":   float(bar["open"]),
                "high":   float(bar["high"]),
                "low":    float(bar["low"]),
                "close":  float(bar["close"]),
                "volume": float(bar.get("volume", 0)),
            }
            for bar in raw_bars
        ]

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        """Fetch current real-time price quote."""
        if not self._api_key:
            raise ValueError("TWELVE_DATA_API_KEY is not set.")

        td_symbol = SYMBOL_MAP.get(symbol.upper(), symbol)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{TWELVE_DATA_BASE}/quote",
                params={"symbol": td_symbol, "apikey": self._api_key},
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") == "error":
            raise ValueError(f"Twelve Data error: {data.get('message')}")

        return {
            "symbol": symbol,
            "price":      float(data.get("close", 0)),
            "open":       float(data.get("open", 0)),
            "high":       float(data.get("high", 0)),
            "low":        float(data.get("low", 0)),
            "change":     float(data.get("change", 0)),
            "change_pct": float(data.get("percent_change", 0)),
            "volume":     float(data.get("volume", 0)),
            "timestamp":  data.get("datetime", ""),
        }
