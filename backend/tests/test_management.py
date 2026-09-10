"""Trade management: the stop only ever moves toward the position."""

from __future__ import annotations

import datetime as dt

from app.config import settings
from app.core.broker.base import Position
from app.core.management import improved_stop, time_stop_hit

NOW = dt.datetime(2026, 3, 10, 14, 0, tzinfo=dt.timezone.utc)


def long_position(stop: float = 2395.0) -> Position:
    return Position(
        trade_id="t1", direction="LONG", units=5, entry_price=2400.0,
        stop_loss=stop, take_profit=2410.0, opened_at=NOW, initial_risk=5.0,
    )


def short_position(stop: float = 2405.0) -> Position:
    return Position(
        trade_id="t2", direction="SHORT", units=5, entry_price=2400.0,
        stop_loss=stop, take_profit=2390.0, opened_at=NOW, initial_risk=5.0,
    )


def test_nothing_moves_before_the_trade_is_in_profit():
    assert improved_stop(long_position(), 2402.0, 0.4, 2.0) is None


def test_the_stop_goes_to_breakeven_at_one_r():
    assert improved_stop(long_position(), 2405.0, 1.0, 2.0) == 2400.0


def test_the_stop_trails_once_the_trade_runs():
    stop = improved_stop(long_position(stop=2400.0), 2412.0, 2.4, 2.0)
    assert stop == 2412.0 - settings.TRAIL_ATR_MULTIPLE * 2.0


def test_a_trailing_stop_is_never_pulled_back():
    # Price has come back in; the existing stop is already better.
    assert improved_stop(long_position(stop=2409.0), 2410.0, 2.0, 2.0) is None


def test_a_short_trails_downward():
    stop = improved_stop(short_position(stop=2400.0), 2388.0, 2.4, 2.0)
    assert stop == 2388.0 + settings.TRAIL_ATR_MULTIPLE * 2.0


def test_a_short_stop_is_never_raised_again():
    assert improved_stop(short_position(stop=2391.0), 2390.0, 2.0, 2.0) is None


def test_the_time_stop_only_fires_on_a_trade_going_nowhere():
    assert time_stop_hit(settings.MAX_TRADE_HOURS + 1, 0.3)
    assert not time_stop_hit(settings.MAX_TRADE_HOURS + 1, 1.5)
    assert not time_stop_hit(1.0, 0.0)
