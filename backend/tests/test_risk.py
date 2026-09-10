"""Risk control: sizing arithmetic and the limits that stop trading."""

from __future__ import annotations

import datetime as dt

import pytest

from app.config import settings
from app.core.broker.base import Account, Position
from app.core.risk import RiskManager, new_day_book
from app.core.strategy import Decision

NOW = dt.datetime(2026, 3, 10, 14, 0, tzinfo=dt.timezone.utc)


def account(nav: float = 10_000.0) -> Account:
    return Account(balance=nav, nav=nav, unrealized_pl=0.0, margin_available=nav, venue="test")


def long_decision(entry: float = 2400.0, stop: float = 2395.0, target: float | None = None) -> Decision:
    risk = abs(entry - stop)
    return Decision(
        time=NOW,
        action="LONG",
        entry=entry,
        stop_loss=stop,
        take_profit=target if target is not None else entry + risk * settings.MIN_RISK_REWARD,
        risk_per_unit=risk,
        risk_reward=settings.MIN_RISK_REWARD,
        summary="test",
    )


def position() -> Position:
    return Position(
        trade_id="t1", direction="LONG", units=5, entry_price=2400.0,
        stop_loss=2395.0, take_profit=2410.0, opened_at=NOW, initial_risk=5.0,
    )


@pytest.fixture
def manager() -> RiskManager:
    return RiskManager()


def test_size_is_the_risk_budget_divided_by_the_stop_distance(manager):
    # 0.5% of $10,000 is $50; a $5 stop buys 10 ounces.
    verdict = manager.evaluate(long_decision(), account(), [], new_day_book(10_000.0), NOW)
    assert verdict.approved
    assert verdict.units == 10
    assert verdict.risk_amount == pytest.approx(50.0)


def test_size_rounds_down_so_the_risk_budget_is_never_exceeded(manager):
    verdict = manager.evaluate(
        long_decision(entry=2400.0, stop=2392.0), account(), [], new_day_book(10_000.0), NOW
    )
    # $50 / $8 = 6.25 ounces -> 6, never 7.
    assert verdict.units == 6
    assert verdict.risk_amount <= 50.0


def test_a_stop_too_wide_for_the_account_is_refused(manager):
    verdict = manager.evaluate(
        long_decision(entry=2400.0, stop=2340.0), account(nav=200.0), [], new_day_book(200.0), NOW
    )
    assert not verdict.approved
    assert "minimum" in verdict.reason


def test_an_existing_position_blocks_another(manager):
    verdict = manager.evaluate(long_decision(), account(), [position()], new_day_book(10_000.0), NOW)
    assert not verdict.approved
    assert "positions" in verdict.reason


def test_the_daily_trade_cap_is_enforced(manager):
    book = new_day_book(10_000.0)
    book.trades_opened = settings.MAX_TRADES_PER_DAY
    verdict = manager.evaluate(long_decision(), account(), [], book, NOW)
    assert not verdict.approved
    assert "Daily cap" in verdict.reason


def test_the_daily_loss_limit_stops_trading(manager):
    book = new_day_book(10_000.0)
    nav = 10_000.0 * (1 - settings.MAX_DAILY_LOSS_PCT / 100) - 1
    verdict = manager.evaluate(long_decision(), account(nav), [], book, NOW)
    assert not verdict.approved
    assert "today" in verdict.reason


def test_the_drawdown_limit_stops_trading(manager):
    book = new_day_book(10_000.0)
    book.peak_nav = 20_000.0
    verdict = manager.evaluate(long_decision(), account(10_000.0), [], book, NOW)
    assert not verdict.approved
    assert "Drawdown" in verdict.reason


def test_a_cooldown_blocks_new_trades_until_it_expires(manager):
    book = new_day_book(10_000.0)
    book.consecutive_losses = 2
    book.cooldown_until = NOW + dt.timedelta(minutes=30)
    assert not manager.evaluate(long_decision(), account(), [], book, NOW).approved
    later = NOW + dt.timedelta(minutes=31)
    assert manager.evaluate(long_decision(), account(), [], book, later).approved


def test_a_halted_agent_takes_nothing(manager):
    book = new_day_book(10_000.0)
    book.halted = True
    book.halt_reason = "drawdown limit"
    verdict = manager.evaluate(long_decision(), account(), [], book, NOW)
    assert not verdict.approved
    assert verdict.reason == "drawdown limit"


def test_leverage_caps_the_size_on_a_small_account(manager):
    # A $2 stop on a $500 account would otherwise buy far more gold than the
    # account could carry.
    verdict = manager.evaluate(
        long_decision(entry=2400.0, stop=2398.0), account(nav=500.0), [], new_day_book(500.0), NOW
    )
    if verdict.approved:
        assert verdict.notional <= 500.0 * settings.MAX_LEVERAGE + 1e-6
    else:
        assert "minimum" in verdict.reason or "Leverage" in verdict.reason


def test_inverted_levels_are_rejected_before_an_order_is_built(manager):
    broken = long_decision()
    broken.stop_loss = broken.entry + 5  # stop on the wrong side of a long
    verdict = manager.evaluate(broken, account(), [], new_day_book(10_000.0), NOW)
    assert not verdict.approved
    assert "ordered" in verdict.reason


def test_a_target_below_the_minimum_reward_is_rejected(manager):
    thin = long_decision(entry=2400.0, stop=2395.0, target=2401.0)
    verdict = manager.evaluate(thin, account(), [], new_day_book(10_000.0), NOW)
    assert not verdict.approved
    assert "Reward:risk" in verdict.reason


def test_an_account_below_the_floor_cannot_trade(manager):
    small = settings.MIN_ACCOUNT_BALANCE - 1
    verdict = manager.evaluate(long_decision(), account(small), [], new_day_book(small), NOW)
    assert not verdict.approved
    assert "floor" in verdict.reason
