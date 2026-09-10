"""
Economic-release blackout for gold.

Gold is quoted in dollars, so it is US data that moves it: CPI, non-farm
payrolls, FOMC decisions, PPI, GDP, jobless claims. Around those releases the
spread widens, liquidity vanishes and stops get taken out on a spike that
reverses minutes later. The agent does not try to predict the number — it just
refuses to be in the market when one is due.

Two sources, in order:
  1. A calendar feed (FCS API) when FCS_API_KEY is configured — real scheduled
     event times.
  2. Otherwise the recurring US release clock: the fixed times of day at which
     these numbers are published. This is deliberately conservative — it can
     only ever block trading, never permit it.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

FCS_URL = "https://fcsapi.com/api-v3/forex/economy_cal"
CACHE_TTL = dt.timedelta(minutes=30)

# Releases that reliably move the gold price.
HIGH_IMPACT_TERMS = (
    "NON-FARM", "NONFARM", "NFP", "PAYROLL", "UNEMPLOYMENT",
    "CPI", "CONSUMER PRICE", "INFLATION",
    "PPI", "PRODUCER PRICE",
    "FOMC", "FED FUNDS", "INTEREST RATE", "RATE DECISION", "FEDERAL RESERVE",
    "GDP", "RETAIL SALES", "JOBLESS CLAIMS", "ISM", "POWELL",
)

# Fallback clock (UTC) used when no calendar feed is configured.
# (hour, minute, label, weekdays) — weekdays is Monday=0 .. Friday=4.
US_RELEASE_CLOCK: tuple[tuple[int, int, str, tuple[int, ...]], ...] = (
    (12, 30, "US morning data release (CPI/PPI/NFP/claims window)", (0, 1, 2, 3, 4)),
    (14, 00, "US mid-morning data release (ISM/sentiment window)", (0, 1, 2, 3, 4)),
    (18, 00, "FOMC decision window", (2,)),
    (18, 30, "FOMC press conference window", (2,)),
)


@dataclass
class Event:
    name: str
    scheduled_at: dt.datetime
    impact: str
    currency: str = "USD"
    source: str = "feed"

    def minutes_from(self, now: dt.datetime) -> float:
        return (self.scheduled_at - now).total_seconds() / 60.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "scheduled_at": self.scheduled_at.isoformat(),
            "impact": self.impact,
            "currency": self.currency,
            "source": self.source,
        }


@dataclass
class Blackout:
    active: bool
    event: Event | None = None
    minutes_away: float = 0.0

    def reason(self) -> str:
        if not self.active or not self.event:
            return "No high-impact US release inside the blackout window"
        when = "in" if self.minutes_away >= 0 else "released"
        return (
            f"{self.event.name} {when} {abs(self.minutes_away):.0f} min "
            f"({self.event.scheduled_at.strftime('%H:%M')} UTC)"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "minutes_away": round(self.minutes_away, 1),
            "reason": self.reason(),
            "event": self.event.as_dict() if self.event else None,
        }


def is_high_impact(name: str) -> bool:
    upper = name.upper()
    return any(term in upper for term in HIGH_IMPACT_TERMS)


class EconomicCalendar:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else settings.FCS_API_KEY
        self._cache: list[Event] = []
        self._fetched_at: dt.datetime | None = None

    @property
    def source(self) -> str:
        return "fcsapi" if self._api_key else "us-release-clock"

    async def upcoming(self, now: dt.datetime | None = None, hours: int = 48) -> list[Event]:
        now = now or dt.datetime.now(dt.timezone.utc)
        if self._api_key:
            events = await self._fetch_feed(now)
            if events:
                horizon = now + dt.timedelta(hours=hours)
                return [e for e in events if now - dt.timedelta(hours=2) <= e.scheduled_at <= horizon]
        return self._release_clock(now, hours)

    async def blackout(self, now: dt.datetime | None = None) -> Blackout:
        """Is a high-impact US release close enough to stand aside for?"""
        now = now or dt.datetime.now(dt.timezone.utc)
        before = settings.NEWS_BLACKOUT_BEFORE_MIN
        after = settings.NEWS_BLACKOUT_AFTER_MIN

        nearest: Event | None = None
        nearest_delta = 1e9
        for event in await self.upcoming(now, hours=6):
            if event.impact != "high":
                continue
            delta = event.minutes_from(now)
            if -after <= delta <= before and abs(delta) < abs(nearest_delta):
                nearest, nearest_delta = event, delta

        if nearest is None:
            return Blackout(active=False)
        return Blackout(active=True, event=nearest, minutes_away=nearest_delta)

    # ── sources ───────────────────────────────────────────────────────────────

    async def _fetch_feed(self, now: dt.datetime) -> list[Event]:
        if self._fetched_at and now - self._fetched_at < CACHE_TTL:
            return self._cache
        params = {
            "access_key": self._api_key,
            "symbol": "USD",
            "from": now.strftime("%Y-%m-%d"),
            "to": (now + dt.timedelta(days=3)).strftime("%Y-%m-%d"),
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(FCS_URL, params=params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Calendar feed unavailable (%s) — using the US release clock", exc)
            return []

        events: list[Event] = []
        for row in payload.get("response", []) or []:
            name = row.get("event_name") or row.get("title") or ""
            when = self._parse(row.get("date", ""))
            if not name or when is None:
                continue
            impact = str(row.get("impact", "")).lower()
            if impact not in ("low", "medium", "high"):
                impact = "high" if is_high_impact(name) else "medium"
            elif is_high_impact(name):
                impact = "high"
            events.append(Event(name=name, scheduled_at=when, impact=impact))

        if events:
            self._cache = events
            self._fetched_at = now
        return events

    def _release_clock(self, now: dt.datetime, hours: int) -> list[Event]:
        """Recurring US publication times — the conservative fallback."""
        events: list[Event] = []
        horizon = now + dt.timedelta(hours=hours)
        day = now.date() - dt.timedelta(days=1)
        while day <= horizon.date():
            for hour, minute, label, weekdays in US_RELEASE_CLOCK:
                if day.weekday() not in weekdays:
                    continue
                when = dt.datetime.combine(
                    day, dt.time(hour, minute), tzinfo=dt.timezone.utc
                )
                events.append(
                    Event(name=label, scheduled_at=when, impact="high", source="us-release-clock")
                )
            day += dt.timedelta(days=1)
        events.sort(key=lambda e: e.scheduled_at)
        return events

    @staticmethod
    def _parse(raw: str) -> dt.datetime | None:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return dt.datetime.strptime(raw, fmt).replace(tzinfo=dt.timezone.utc)
            except ValueError:
                continue
        try:
            return dt.datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
        except ValueError:
            return None
