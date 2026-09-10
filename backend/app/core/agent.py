"""
The trading agent: one loop, run on a timer, that does the same five things
every cycle.

    1. Look at the account and roll the day's book over at UTC midnight.
    2. Pull current gold data — quote, candles, the release calendar.
    3. Reconcile: find out what the broker did with any position we hold.
    4. Manage the open trade — breakeven, trail, time stop, news exit.
    5. If flat and permitted, evaluate the strategy, size it, and send it.

It holds no opinion between cycles. Everything it acts on is either read from
the broker or measured from candles in that same cycle, so restarting it
changes nothing about what it would do next.

Paper is the default mode. Live execution requires AGENT_MODE=live *and*
EXECUTION_CONFIRMED=true, and even then every order carries a stop.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from app.config import settings
from app.core.broker.base import Account, Broker, BrokerError, MarketClient, Position, Quote
from app.core.broker.mt5 import Mt5Broker
from app.core.broker.oanda import OandaBroker
from app.core.broker.paper import PaperBroker
from app.core.management import improved_stop, time_stop_hit
from app.core.market import session as session_clock
from app.core.market.calendar import EconomicCalendar
from app.core.risk import DayBook, RiskManager, RiskVerdict, new_day_book
from app.core.strategy import GoldStrategy, MarketSnapshot, Decision
from app.instrument import GOLD, SYMBOL
from app.services.store import Store, store as default_store

logger = logging.getLogger(__name__)

PEAK_STATE_KEY = "equity_peak"
HALT_STATE_KEY = "halt"

# Candles pulled each cycle, per timeframe.
CANDLE_COUNTS = {"M15": 260, "H1": 260, "H4": 260, "D1": 90}


@dataclass
class CycleReport:
    """What one pass of the loop observed and did."""

    time: dt.datetime
    ran: bool
    decision: Decision | None = None
    verdict: RiskVerdict | None = None
    actions: list[str] = field(default_factory=list)
    error: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "time": self.time.isoformat(),
            "ran": self.ran,
            "decision": self.decision.as_dict() if self.decision else None,
            "risk": self.verdict.as_dict() if self.verdict else None,
            "actions": self.actions,
            "error": self.error,
        }


def build_market_client() -> MarketClient:
    """The configured venue: OANDA's REST API, or a MetaTrader 5 terminal."""
    choice = settings.BROKER.strip().lower()
    if choice == "mt5":
        return Mt5Broker()
    if choice == "oanda":
        return OandaBroker()
    raise ValueError(f"Unknown BROKER '{settings.BROKER}'. Use 'oanda' or 'mt5'.")


def build_broker(
    clock: Callable[[], dt.datetime] | None = None,
) -> tuple[Broker, MarketClient]:
    """
    Returns (execution broker, market-data client).

    Both modes read the market through the configured venue. Only live mode
    sends orders there; paper mode fills them against the same real quotes.
    """
    market = build_market_client()
    if settings.is_live:
        return market, market
    return (
        PaperBroker(market, starting_balance=settings.PAPER_STARTING_BALANCE, clock=clock),
        market,
    )


