"""The agent loop, end to end, against a scripted market."""

from __future__ import annotations

import datetime as dt

import pytest

from app.config import settings
from app.core.agent import TradingAgent
from app.core.broker.base import Candle
from app.core.broker.paper import PaperBroker
from app.core.market.calendar import Blackout, Event
from app.services.store import store

from factories import BASE_TIME
from fakes import FakeCalendar, FakeMarket


def build(market: FakeMarket | None = None, calendar: FakeCalendar | None = None,
          now: dt.datetime = BASE_TIME) -> TradingAgent:
    market = market or FakeMarket(now=now)
    clock = lambda: now  # noqa: E731 — a frozen clock keeps the test deterministic
    return TradingAgent(
        broker=PaperBroker(market, starting_balance=10_000.0, clock=clock),
        market=market,
        calendar=calendar or FakeCalendar(),
        clock=clock,
    )


async def test_a_stopped_agent_does_nothing():
    agent = build()
    report = await agent.cycle()
    assert not report.ran
    assert await store.trades() == []


async def test_a_running_agent_opens_a_trade_and_records_it():
    agent = build()
    await agent.start()
    report = await agent.cycle()

    assert report.error == ""
    assert report.decision is not None and report.decision.action == "LONG"
    assert report.verdict is not None and report.verdict.approved
    assert any("Opened LONG" in action for action in report.actions)

    trades = await store.trades()
    assert len(trades) == 1
    assert trades[0]["status"] == "OPEN"
    assert trades[0]["mode"] == "paper"
    assert trades[0]["stop_loss"] < trades[0]["entry_price"] < trades[0]["take_profit"]


async def test_the_agent_holds_one_position_at_a_time():
    agent = build()
    await agent.start()
    await agent.cycle()
    second = await agent.cycle()
    assert second.verdict is not None and not second.verdict.approved
    assert "positions" in second.verdict.reason
    assert len(await store.trades()) == 1


async def test_a_forced_cycle_evaluates_without_trading():
    agent = build()
    report = await agent.cycle(force=True)
    assert report.ran
    assert report.decision is not None
    assert await store.trades() == []
    assert any("stopped" in action for action in report.actions)


async def test_a_scheduled_release_keeps_the_agent_out():
    blackout = Blackout(
        active=True,
        event=Event(name="US CPI", scheduled_at=BASE_TIME + dt.timedelta(minutes=10), impact="high"),
        minutes_away=10,
    )
    agent = build(calendar=FakeCalendar(blackout))
    await agent.start()
    report = await agent.cycle()
    assert report.decision is not None and report.decision.action == "STAND_ASIDE"
    assert await store.trades() == []


async def test_an_open_trade_is_closed_before_a_release():
    agent = build()
    await agent.start()
    await agent.cycle()
    assert len(await store.trades(status="OPEN")) == 1

    agent.calendar = FakeCalendar(
        Blackout(
            active=True,
            event=Event(name="FOMC", scheduled_at=BASE_TIME + dt.timedelta(minutes=5), impact="high"),
            minutes_away=5,
        )
    )
    report = await agent.cycle()
    assert any("NEWS" in action for action in report.actions)
    assert await store.trades(status="OPEN") == []


async def test_the_stop_moves_to_breakeven_once_the_trade_is_up_one_r():
    agent = build()
    await agent.start()
    await agent.cycle()
    position = (await agent.broker.get_open_positions())[0]
    entry, risk = position.entry_price, position.initial_risk

    # Push the market a full R in our favour and run the loop again.
    agent.market.price = entry + risk * 1.05
    report = await agent.cycle()

    assert any("breakeven" in action for action in report.actions)
    moved = (await agent.broker.get_open_positions())[0]
    assert moved.stop_loss == pytest.approx(entry, abs=0.01)


async def test_a_stopped_out_trade_is_journalled_with_its_loss():
    agent = build()
    await agent.start()
    await agent.cycle()
    position = (await agent.broker.get_open_positions())[0]

    # A later M1 bar trades through the stop.
    agent.market.series["M1"] = agent.market.series["M1"] + [
        Candle(
            time=BASE_TIME + dt.timedelta(minutes=5),
            open=position.entry_price,
            high=position.entry_price,
            low=position.stop_loss - 1.0,
            close=position.stop_loss - 0.5,
        )
    ]
    report = await agent.cycle()

    assert any("STOP_LOSS" in action for action in report.actions)
    closed = await store.trades(status="CLOSED")
    assert len(closed) == 1
    assert closed[0]["realized_pl"] < 0
    assert closed[0]["r_multiple"] == pytest.approx(-1.0, abs=0.05)


async def test_no_new_trade_is_opened_in_the_cycle_that_closed_one():
    agent = build()
    await agent.start()
    await agent.cycle()
    position = (await agent.broker.get_open_positions())[0]
    agent.market.series["M1"] = agent.market.series["M1"] + [
        Candle(
            time=BASE_TIME + dt.timedelta(minutes=5),
            open=position.entry_price, high=position.entry_price,
            low=position.stop_loss - 1.0, close=position.stop_loss - 0.5,
        )
    ]
    report = await agent.cycle()
    assert not any("Opened" in action for action in report.actions)


async def test_flatten_closes_everything_on_demand():
    agent = build()
    await agent.start()
    await agent.cycle()
    result = await agent.flatten("test")
    assert result["closed"] == 1
    assert await store.trades(status="OPEN") == []


async def test_a_halt_survives_a_restart_and_refuses_to_start():
    agent = build()
    await agent.halt("drawdown limit reached")
    assert not agent.enabled

    fresh = build()  # a new process would rebuild the agent like this
    result = await fresh.start()
    assert not result["enabled"]
    assert "halted" in result["message"]

    await fresh.clear_halt()
    assert (await fresh.start())["enabled"]


async def test_a_broker_failure_is_reported_without_killing_the_loop():
    agent = build()
    await agent.start()

    async def explode() -> None:
        raise RuntimeError("connection reset")

    agent.broker.get_account = explode  # type: ignore[method-assign]
    report = await agent.cycle()
    assert "connection reset" in report.error
    assert agent.enabled  # the agent stays up and tries again next cycle


async def test_the_daily_loss_limit_halts_trading_for_the_day():
    agent = build()
    await agent.start()
    await agent.cycle()  # establishes the day's book

    assert agent.book is not None
    agent.book.start_nav = 10_000.0
    limit_breached = 10_000.0 * (1 - settings.MAX_DAILY_LOSS_PCT / 100) - 1
    account = await agent.broker.get_account()
    agent.book.peak_nav = 10_000.0

    await agent._refresh_book(
        type(account)(
            balance=limit_breached, nav=limit_breached, unrealized_pl=0.0,
            margin_available=limit_breached, venue="paper",
        ),
        BASE_TIME,
    )
    assert agent.book.halted
    assert "today" in agent.book.halt_reason


async def test_status_reports_the_mode_and_the_limits_in_force():
    agent = build()
    await agent.start()
    await agent.cycle()
    status = await agent.status()
    assert status["symbol"] == "XAUUSD"
    assert status["mode"] == "paper"
    assert status["enabled"] is True
    assert status["day"]["trades_opened"] == 1
    assert len(status["positions"]) == 1
