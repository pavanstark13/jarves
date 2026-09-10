"""Offline stand-ins for the broker and the calendar."""

from __future__ import annotations

import datetime as dt

from app.core.broker.base import Account, Candle, Quote
from app.core.market.calendar import Blackout
from app.instrument import GOLD, InstrumentSpec

from factories import BASE_TIME, wavy_trend


class FakeMarket:
    """
    A market data source with a scripted gold market. Timeframes are generated
    from the same trend so the multi-timeframe gates line up.
    """

    name = "fake"
    configured = True

    def __init__(
        self,
        now: dt.datetime = BASE_TIME,
        direction: str = "up",
        spread: float = 0.30,
        tradeable: bool = True,
    ) -> None:
        self.now = now
        self.spread = spread
        self.tradeable = tradeable
        sign = 1.0 if direction == "up" else -1.0
        base = 2300.0 if direction == "up" else 2400.0
        self.series = {
            "M1": wavy_trend(200, 1, base, sign * 0.02, wave_amp=1.0, wave_period=20, end_time=now),
            "M15": wavy_trend(260, 15, base, sign * 0.18, wave_amp=4.0, wave_period=24,
                              end_time=now, bars_past_trough=7),
            "H1": wavy_trend(260, 60, base - sign * 150, sign * 0.55, wave_amp=4.0,
                             wave_period=30, end_time=now),
            "H4": wavy_trend(260, 240, base - sign * 400, sign * 1.6, wave_amp=8.0,
                             wave_period=30, end_time=now),
            "D1": wavy_trend(90, 1440, base - sign * 200, sign * 3.0, wave_amp=10.0,
                             wave_period=20, end_time=now),
        }
        self.price = self.series["M15"][-1].close
        self.spec = GOLD

    async def load_instrument_spec(self) -> InstrumentSpec:
        """The real client reads this from the venue; here it is fixed."""
        return self.spec

    async def get_candles(self, granularity: str = "M15", count: int = 300) -> list[Candle]:
        return self.series[granularity.upper()][-count:]

    async def get_quote(self) -> Quote:
        return Quote(
            time=self.now,
            bid=self.price - self.spread / 2,
            ask=self.price + self.spread / 2,
            tradeable=self.tradeable,
        )

    async def get_account(self) -> Account:
        return Account(
            balance=10_000.0, nav=10_000.0, unrealized_pl=0.0,
            margin_available=10_000.0, venue="fake",
        )


class FakeCalendar:
    """Calendar with a fixed answer, so news behaviour is testable."""

    def __init__(self, blackout: Blackout | None = None) -> None:
        self._blackout = blackout or Blackout(active=False)
        self.source = "fake"

    async def blackout(self, now: dt.datetime | None = None) -> Blackout:
        return self._blackout

    async def upcoming(self, now: dt.datetime | None = None, hours: int = 48):
        return []
