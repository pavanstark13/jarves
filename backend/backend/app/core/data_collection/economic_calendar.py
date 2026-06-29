"""
EconomicCalendar — Fetches upcoming economic events.

Integrates with Forex Factory, Investing.com, or any economic calendar API.
The mock implementation returns realistic upcoming events for demo purposes.
"""

import datetime
from typing import Any

import httpx


class EconomicCalendar:
    def __init__(self, api_url: str | None = None, api_key: str | None = None) -> None:
        self._api_url = api_url or ""
        self._api_key = api_key or ""

    async def fetch(
        self,
        currencies: list[str] | None = None,
        impact: str | None = None,  # "low", "medium", "high", or None for all
        days_ahead: int = 7,
    ) -> list[dict[str, Any]]:
        """Return upcoming economic events."""
        if not self._api_url:
            return self._mock_calendar(currencies, impact, days_ahead)

        async with httpx.AsyncClient() as client:
            params: dict[str, Any] = {"days_ahead": days_ahead}
            if currencies:
                params["currencies"] = ",".join(currencies)
            if impact:
                params["impact"] = impact
            resp = await client.get(
                f"{self._api_url}/calendar",
                params=params,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json().get("events", [])

    def _mock_calendar(
        self,
        currencies: list[str] | None,
        impact: str | None,
        days_ahead: int,
    ) -> list[dict[str, Any]]:
        now = datetime.datetime.utcnow()
        events = [
            {
                "name": "US Non-Farm Payrolls",
                "currency": "USD",
                "impact": "high",
                "scheduled_at": (now + datetime.timedelta(days=2, hours=13, minutes=30)).isoformat(),
                "forecast": "185K",
                "previous": "175K",
                "actual": None,
                "is_released": False,
            },
            {
                "name": "US Consumer Price Index (CPI)",
                "currency": "USD",
                "impact": "high",
                "scheduled_at": (now + datetime.timedelta(days=5, hours=13, minutes=30)).isoformat(),
                "forecast": "3.2%",
                "previous": "3.4%",
                "actual": None,
                "is_released": False,
            },
            {
                "name": "ECB Interest Rate Decision",
                "currency": "EUR",
                "impact": "high",
                "scheduled_at": (now + datetime.timedelta(days=3, hours=12, minutes=15)).isoformat(),
                "forecast": "4.25%",
                "previous": "4.50%",
                "actual": None,
                "is_released": False,
            },
            {
                "name": "UK GDP m/m",
                "currency": "GBP",
                "impact": "medium",
                "scheduled_at": (now + datetime.timedelta(hours=6)).isoformat(),
                "forecast": "0.2%",
                "previous": "-0.1%",
                "actual": None,
                "is_released": False,
            },
            {
                "name": "FOMC Meeting Minutes",
                "currency": "USD",
                "impact": "high",
                "scheduled_at": (now + datetime.timedelta(days=1, hours=18)).isoformat(),
                "forecast": None,
                "previous": None,
                "actual": None,
                "is_released": False,
            },
        ]

        result = events
        if currencies:
            result = [e for e in result if e["currency"] in currencies]
        if impact:
            result = [e for e in result if e["impact"] == impact]
        # Filter by days_ahead
        cutoff = now + datetime.timedelta(days=days_ahead)
        result = [
            e for e in result
            if datetime.datetime.fromisoformat(e["scheduled_at"]) <= cutoff
        ]
        return result
