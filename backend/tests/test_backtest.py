"""The backtest must replay the live rules without cheating."""

from __future__ import annotations

import datetime as dt

from app.core.backtest import Backtester, WARMUP_BARS

from factories import BASE_TIME, wavy_trend
from fakes import FakeCalendar


def history(bars: int = 400) -> dict[str, list]:
    end = BASE_TIME
    return {
        "M15": wavy_trend(bars, 15, 2300.0, 0.18, wave_amp=4.0, wave_period=24,
                          end_time=end, bars_past_trough=7),
        "H1": wavy_trend(400, 60, 2150.0, 0.55, wave_amp=4.0, wave_period=30, end_time=end),
        "H4": wavy_trend(400, 240, 1900.0, 1.6, wave_amp=8.0, wave_period=30, end_time=end),
        "D1": wavy_trend(120, 1440, 2100.0, 3.0, wave_amp=10.0, wave_period=20, end_time=end),
    }


def backtester() -> Backtester:
    return Backtester(calendar=FakeCalendar())


async def test_higher_timeframes_are_truncated_to_what_had_already_closed():
    candles = wavy_trend(50, 60, 2300.0, 0.5, end_time=BASE_TIME)
    cutoff = candles[20].time
    visible = Backtester._closed_by(candles, cutoff)
    assert all(candle.time <= cutoff for candle in visible)
    assert len(visible) == 21


async def test_a_bar_holding_both_levels_is_scored_as_a_stop():
    from app.core.broker.base import Candle, Position

    position = Position(
        trade_id="bt-1", direction="LONG", units=5, entry_price=2400.0,
        stop_loss=2395.0, take_profit=2410.0, opened_at=BASE_TIME, initial_risk=5.0,
    )
    bar = Candle(time=BASE_TIME, open=2400, high=2411, low=2394, close=2400)
    price, reason = Backtester._exit_on_bar(position, bar)
    assert reason == "STOP_LOSS"
    assert price == 2395.0


async def test_too_little_history_reports_instead_of_pretending():
    result = await backtester().run(
        history={"M15": [], "H1": [], "H4": [], "D1": []}, starting_balance=5_000.0
    )
    assert result.total_trades == 0
    assert "warm up" in result.note
    assert result.ending_balance == 5_000.0


async def test_a_run_over_a_trending_market_produces_measurable_results():
    result = await backtester().run(history=history(), starting_balance=10_000.0)
    assert result.bars_tested > 0
    assert result.starting_balance == 10_000.0
    # Every trade it took must carry a real exit and a measured R multiple.
    for trade in result.trades:
        assert trade.exit_reason
        assert trade.entry_time < trade.exit_time
        assert trade.direction in ("LONG", "SHORT")
    payload = result.as_dict()
    assert payload["symbol"] == "XAUUSD"
    assert "assumed_spread" in payload


async def test_the_result_reports_how_the_fills_were_assumed():
    result = await backtester().run(history=history(), assumed_spread=0.4)
    assert result.assumed_spread == 0.4
    assert "spread" in result.note


async def test_the_same_history_backtests_identically():
    data = history()
    first = await backtester().run(history=data, starting_balance=10_000.0)
    second = await backtester().run(history=data, starting_balance=10_000.0)
    assert first.as_dict() == second.as_dict()
