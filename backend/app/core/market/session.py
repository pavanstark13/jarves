"""
Trading clock for gold.

Gold trades nearly around the clock, but it does not trade *well* around the
clock: outside London and New York hours the book is thin, the spread is wide
and the moves are noise. This module answers, from the current UTC time alone,
whether we are inside a window the agent is allowed to open trades in.

Whether the venue is actually quoting is a separate, factual check — the live
quote's `tradeable` flag — and the agent uses both.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from app.config import settings


def _parse_windows(raw: str) -> list[tuple[dt.time, dt.time, str]]:
    """Parse "07:00-11:00,12:30-17:00" into comparable UTC time ranges."""
    windows: list[tuple[dt.time, dt.time, str]] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk or "-" not in chunk:
            continue
        start_raw, end_raw = chunk.split("-", 1)
        start = dt.time.fromisoformat(start_raw.strip())
        end = dt.time.fromisoformat(end_raw.strip())
        windows.append((start, end, chunk))
    return windows


def _in_window(now: dt.time, start: dt.time, end: dt.time) -> bool:
    if start <= end:
        return start <= now < end
    # Window wraps past midnight (e.g. 20:45-22:15 never does, but rollover
    # windows configured across midnight would).
    return now >= start or now < end


def label_for(now: dt.datetime) -> str:
    """Human name of the liquidity period the given UTC time falls in."""
    hour = now.hour
    if 7 <= hour < 12:
        return "LONDON"
    if 12 <= hour < 16:
        return "LONDON_NEWYORK_OVERLAP"
    if 16 <= hour < 21:
        return "NEW_YORK"
    if 22 <= hour or hour < 7:
        return "ASIA"
    return "ROLLOVER"


@dataclass
class SessionState:
    now: dt.datetime
    session: str
    tradeable_window: bool
    window: str
    is_rollover: bool
    is_weekend: bool
    is_friday_late: bool

    @property
    def can_open(self) -> bool:
        """True only when a new position may be opened right now."""
        if self.is_weekend or self.is_rollover or not self.tradeable_window:
            return False
        if self.is_friday_late and not settings.TRADE_ON_FRIDAY_CLOSE:
            return False
        return True

    def reason(self) -> str:
        if self.is_weekend:
            return "Gold market is closed for the weekend"
        if self.is_rollover:
            return "Inside the daily rollover window — spreads widen, no trading"
        if self.is_friday_late and not settings.TRADE_ON_FRIDAY_CLOSE:
            return "Friday close approaching — no new positions"
        if not self.tradeable_window:
            return f"Outside the London/NY trading windows ({settings.SESSION_WINDOWS} UTC)"
        return f"{self.session} session, inside window {self.window}"

    def as_dict(self) -> dict:
        return {
            "utc_time": self.now.isoformat(),
            "session": self.session,
            "window": self.window,
            "can_open": self.can_open,
            "is_rollover": self.is_rollover,
            "is_weekend": self.is_weekend,
            "reason": self.reason(),
        }


def evaluate(now: dt.datetime | None = None) -> SessionState:
    """Classify the given (or current) UTC moment."""
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    now = now.astimezone(dt.timezone.utc)
    clock = now.time()
    weekday = now.weekday()  # Monday=0 .. Sunday=6

    matched = ""
    for start, end, name in _parse_windows(settings.SESSION_WINDOWS):
        if _in_window(clock, start, end):
            matched = name
            break

    rollover = any(
        _in_window(clock, start, end)
        for start, end, _ in _parse_windows(settings.ROLLOVER_WINDOW)
    )

    # Gold is quoted from Sunday 22:00 UTC to Friday 21:00 UTC.
    weekend = (
        weekday == 5                              # Saturday
        or (weekday == 6 and clock < dt.time(22))  # Sunday before the open
        or (weekday == 4 and clock >= dt.time(21))  # after the Friday close
    )
    friday_late = weekday == 4 and clock >= dt.time(16)

    return SessionState(
        now=now,
        session=label_for(now),
        tradeable_window=bool(matched),
        window=matched or "none",
        is_rollover=rollover,
        is_weekend=weekend,
        is_friday_late=friday_late,
    )
