"""
NewsCollector — Fetches real financial news from NewsAPI.org.
Free tier: 100 requests/day.
Sign up at https://newsapi.org to get a free API key.

Filters results to forex/commodities/market-relevant content.
"""

import datetime
from typing import Any

import httpx

from app.config import settings

NEWSAPI_BASE = "https://newsapi.org/v2"

SYMBOL_KEYWORDS = {
    "XAUUSD": "gold XAU",
    "EURUSD": "euro EUR ECB",
    "GBPUSD": "pound sterling GBP",
    "US30":   "Dow Jones DJIA stock market",
    "US500":  "S&P 500 SPX",
    "NAS100": "Nasdaq tech stocks",
    "USDJPY": "yen BOJ Japan",
    "UKOIL":  "crude oil Brent",
    "USOIL":  "crude oil WTI",
}

ALWAYS_RELEVANT = [
    "Federal Reserve", "Fed rate", "CPI", "inflation", "NFP", "jobs report",
    "FOMC", "central bank", "interest rate", "dollar", "DXY", "Treasury",
]


class NewsCollector:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or getattr(settings, "NEWS_API_KEY", "")

    async def fetch(
        self,
        symbols: list[str] | None = None,
        limit: int = 20,
        since: datetime.datetime | None = None,
    ) -> list[dict[str, Any]]:
        if not self._api_key:
            raise ValueError(
                "NEWS_API_KEY is not set. "
                "Get a free key at https://newsapi.org and add it to your .env file."
            )

        query_terms: list[str] = list(ALWAYS_RELEVANT)
        if symbols:
            for s in symbols:
                kw = SYMBOL_KEYWORDS.get(s.upper())
                if kw:
                    query_terms.append(kw)

        query = " OR ".join(f'"{t}"' for t in query_terms[:10])

        from_date = since or (datetime.datetime.utcnow() - datetime.timedelta(hours=24))

        params: dict[str, Any] = {
            "q":        query,
            "language": "en",
            "sortBy":   "publishedAt",
            "pageSize": min(limit, 100),
            "from":     from_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "apiKey":   self._api_key,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{NEWSAPI_BASE}/everything", params=params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "ok":
            raise ValueError(f"NewsAPI error: {data.get('message', 'Unknown error')}")

        articles = data.get("articles", [])
        return [
            {
                "title":        a.get("title", ""),
                "source":       a.get("source", {}).get("name", ""),
                "url":          a.get("url", ""),
                "content":      (a.get("description") or a.get("content") or "")[:500],
                "sentiment":    self._score_sentiment(a.get("title", "") + " " + (a.get("description") or "")),
                "symbols":      self._match_symbols(a.get("title", "") + " " + (a.get("description") or ""), symbols),
                "published_at": a.get("publishedAt", ""),
            }
            for a in articles
        ]

    def _score_sentiment(self, text: str) -> str:
        text_lower = text.lower()
        positive = ["surges", "rises", "rallies", "gains", "strong", "bullish", "beats", "optimism", "recovery"]
        negative = ["falls", "drops", "declines", "weak", "bearish", "misses", "concern", "fears", "recession", "crash"]
        pos = sum(1 for w in positive if w in text_lower)
        neg = sum(1 for w in negative if w in text_lower)
        if pos > neg:
            return "positive"
        if neg > pos:
            return "negative"
        return "neutral"

    def _match_symbols(self, text: str, requested: list[str] | None) -> str:
        text_upper = text.upper()
        matched = []
        for sym, keywords in SYMBOL_KEYWORDS.items():
            if any(kw.upper() in text_upper for kw in keywords.split()):
                matched.append(sym)
        return ",".join(matched) if matched else ""
