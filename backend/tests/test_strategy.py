"""The strategy's gates: what it takes, and everything it refuses."""

from __future__ import annotations

import dataclasses
import datetime as dt

import pytest

from app.core.market.calendar import Blackout, Event
from app.core.strategy import GoldStrategy, MarketSnapshot

from factories import BASE_TIME, bearish_snapshot, bullish_snapshot, choppy_snapshot


@pytest.fixture
def strategy() -> GoldStrategy:
    return GoldStrategy()


def failed(decision) -> set[str]:
    return {gate.name for gate in decision.gates if not gate.passed}


def test_an_aligned_uptrend_with_a_pullback_produces_a_long(strategy):
    decision = strategy.evaluate(bullish_snapshot())
    assert decision.action == "LONG", failed(decision)
    assert decision.stop_loss < decision.entry < decision.take_profit


def test_an_aligned_downtrend_produces_a_short(strategy):
    decision = strategy.evaluate(bearish_snapshot())
    assert decision.action == "SHORT", failed(decision)
    assert decision.take_profit < decision.entry < decision.stop_loss


def test_a_trendless_market_is_refused(strategy):
    decision = strategy.evaluate(choppy_snapshot())
    assert decision.action == "STAND_ASIDE"
    assert "regime" in failed(decision)


def test_the_target_is_the_configured_multiple_of_the_risk(strategy):
    decision = strategy.evaluate(bullish_snapshot())
    reward = abs(decision.take_profit - decision.entry)
    assert round(reward / decision.risk_per_unit, 2) == pytest.approx(2.0, abs=0.01)


def test_every_gate_carries_the_measurement_behind_it(strategy):
    decision = strategy.evaluate(bullish_snapshot())
    assert len(decision.gates) >= 10
    assert all(gate.detail for gate in decision.gates)
    assert all(isinstance(gate.passed, bool) for gate in decision.gates)


def test_a_scheduled_release_blocks_the_trade(strategy):
    blackout = Blackout(
        active=True,
        event=Event(name="US CPI", scheduled_at=BASE_TIME + dt.timedelta(minutes=20), impact="high"),
        minutes_away=20,
    )
    decision = strategy.evaluate(bullish_snapshot(blackout=blackout))
    assert decision.action == "STAND_ASIDE"
    assert "news" in failed(decision)


def test_a_wide_spread_blocks_the_trade(strategy):
    decision = strategy.evaluate(bullish_snapshot(spread=3.00))
    assert decision.action == "STAND_ASIDE"
    assert "spread" in failed(decision)


def test_trading_outside_the_session_windows_is_refused(strategy):
    quiet_hour = BASE_TIME.replace(hour=3, minute=0)
    decision = strategy.evaluate(bullish_snapshot(now=quiet_hour))
    assert decision.action == "STAND_ASIDE"
    assert "session" in failed(decision)


def test_the_weekend_is_refused(strategy):
    saturday = dt.datetime(2026, 3, 14, 14, 0, tzinfo=dt.timezone.utc)
    decision = strategy.evaluate(bullish_snapshot(now=saturday))
    assert decision.action == "STAND_ASIDE"
    assert "session" in failed(decision)


def test_an_untradeable_quote_stops_the_evaluation(strategy):
    snapshot = bullish_snapshot()
    snapshot = dataclasses.replace(
        snapshot, quote=dataclasses.replace(snapshot.quote, tradeable=False)
    )
    decision = strategy.evaluate(snapshot)
    assert decision.action == "STAND_ASIDE"
    assert "market_open" in failed(decision)


def test_short_history_is_refused_before_anything_is_measured(strategy):
    full = bullish_snapshot()
    thin = MarketSnapshot(
        time=full.time,
        quote=full.quote,
        m15=full.m15[-20:],
        h1=full.h1,
        h4=full.h4,
        d1=full.d1,
        blackout=full.blackout,
    )
    decision = strategy.evaluate(thin)
    assert decision.action == "STAND_ASIDE"
    assert failed(decision) == {"data"}


def test_the_same_snapshot_always_yields_the_same_decision(strategy):
    snapshot = bullish_snapshot()
    first = strategy.evaluate(snapshot)
    second = strategy.evaluate(snapshot)
    assert first.as_dict() == second.as_dict()
