"""
Synthetic gold market data for tests — deterministic and offline.

Real price series oscillate around their trend, which is what creates the
swings, pullbacks and momentum resets the strategy reads. These generators
build a trend with a sine oscillation on top, and can end the series at a
chosen point in that cycle so a test can present a market that has just
pulled back and turned.
"""

from __future__ import annotations

import datetime as dt
import math

from app.core.broker.base import Candle, Quote
from app.core.market.calendar import Blackout
from app.core.strategy import MarketSnapshot

BASE_TIME = dt.datetime(2026, 3, 10, 14, 0, tzinfo=dt.timezone.utc)  # Tuesday, NY overlap


def candle(time: dt.datetime, open_: float, close: float, wick: float = 0.5, seed: int = 0) -> Candle:
    """
    One bar. The wick length varies deterministically with the bar index so
    that no two neighbouring bars share an identical high or low — real bars
    never tie, and swing detection requires a strict extreme.
    """
    upper = wick * (0.55 + 0.45 * abs(math.sin(seed * 2.3)))
    lower = wick * (0.55 + 0.45 * abs(math.cos(seed * 1.7)))
    return Candle(
        time=time,
        open=open_,
        high=max(open_, close) + upper,
        low=min(open_, close) - lower,
        close=close,
        volume=1000.0,
    )


def wavy_trend(
    count: int,
    step_minutes: int,
    start_price: float,
    drift: float,
    wave_amp: float = 0.0,
    wave_period: int = 24,
    end_time: dt.datetime = BASE_TIME,
    bars_past_trough: int | None = None,
    wick: float = 0.5,
) -> list[Candle]:
    """
    A trending series with a sine oscillation.

    `bars_past_trough` positions the end of the series that many bars after the
    oscillation's low point (for an uptrend: just after a pullback bottomed and
    price turned back up). Pass None to leave the phase alone.
    """
    phase = 0.0
    if wave_amp and bars_past_trough is not None:
        trough_index = count - 1 - bars_past_trough
        # sin is at its minimum when (i + phase) / period == 0.75
        phase = 0.75 * wave_period - trough_index

    def price_at(i: int) -> float:
        wave = wave_amp * math.sin(2 * math.pi * (i + phase) / wave_period) if wave_amp else 0.0
        # An uptrend's wave should trough below the mean; invert for downtrends
        # so the shape is the mirror image.
        if drift < 0:
            wave = -wave
        return start_price + drift * i + wave

    first = end_time - dt.timedelta(minutes=step_minutes * (count - 1))
    candles: list[Candle] = []
    previous = price_at(0)
    for i in range(count):
        current = price_at(i)
        candles.append(
            candle(first + dt.timedelta(minutes=step_minutes * i), previous, current, wick, seed=i)
        )
        previous = current
    return candles


def _snapshot(
    m15: list[Candle],
    h1: list[Candle],
    h4: list[Candle],
    d1: list[Candle],
    now: dt.datetime,
    spread: float,
    blackout: Blackout | None = None,
) -> MarketSnapshot:
    last = m15[-1].close
    return MarketSnapshot(
        time=now,
        quote=Quote(time=now, bid=last - spread / 2, ask=last + spread / 2, tradeable=True),
        m15=m15,
        h1=h1,
        h4=h4,
        d1=d1,
        blackout=blackout or Blackout(active=False),
    )


def bullish_snapshot(
    now: dt.datetime = BASE_TIME,
    spread: float = 0.30,
    blackout: Blackout | None = None,
) -> MarketSnapshot:
    """Every timeframe trending up; M15 has just turned back up off a pullback."""
    return _snapshot(
        m15=wavy_trend(200, 15, 2300.0, 0.18, wave_amp=4.0, wave_period=24,
                       end_time=now, bars_past_trough=7),
        h1=wavy_trend(260, 60, 2150.0, 0.55, wave_amp=4.0, wave_period=30, end_time=now),
        h4=wavy_trend(260, 240, 1900.0, 1.6, wave_amp=8.0, wave_period=30, end_time=now),
        d1=wavy_trend(90, 1440, 2100.0, 3.0, wave_amp=10.0, wave_period=20, end_time=now),
        now=now,
        spread=spread,
        blackout=blackout,
    )


def bearish_snapshot(now: dt.datetime = BASE_TIME, spread: float = 0.30) -> MarketSnapshot:
    """The mirror image: every timeframe trending down into a short."""
    return _snapshot(
        m15=wavy_trend(200, 15, 2400.0, -0.18, wave_amp=4.0, wave_period=24,
                       end_time=now, bars_past_trough=7),
        h1=wavy_trend(260, 60, 2550.0, -0.55, wave_amp=4.0, wave_period=30, end_time=now),
        h4=wavy_trend(260, 240, 2800.0, -1.6, wave_amp=8.0, wave_period=30, end_time=now),
        d1=wavy_trend(90, 1440, 2600.0, -3.0, wave_amp=10.0, wave_period=20, end_time=now),
        now=now,
        spread=spread,
    )


def choppy_snapshot(now: dt.datetime = BASE_TIME) -> MarketSnapshot:
    """No trend on any timeframe — the agent must refuse to trade this."""
    return _snapshot(
        m15=wavy_trend(200, 15, 2350.0, 0.0, wave_amp=4.0, wave_period=24, end_time=now),
        h1=wavy_trend(260, 60, 2350.0, 0.0, wave_amp=10.0, wave_period=30, end_time=now),
        h4=wavy_trend(260, 240, 2350.0, 0.0, wave_amp=20.0, wave_period=40, end_time=now),
        d1=wavy_trend(90, 1440, 2350.0, 0.0, wave_amp=25.0, wave_period=20, end_time=now),
        now=now,
        spread=0.30,
    )
