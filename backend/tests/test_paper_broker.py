"""The simulator must be pessimistic, not flattering."""

from __future__ import annotations

import datetime as dt

import pytest

from app.core.broker.base import Candle, Quote
from app.core.broker.paper import PaperBroker

NOW = dt.datetime(2026, 3, 10, 14, 0, tzinfo=dt.timezone.utc)


class Source:
    def __init__(self, bid: float = 2400.0, ask: float = 2400.3, tradeable: bool = True) -> None:
        self.bid, self.ask, self.tradeable = bid, ask, tradeable

    async def get_quote(self) -> Quote:
        return Quote(time=NOW, bid=self.bid, ask=self.ask, tradeable=self.tradeable)

    async def get_candles(self, granularity: str, count: int) -> list[Candle]:
        return []


def broker(source: Source | None = None) -> PaperBroker:
    return PaperBroker(source or Source(), starting_balance=10_000.0, clock=lambda: NOW)


def bar(high: float, low: float, minutes: int = 1) -> Candle:
    return Candle(
        time=NOW + dt.timedelta(minutes=minutes),
        open=(high + low) / 2, high=high, low=low, close=(high + low) / 2,
    )


async def test_a_long_is_filled_at_the_ask_so_the_spread_is_paid():
    paper = broker()
    result = await paper.place_order("LONG", 10, 2395.0, 2410.0, "cid", "test")
    assert result.accepted
    assert result.fill_price == 2400.3
    account = await paper.get_account()
    assert account.unrealized_pl == pytest.approx(-3.0)


async def test_a_short_is_filled_at_the_bid():
    paper = broker()
    result = await paper.place_order("SHORT", 10, 2405.0, 2390.0, "cid", "test")
    assert result.fill_price == 2400.0


async def test_the_target_pays_out_when_the_bar_reaches_it():
    paper = broker()
    await paper.place_order("LONG", 10, 2395.0, 2410.0, "cid", "test")
    exits = paper.settle([bar(high=2411.0, low=2400.0)], await paper.get_quote())
    assert len(exits) == 1
    assert exits[0]["exit_reason"] == "TAKE_PROFIT"
    assert exits[0]["realized_pl"] == pytest.approx(97.0)


async def test_a_bar_holding_both_levels_is_treated_as_a_stop():
    paper = broker()
    await paper.place_order("LONG", 10, 2395.0, 2410.0, "cid", "test")
    exits = paper.settle([bar(high=2411.0, low=2394.0)], await paper.get_quote())
    assert exits[0]["exit_reason"] == "STOP_LOSS"
    assert exits[0]["realized_pl"] < 0


async def test_bars_from_before_the_entry_cannot_close_the_trade():
    paper = broker()
    await paper.place_order("LONG", 10, 2395.0, 2410.0, "cid", "test")
    stale = Candle(time=NOW - dt.timedelta(minutes=5), open=2400, high=2411, low=2390, close=2400)
    assert paper.settle([stale], await paper.get_quote()) == []


async def test_a_size_below_the_minimum_is_refused():
    paper = broker()
    result = await paper.place_order("LONG", 0.4, 2395.0, 2410.0, "cid", "test")
    assert not result.accepted
    assert "minimum" in result.reason


async def test_a_closed_market_refuses_the_order():
    paper = broker(Source(tradeable=False))
    result = await paper.place_order("LONG", 10, 2395.0, 2410.0, "cid", "test")
    assert not result.accepted
    assert "closed" in result.reason


async def test_realised_profit_moves_the_balance():
    paper = broker()
    await paper.place_order("LONG", 10, 2395.0, 2410.0, "cid", "test")
    paper.settle([bar(high=2411.0, low=2400.0)], await paper.get_quote())
    account = await paper.get_account()
    assert account.balance == pytest.approx(10_097.0)


async def test_a_stop_can_be_tightened_on_an_open_trade():
    paper = broker()
    result = await paper.place_order("LONG", 10, 2395.0, 2410.0, "cid", "test")
    assert await paper.modify_stop(result.trade_id, 2400.3)
    positions = await paper.get_open_positions()
    assert positions[0].stop_loss == 2400.3
