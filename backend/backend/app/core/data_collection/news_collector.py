"""
NewsCollector — Fetches financial news from external providers.

Supports a generic REST endpoint.  Replace with real providers such as
NewsAPI, Benzinga, Polygon.io, or Alpha Vantage.
"""

import datetime
from typing import Any

import httpx

from app.config import settings


class NewsCollector:
    def __init__(self, api_url: str | None = None, api_key: str | None = None) -> None:
        self._api_url = api_url or ""
        self._api_key = api_key or ""

    async def fetch(
        self,
        symbols: list[str] | None = None,
        limit: int = 50,
        since: datetime.datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch news items. Returns list of dicts matching NewsItemCreate schema."""
        if not self._api_url:
            return self._mock_news(symbols, limit)

        async with httpx.AsyncClient() as client:
            params: dict[str, Any] = {"limit": limit}
            if symbols:
                params["symbols"] = ",".join(symbols)
            if since:
                params["published_since"] = since.isoformat()
            resp = await client.get(
                f"{self._api_url}/news",
                params=params,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json().get("news", [])

    def _mock_news(
        self, symbols: list[str] | None, limit: int
    ) -> list[dict[str, Any]]:
        now = datetime.datetime.utcnow()
        items = [
            {
                "title": "Federal Reserve signals patience on rate cuts amid sticky inflation",
                "source": "Reuters",
                "url": "https://reuters.com/mock",
                "content": "The Federal Reserve indicated it would maintain current rates...",
                "sentiment": "negative",
                "symbols": "EURUSD,USDJPY",
                "published_at": (now - datetime.timedelta(hours=2)).isoformat(),
            },
            {
                "title": "Gold surges on safe-haven demand as geopolitical tensions rise",
                "source": "Bloomberg",
                "url": "https://bloomberg.com/mock",
                "content": "Spot gold climbed 0.8% as investors sought safety...",
                "sentiment": "positive",
                "symbols": "XAUUSD",
                "published_at": (now - datetime.timedelta(hours=1)).isoformat(),
            },
            {
                "title": "EUR/USD edges lower ahead of ECB decision",
                "source": "FXStreet",
                "url": "https://fxstreet.com/mock",
                "content": "The euro fell against the dollar as traders positioned ahead...",
                "sentiment": "negative",
                "symbols": "EURUSD",
                "published_at": (now - datetime.timedelta(minutes=30)).isoformat(),
            },
        ]
        if symbols:
            filtered = [
                n for n in items
                if any(s in (n.get("symbols") or "") for s in symbols)
            ]
            return filtered[:limit]
        return items[:limit]
