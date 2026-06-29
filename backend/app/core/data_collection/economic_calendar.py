"""
EconomicCalendar — Fetches real upcoming economic events.

Primary source: FCS API (free, no key needed for basic calendar).
Fallback: Twelve Data economic calendar (requires API key).

Events are filtered by currency and impact level, and sorted by time.
High-impact events within 30 minutes are flagged — the NewsEngine
uses this to block trades automatically.
"""

import datetime
from typing import Any

import httpx

from app.config import settings

# FCS API — free economic calendar, no authentication required
FCS_BASE = "https://fcsapi.com/api-v3/forex/economy_cal"


class EconomicCalendar:
    def __init__(self, api_key: str | None = None) -> None:
        self._fcs_key = api_key or getattr(settings, "FCS_API_KEY", "")
        self._td_key  = getattr(settings, "TWELVE_DATA_API_KEY", "")

    async def fetch(
        self,
        currencies: list[str] | None = None,
        impact: str | None = None,
        days_ahead: int = 7,
    ) -> list[dict[str, Any]]:
        """
        Returns upcoming economic events sorted by scheduled time (ascending).
        Each event dict:
          name, currency, impact, scheduled_at (ISO), forecast, previous, actual, is_released
        """
        events = await self._fetch_fcs(currencies, days_ahead)
        if not events:
            events = await self._fetch_twelve_data(currencies, days_ahead)

        if impact:
            events = [e for e in events if e.get("impact") == impact]

        events.sort(key=lambda e: e.get("scheduled_at", ""))
        return events

    async def _fetch_fcs(
        self, currencies: list[str] | None, days_ahead: int
    ) -> list[dict[str, Any]]:
        if not self._fcs_key:
            return []

        now = datetime.datetime.utcnow()
        end = now + datetime.timedelta(days=days_ahead)

        params: dict[str, Any] = {
            "access_key": self._fcs_key,
            "from":       now.strftime("%Y-%m-%d"),
            "to":         end.strftime("%Y-%m-%d"),
        }
        if currencies:
            params["symbol"] = ",".join(currencies)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(FCS_BASE, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return []

        events = []
        for item in data.get("response", []):
            imp = item.get("impact", "").lower()
            if imp not in ("low", "medium", "high"):
                imp = "medium"
            events.append({
                "name":         item.get("event_name", ""),
                "currency":     item.get("country", "").upper(),
                "impact":       imp,
                "scheduled_at": self._parse_dt(item.get("date", "")),
                "forecast":     item.get("forecast"),
                "previous":     item.get("previous"),
                "actual":       item.get("actual") or None,
                "is_released":  bool(item.get("actual")),
            })
        return events

    async def _fetch_twelve_data(
        self, currencies: list[str] | None, days_ahead: int
    ) -> list[dict[str, Any]]:
        if not self._td_key:
            return []

        now = datetime.datetime.utcnow()
        end = now + datetime.timedelta(days=days_ahead)

        params: dict[str, Any] = {
            "apikey":    self._td_key,
            "start":     now.strftime("%Y-%m-%d"),
            "end":       end.strftime("%Y-%m-%d"),
            "importance": "high",       # free tier only returns high-impact
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://api.twelvedata.com/economic_calendar",
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return []

        if data.get("status") == "error":
            return []

        events = []
        for item in data.get("result", {}).get("list", []):
            currency = item.get("currency", "").upper()
            if currencies and currency not in currencies:
                continue
            events.append({
                "name":         item.get("event", ""),
                "currency":     currency,
                "impact":       "high",
                "scheduled_at": item.get("datetime", ""),
                "forecast":     item.get("estimate"),
                "previous":     item.get("previous"),
                "actual":       item.get("actual") or None,
                "is_released":  bool(item.get("actual")),
            })
        return events

    def _parse_dt(self, raw: str) -> str:
        """Normalise various date strings to ISO format."""
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(raw, fmt).isoformat()
            except ValueError:
                continue
        return raw

    def get_next_high_impact(
        self, events: list[dict[str, Any]], minutes_window: int = 30
    ) -> dict[str, Any] | None:
        """
        Return the nearest high-impact event within `minutes_window` minutes,
        or None. Used by the NewsEngine to block trades.
        """
        now = datetime.datetime.utcnow()
        cutoff = now + datetime.timedelta(minutes=minutes_window)
        for event in events:
            if event.get("impact") != "high":
                continue
            try:
                evt_dt = datetime.datetime.fromisoformat(event["scheduled_at"])
                if now <= evt_dt <= cutoff:
                    return event
            except (ValueError, KeyError):
                continue
        return None
