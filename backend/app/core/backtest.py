"""
Backtest: the live strategy replayed over real gold history.

This imports GoldStrategy, RiskManager and the shared management rules rather
than reimplementing them, so what it measures is what the agent would actually
have done. Two things it is careful about:

  * No look-ahead. At each M15 bar, the higher timeframes are truncated to
    candles that had already closed at that moment.
  * No optimistic fills. Entries pay an assumed spread, and when a bar contains
    both the stop and the target the stop is taken.

It is a measurement of the rules against history, not a prediction. Slippage,
real spread variation and news gaps make live results worse, not better.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import asdict, dataclass, field
from typing import Any

from app.config import settings
from app.core import indicators as ind
from app.core.broker.base import Candle, Position, Quote
from app.core.broker.oanda import OandaBroker
from app.core.management import improved_stop, time_stop_hit
from app.core.market import session as session_clock
from app.core.market.calendar import EconomicCalendar
from app.core.risk import RiskManager, new_day_book
from app.core.broker.base import Account
from app.core.strategy import GoldStrategy, MarketSnapshot
from app.instrument import GOLD, SYMBOL

logger = logging.getLogger(__name__)

WARMUP_BARS = 260  # M15 bars needed before the first evaluation


@dataclass
class BacktestTrade:
    direction: str
    units: float
    entry_time: str
    entry_price: float
    exit_time: str
    exit_price: float
    stop_loss: float
    take_profit: float
    r_multiple: float
    pnl: float
    exit_reason: str
    session: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BacktestResult:
    symbol: str = SYMBOL
    start: str = ""
    end: str = ""
    bars_tested: int = 0
    starting_balance: float = 0.0
    ending_balance: float = 0.0
    trades: list[BacktestTrade] = field(default_factory=list)
    equity_curve: list[dict[str, Any]] = field(default_factory=list)
    assumed_spread: float = 0.0
    note: str = ""

    # ── measured performance ──────────────────────────────────────────────────

    @property
    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def wins(self) -> int:
        return sum(1 for t in self.trades if t.pnl > 0)

    @property
    def losses(self) -> int:
        return sum(1 for t in self.trades if t.pnl < 0)

    @property
    def win_rate(self) -> float:
        return (self.wins / self.total_trades * 100.0) if self.total_trades else 0.0

    @property
    def profit_factor(self) -> float:
        gains = sum(t.pnl for t in self.trades if t.pnl > 0)
        pains = abs(sum(t.pnl for t in self.trades if t.pnl < 0))
        return gains / pains if pains > 0 else 0.0

    @property
    def expectancy_r(self) -> float:
        if not self.trades:
            return 0.0
        return sum(t.r_multiple for t in self.trades) / self.total_trades

    @property
    def max_drawdown_pct(self) -> float:
        peak = self.starting_balance
        worst = 0.0
        for point in self.equity_curve:
            equity = point["equity"]
            peak = max(peak, equity)
            if peak > 0:
                worst = max(worst, (peak - equity) / peak * 100.0)
        return worst

    def as_dict(self, include_trades: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "symbol": self.symbol,
            "start": self.start,
            "end": self.end,
            "bars_tested": self.bars_tested,
            "starting_balance": round(self.starting_balance, 2),
            "ending_balance": round(self.ending_balance, 2),
            "total_pnl": round(self.ending_balance - self.starting_balance, 2),
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": round(self.win_rate, 2),
            "profit_factor": round(self.profit_factor, 2),
            "expectancy_r": round(self.expectancy_r, 3),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "assumed_spread": self.assumed_spread,
            "note": self.note,
            "equity_curve": self.equity_curve,
        }
        if include_trades:
            payload["trades"] = [t.as_dict() for t in self.trades]
        return payload


class Backtester:
    def __init__(
        self,
        broker: OandaBroker | None = None,
        strategy: GoldStrategy | None = None,
        risk: RiskManager | None = None,
        calendar: EconomicCalendar | None = None,
    ) -> None:
        self.broker = broker or OandaBroker()
        self.strategy = strategy or GoldStrategy()
        self.risk = risk or RiskManager()
        self.calendar = calendar or EconomicCalendar()

    async def load_history(self, days: int) -> dict[str, list[Candle]]:
        """Fetch every timeframe, with enough lead-in for the slow averages."""
        end = dt.datetime.now(dt.timezone.utc)
        start = end - dt.timedelta(days=days)
        # The H4 EMA200 needs roughly 200 four-hour bars of history before the
        # window being tested, plus weekends.
        lead_in = start - dt.timedelta(days=90)
        return {
            "M15": await self.broker.get_candles_range("M15", start - dt.timedelta(days=5), end),
            "H1": await self.broker.get_candles_range("H1", lead_in, end),
            "H4": await self.broker.get_candles_range("H4", lead_in, end),
            "D1": await self.broker.get_candles_range("D1", lead_in, end),
        }

    async def run(
        self,
        days: int = 60,
        starting_balance: float = 10_000.0,
        assumed_spread: float = 0.30,
        history: dict[str, list[Candle]] | None = None,
    ) -> BacktestResult:
        history = history or await self.load_history(days)
        m15 = history["M15"]
        if len(m15) <= WARMUP_BARS:
            return BacktestResult(
                starting_balance=starting_balance,
                ending_balance=starting_balance,
                note=f"Only {len(m15)} M15 bars available; {WARMUP_BARS} are needed to warm up.",
            )

        result = BacktestResult(
            start=m15[WARMUP_BARS].time.isoformat(),
            end=m15[-1].time.isoformat(),
            starting_balance=starting_balance,
            ending_balance=starting_balance,
            assumed_spread=assumed_spread,
            note=(
                "Mid-price candles with a flat assumed spread; stops are taken "
                "before targets inside the same bar."
            ),
        )

        balance = starting_balance
        book = new_day_book(balance, m15[WARMUP_BARS].time.date())
        position: Position | None = None
        entry_session = ""

        for i in range(WARMUP_BARS, len(m15)):
            bar = m15[i]
            now = bar.time

            # New UTC day: reset the day's counters, exactly as the agent does.
            if now.date() != book.date:
                book = new_day_book(balance, now.date(), peak_nav=book.peak_nav)

            window = m15[: i + 1]
            highs = [c.high for c in window[-60:]]
            lows = [c.low for c in window[-60:]]
            closes = [c.close for c in window[-60:]]
            atr = ind.atr(highs, lows, closes, 14)

            # ── manage an open trade against this bar ─────────────────────────
            if position is not None:
                exit_price, reason = self._exit_on_bar(position, bar)
                if exit_price is None:
                    price = bar.close
                    r = position.r_multiple(price)
                    age = (now - position.opened_at).total_seconds() / 3600
                    if time_stop_hit(age, r):
                        exit_price, reason = price, "TIME_STOP"
                    else:
                        moved = improved_stop(position, price, r, atr)
                        if moved is not None:
                            position.stop_loss = GOLD.round_price(moved)

                if exit_price is not None:
                    move = (
                        exit_price - position.entry_price
                        if position.direction == "LONG"
                        else position.entry_price - exit_price
                    )
                    pnl = GOLD.pnl_for_move(move, position.units)
                    balance += pnl
                    book.realized_pl += pnl
                    if pnl < 0:
                        book.consecutive_losses += 1
                        if book.consecutive_losses >= settings.MAX_CONSECUTIVE_LOSSES:
                            book.cooldown_until = now + dt.timedelta(minutes=settings.COOLDOWN_MINUTES)
                    else:
                        book.consecutive_losses = 0
                    result.trades.append(
                        BacktestTrade(
                            direction=position.direction,
                            units=position.units,
                            entry_time=position.opened_at.isoformat(),
                            entry_price=round(position.entry_price, 3),
                            exit_time=now.isoformat(),
                            exit_price=round(exit_price, 3),
                            stop_loss=round(position.stop_loss or 0.0, 3),
                            take_profit=round(position.take_profit or 0.0, 3),
                            r_multiple=round(
                                move / position.initial_risk if position.initial_risk else 0.0, 3
                            ),
                            pnl=round(pnl, 2),
                            exit_reason=reason,
                            session=entry_session,
                        )
                    )
                    result.equity_curve.append(
                        {"time": now.isoformat(), "equity": round(balance, 2)}
                    )
                    book.peak_nav = max(book.peak_nav, balance)
                    position = None
                    continue  # no re-entry on the bar that closed a trade

            if position is not None:
                continue  # one position at a time

            # ── look for an entry ─────────────────────────────────────────────
            snapshot = MarketSnapshot(
                time=now,
                quote=Quote(
                    time=now,
                    bid=bar.close - assumed_spread / 2,
                    ask=bar.close + assumed_spread / 2,
                    tradeable=True,
                ),
                m15=window,
                h1=self._closed_by(history["H1"], now),
                h4=self._closed_by(history["H4"], now),
                d1=self._closed_by(history["D1"], now),
                blackout=await self.calendar.blackout(now),
            )
            decision = self.strategy.evaluate(snapshot)
            if not decision.is_trade:
                continue

            account = Account(
                balance=balance, nav=balance, unrealized_pl=0.0,
                margin_available=balance, venue="backtest",
            )
            verdict = self.risk.evaluate(decision, account, [], book, now)
            if not verdict.approved:
                continue

            position = Position(
                trade_id=f"bt-{len(result.trades) + 1}",
                direction=decision.action,
                units=verdict.units,
                entry_price=decision.entry,
                stop_loss=decision.stop_loss,
                take_profit=decision.take_profit,
                opened_at=now,
                initial_risk=decision.risk_per_unit,
            )
            entry_session = session_clock.evaluate(now).session
            book.trades_opened += 1

        result.bars_tested = len(m15) - WARMUP_BARS
        result.ending_balance = balance
        if not result.equity_curve:
            result.equity_curve = [
                {"time": result.start, "equity": round(starting_balance, 2)}
            ]
        return result

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _closed_by(candles: list[Candle], now: dt.datetime) -> list[Candle]:
        """Only candles that had already closed — the guard against look-ahead."""
        return [c for c in candles if c.time <= now]

    @staticmethod
    def _exit_on_bar(position: Position, bar: Candle) -> tuple[float | None, str]:
        """Did this bar's range take the stop or the target? Stop wins ties."""
        stop, target = position.stop_loss, position.take_profit
        if position.direction == "LONG":
            if stop is not None and bar.low <= stop:
                return stop, "STOP_LOSS"
            if target is not None and bar.high >= target:
                return target, "TAKE_PROFIT"
        else:
            if stop is not None and bar.high >= stop:
                return stop, "STOP_LOSS"
            if target is not None and bar.low <= target:
                return target, "TAKE_PROFIT"
        return None, ""