class TradingAgent:
    def __init__(
        self,
        broker: Broker | None = None,
        market: MarketClient | None = None,
        strategy: GoldStrategy | None = None,
        risk: RiskManager | None = None,
        calendar: EconomicCalendar | None = None,
        store: Store | None = None,
        clock: Callable[[], dt.datetime] | None = None,
    ) -> None:
        self._clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))
        if broker is None:
            broker, market_client = build_broker(self._clock)
            market = market or market_client
        self.broker = broker
        self.market = market
        self.strategy = strategy or GoldStrategy()
        self.risk = risk or RiskManager()
        self.calendar = calendar or EconomicCalendar()
        self.store = store or default_store

        self.enabled = False
        self.book: DayBook | None = None
        self.last_cycle: CycleReport | None = None
        self.last_quote: Quote | None = None
        self.last_account: Account | None = None
        self.started_at: dt.datetime | None = None
        self.cycles = 0
        self._lock = asyncio.Lock()

    def now(self) -> dt.datetime:
        """The agent's clock. Every timestamp it writes comes from here."""
        return self._clock()

    # ── lifecycle ─────────────────────────────────────────────────────────────

    @property
    def mode(self) -> str:
        return "live" if settings.is_live else "paper"

    async def start(self) -> dict[str, Any]:
        halt = await self.store.get_state(HALT_STATE_KEY)
        if halt.get("active"):
            return {
                "enabled": False,
                "message": f"Agent is halted: {halt.get('reason', 'unknown')}. Reset it before starting.",
            }
        self.enabled = True
        self.started_at = self.now()
        await self.store.log_event("start", f"Agent started in {self.mode} mode")
        logger.info("Agent started in %s mode", self.mode)
        return {"enabled": True, "message": f"Agent running in {self.mode} mode"}

    async def stop(self, reason: str = "stopped by operator") -> dict[str, Any]:
        self.enabled = False
        await self.store.log_event("stop", reason)
        logger.info("Agent stopped: %s", reason)
        return {"enabled": False, "message": reason}

    async def halt(self, reason: str) -> None:
        """Stop trading and remember it, so a restart does not clear the limit."""
        self.enabled = False
        if self.book:
            self.book.halted = True
            self.book.halt_reason = reason
        await self.store.set_state(
            HALT_STATE_KEY,
            {"active": True, "reason": reason, "at": self.now().isoformat()},
        )
        await self.store.log_event("halt", reason)
        logger.warning("Agent halted: %s", reason)

    async def clear_halt(self) -> dict[str, Any]:
        await self.store.set_state(HALT_STATE_KEY, {"active": False})
        if self.book:
            self.book.halted = False
            self.book.halt_reason = ""
        await self.store.log_event("halt_cleared", "Halt cleared by operator")
        return {"halted": False, "message": "Halt cleared. Start the agent when ready."}

    # ── the loop ──────────────────────────────────────────────────────────────

    async def cycle(self, force: bool = False) -> CycleReport:
        """
        One pass. `force` evaluates and manages without opening new positions —
        used by the API to show what the agent sees while it is stopped.
        """
        async with self._lock:
            now = self.now()
            report = CycleReport(time=now, ran=True)
            if not self.enabled and not force:
                report.ran = False
                report.actions.append("Agent is stopped")
                return report

            try:
                await self._run_cycle(report, now, allow_entries=self.enabled)
            except BrokerError as exc:
                report.error = str(exc)
                await self.store.log_event("broker_error", str(exc))
                logger.error("Broker error: %s", exc)
            except Exception as exc:  # keep the loop alive; surface the fault
                report.error = f"{type(exc).__name__}: {exc}"
                await self.store.log_event("error", report.error)
                logger.exception("Agent cycle failed")

            self.cycles += 1
            self.last_cycle = report
            return report

    async def _run_cycle(self, report: CycleReport, now: dt.datetime, allow_entries: bool) -> None:
        # 1. Account and the day's book.
        account = await self.broker.get_account()
        self.last_account = account
        await self._refresh_book(account, now)
        assert self.book is not None

        # 2. Current market data.
        quote = await self.broker.get_quote()
        self.last_quote = quote
        candles = {
            timeframe: await self.broker.get_candles(timeframe, count)
            for timeframe, count in CANDLE_COUNTS.items()
        }

        # 3. Settle simulated fills, then reconcile against the broker's truth.
        if isinstance(self.broker, PaperBroker):
            recent_m1 = await self.broker.get_candles("M1", 120)
            settled = self.broker.settle(recent_m1, quote)
            self.broker.drain_closed()   # these are journalled here, not later
            for exit_record in settled:
                await self._record_exit(
                    exit_record["trade_id"],
                    exit_record["exit_price"],
                    exit_record["realized_pl"],
                    exit_record["exit_reason"],
                    exit_record["closed_at"],
                    exit_record["r_multiple"],
                    report,
                )
            account = await self.broker.get_account()
            self.last_account = account

        positions = await self.broker.get_open_positions()
        await self._reconcile(positions, quote, report)
        positions = await self.broker.get_open_positions()

        blackout = await self.calendar.blackout(now)

        # 4. Manage whatever is open.
        if positions:
            await self._manage(positions, quote, candles["M15"], blackout, now, report)
            positions = await self.broker.get_open_positions()

        # 5. Look for a new trade. Never in the same cycle one was closed —
        #    the exit is barely seconds old and the next cycle is a minute away.
        closed_this_cycle = any(action.startswith("Closed ") for action in report.actions)
        snapshot = MarketSnapshot(
            time=now,
            quote=quote,
            m15=candles["M15"],
            h1=candles["H1"],
            h4=candles["H4"],
            d1=candles["D1"],
            blackout=blackout,
        )
        decision = self.strategy.evaluate(snapshot)
        report.decision = decision

        if not decision.is_trade:
            await self.store.record_decision(decision, executed=False)
            return

        verdict = self.risk.evaluate(decision, account, positions, self.book, now)
        report.verdict = verdict

        if not verdict.approved:
            report.actions.append(f"Signal not taken — {verdict.reason}")
            await self.store.record_decision(decision, executed=False, verdict=verdict)
            return

        if closed_this_cycle:
            report.actions.append("Signal held back — a position closed in this same cycle")
            await self.store.record_decision(decision, executed=False, verdict=verdict)
            return

        if not allow_entries:
            report.actions.append("Signal approved but the agent is stopped — not sent")
            await self.store.record_decision(decision, executed=False, verdict=verdict)
            return

        await self._enter(decision, verdict, now, report)

    # ── day book ──────────────────────────────────────────────────────────────

    async def _refresh_book(self, account: Account, now: dt.datetime) -> None:
        """Roll the day at UTC midnight and keep the equity peak up to date."""
        today = now.date()
        if self.book is None or self.book.date != today:
            midnight = dt.datetime.combine(today, dt.time.min, tzinfo=dt.timezone.utc)
            realized_today = await self.store.realized_pl_since(midnight, mode=self.mode)
            peak_state = await self.store.get_state(PEAK_STATE_KEY, {"nav": account.nav})
            self.book = new_day_book(
                nav=account.nav - realized_today,   # the day's opening NAV
                day=today,
                peak_nav=float(peak_state.get("nav", account.nav)),
            )
            self.book.realized_pl = realized_today
            self.book.trades_opened = await self.store.trades_opened_since(midnight)
            self.book.consecutive_losses = await self.store.consecutive_losses()
            halt = await self.store.get_state(HALT_STATE_KEY)
            self.book.halted = bool(halt.get("active"))
            self.book.halt_reason = halt.get("reason", "")

        if account.nav > self.book.peak_nav:
            self.book.peak_nav = account.nav
            await self.store.set_state(PEAK_STATE_KEY, {"nav": account.nav})

        # Breaching a limit stops the agent rather than merely failing one order.
        if self.book.drawdown_pct(account.nav) >= settings.MAX_DRAWDOWN_PCT and not self.book.halted:
            await self.halt(
                f"Drawdown {self.book.drawdown_pct(account.nav):.2f}% reached the "
                f"{settings.MAX_DRAWDOWN_PCT:.2f}% limit"
            )
        elif self.book.daily_loss_pct(account.nav) >= settings.MAX_DAILY_LOSS_PCT:
            if not self.book.halted:
                self.book.halted = True
                self.book.halt_reason = (
                    f"Down {self.book.daily_loss_pct(account.nav):.2f}% today — "
                    f"trading stops until tomorrow"
                )
                await self.store.log_event("daily_limit", self.book.halt_reason)

    # ── reconciliation ────────────────────────────────────────────────────────

    async def _reconcile(self, positions: list[Position], quote: Quote, report: CycleReport) -> None:
        """Close our record of any trade the broker no longer shows as open."""
        live_ids = {p.trade_id for p in positions}
        for record in await self.store.open_trades(mode=self.mode):
            trade_id = record["broker_trade_id"]
            if trade_id in live_ids:
                continue
            exit_price, realized, reason, closed_at = await self._lookup_exit(trade_id, record, quote)
            await self._record_exit(trade_id, exit_price, realized, reason, closed_at, None, report)

    async def _lookup_exit(
        self, trade_id: str, record: dict[str, Any], quote: Quote
    ) -> tuple[float, float, str, dt.datetime]:
        """Ask the broker how a vanished trade actually ended."""
        if not isinstance(self.broker, PaperBroker) and hasattr(self.broker, "get_closed_trades"):
            try:
                for closed in await self.broker.get_closed_trades(count=50):
                    if closed["trade_id"] == trade_id:
                        closed_at = closed["closed_at"]
                        when = (
                            dt.datetime.fromisoformat(closed_at.replace("Z", "+00:00"))
                            if closed_at
                            else self.now()
                        )
                        return closed["exit_price"], closed["realized_pl"], "BROKER_CLOSE", when
            except BrokerError as exc:
                logger.warning("Could not read closed trades: %s", exc)

        # Fall back to marking out at the current price.
        price = quote.bid if record["direction"] == "LONG" else quote.ask
        move = (
            price - record["entry_price"]
            if record["direction"] == "LONG"
            else record["entry_price"] - price
        )
        return price, GOLD.pnl_for_move(move, record["units"]), "RECONCILED", self.now()

    async def _record_exit(
        self,
        trade_id: str,
        exit_price: float,
        realized: float,
        reason: str,
        closed_at: dt.datetime,
        r_multiple: float | None,
        report: CycleReport,
    ) -> None:
        closed = await self.store.close_trade(
            trade_id, exit_price, realized, reason, closed_at, r_multiple
        )
        if closed is None:
            return
        if self.book:
            self.book.realized_pl += realized
            if realized < 0:
                self.book.consecutive_losses += 1
                if self.book.consecutive_losses >= settings.MAX_CONSECUTIVE_LOSSES:
                    self.book.cooldown_until = self.now() + dt.timedelta(
                        minutes=settings.COOLDOWN_MINUTES
                    )
                    await self.store.log_event(
                        "cooldown",
                        f"{self.book.consecutive_losses} losses in a row — pausing for "
                        f"{settings.COOLDOWN_MINUTES} minutes",
                    )
            else:
                self.book.consecutive_losses = 0
        message = (
            f"Closed {closed['direction']} {closed['units']:g} oz at {exit_price:.2f} "
            f"({reason}) for ${realized:,.2f}"
        )
        report.actions.append(message)
        await self.store.log_event("exit", message)

    # ── open-trade management ─────────────────────────────────────────────────

    async def _manage(
        self,
        positions: list[Position],
        quote: Quote,
        m15: list,
        blackout,
        now: dt.datetime,
        report: CycleReport,
    ) -> None:
        from app.core import indicators as ind

        atr = ind.atr([c.high for c in m15], [c.low for c in m15], [c.close for c in m15], 14)

        for position in positions:
            price = quote.bid if position.direction == "LONG" else quote.ask
            r = position.r_multiple(price)

            # Step out of the way of a scheduled release.
            if blackout.active and settings.FLATTEN_BEFORE_NEWS:
                await self._close(position, f"NEWS:{blackout.reason()[:40]}", report)
                continue

            # A trade that has gone nowhere for too long is capital sitting idle.
            age_hours = (now - position.opened_at).total_seconds() / 3600
            if time_stop_hit(age_hours, r):
                await self._close(position, "TIME_STOP", report)
                continue

            new_stop = improved_stop(position, price, r, atr)
            if new_stop is not None:
                if await self.broker.modify_stop(position.trade_id, GOLD.round_price(new_stop)):
                    await self.store.update_stop(position.trade_id, GOLD.round_price(new_stop))
                    label = "breakeven" if abs(new_stop - position.entry_price) < 1e-6 else "trailing"
                    message = f"Moved stop to {new_stop:.2f} ({label}, {r:.2f}R open)"
                    position.stop_loss = new_stop
                    report.actions.append(message)
                    await self.store.log_event("stop_moved", message)

    async def _close(self, position: Position, reason: str, report: CycleReport) -> None:
        result = await self.broker.close_position(position.trade_id, reason)
        if not result.accepted:
            report.actions.append(f"Failed to close {position.trade_id}: {result.reason}")
            return
        if isinstance(self.broker, PaperBroker):
            for record in self.broker.drain_closed():
                await self._record_exit(
                    record["trade_id"], record["exit_price"], record["realized_pl"],
                    reason, record["closed_at"], record["r_multiple"], report,
                )
        else:
            move = (
                result.fill_price - position.entry_price
                if position.direction == "LONG"
                else position.entry_price - result.fill_price
            )
            await self._record_exit(
                position.trade_id, result.fill_price, GOLD.pnl_for_move(move, position.units),
                reason, self.now(), None, report,
            )

    # ── entry ─────────────────────────────────────────────────────────────────

    async def _enter(
        self, decision: Decision, verdict: RiskVerdict, now: dt.datetime, report: CycleReport
    ) -> None:
        client_id = f"jarves-{uuid.uuid4().hex[:16]}"
        result = await self.broker.place_order(
            direction=decision.action,
            units=verdict.units,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
            client_id=client_id,
            reason=decision.summary,
        )

        if not result.accepted:
            message = f"Order rejected: {result.reason}"
            report.actions.append(message)
            await self.store.log_event("order_rejected", message)
            await self.store.record_decision(decision, executed=False, verdict=verdict)
            return

        # Risk is recomputed from the actual fill, which may differ from the quote.
        realized_risk = abs(result.fill_price - decision.stop_loss)
        await self.store.open_trade(
            broker_trade_id=result.trade_id,
            mode=self.mode,
            venue=getattr(self.broker, "name", "unknown"),
            direction=decision.action,
            units=result.units,
            entry_price=result.fill_price,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
            initial_risk=realized_risk,
            risk_amount=realized_risk * result.units,
            opened_at=now,
            session_name=session_clock.evaluate(now).session,
            entry_reason=decision.summary,
        )
        if self.book:
            self.book.trades_opened += 1
        message = (
            f"Opened {decision.action} {result.units:g} oz {SYMBOL} at {result.fill_price:.2f}, "
            f"stop {decision.stop_loss:.2f}, target {decision.take_profit:.2f} "
            f"(risking ${realized_risk * result.units:,.2f})"
        )
        report.actions.append(message)
        await self.store.log_event("entry", message)
        await self.store.record_decision(decision, executed=True, verdict=verdict)

    # ── operator actions ──────────────────────────────────────────────────────

    async def flatten(self, reason: str = "manual flatten") -> dict[str, Any]:
        report = CycleReport(time=self.now(), ran=True)
        positions = await self.broker.get_open_positions()
        for position in positions:
            await self._close(position, reason, report)
        return {"closed": len(positions), "actions": report.actions}

    async def status(self) -> dict[str, Any]:
        halt = await self.store.get_state(HALT_STATE_KEY)
        nav = self.last_account.nav if self.last_account else 0.0
        positions = []
        try:
            positions = [p.as_dict() for p in await self.broker.get_open_positions()]
        except BrokerError:
            pass
        return {
            "symbol": SYMBOL,
            "enabled": self.enabled,
            "mode": self.mode,
            "venue": getattr(self.broker, "name", "unknown"),
            "broker": settings.BROKER,
            "broker_configured": self.market.configured if self.market else False,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "cycles": self.cycles,
            "scan_interval_seconds": settings.SCAN_INTERVAL_SECONDS,
            "halted": bool(halt.get("active")),
            "halt_reason": halt.get("reason", ""),
            "account": self.last_account.as_dict() if self.last_account else None,
            "quote": self.last_quote.as_dict() if self.last_quote else None,
            "day": self.book.as_dict(nav) if self.book else None,
            "positions": positions,
            "last_cycle": self.last_cycle.as_dict() if self.last_cycle else None,
            "session": session_clock.evaluate(self.now()).as_dict(),
        }


_agent: TradingAgent | None = None


def get_agent() -> TradingAgent:
    """The process-wide agent, built on first use."""
    global _agent
    if _agent is None:
        _agent = TradingAgent()
    return _agent


def set_agent(instance: TradingAgent | None) -> None:
    """Swap the process-wide agent — used by tests and by the API lifespan."""
    global _agent
    _agent = instance
