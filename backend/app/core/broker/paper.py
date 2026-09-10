"""
Paper broker — the default execution mode.

It runs the exact same agent code path as live trading but fills orders itself
against real OANDA quotes, so the track record it produces is honest rather
than flattering:

  * entries pay the live spread (buy the ask, sell the bid);
  * stops and targets are checked against real M1 bars, not just the polled
    quote, so a level touched between two cycles still counts;
  * when one bar contains both the stop and the target, the stop is taken —
    the pessimistic assumption, because the true sequence is unknowable.

Market data comes from the injected price source (the OANDA client), so paper
mode still needs OANDA credentials — it simulates the money, not the market.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Callable

from app.core.broker.base import Account, Broker, Candle, OrderResult, Position, Quote
from app.instrument import GOLD, InstrumentSpec

logger = logging.getLogger(__name__)


class PaperBroker(Broker):
    name = "paper"

    def __init__(
        self,
        price_source: Broker,
        starting_balance: float = 10_000.0,
        spec: InstrumentSpec | None = None,
        clock: Callable[[], dt.datetime] | None = None,
    ) -> None:
        self._prices = price_source
        # A fill is stamped with when we traded, not with the timestamp the
        # price carries — they are different facts, and tests drive the clock.
        self._clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))
        self.starting_balance = starting_balance
        self.realized_pl = 0.0
        self.spec = spec or GOLD
        self._positions: dict[str, Position] = {}
        self._closed: list[dict[str, Any]] = []
        self._last_quote: Quote | None = None
        self._seq = 0

    # ── state restore ─────────────────────────────────────────────────────────

    def restore(self, realized_pl: float, positions: list[Position]) -> None:
        """Rebuild simulator state after a restart from persisted trades."""
        self.realized_pl = realized_pl
        self._positions = {p.trade_id: p for p in positions}
        for p in positions:
            try:
                self._seq = max(self._seq, int(str(p.trade_id).rsplit("-", 1)[-1]))
            except ValueError:
                continue

    # ── market data passthrough ───────────────────────────────────────────────

    async def get_candles(self, granularity: str = "M15", count: int = 300) -> list[Candle]:
        return await self._prices.get_candles(granularity, count)

    async def get_quote(self) -> Quote:
        quote = await self._prices.get_quote()
        self._last_quote = quote
        return quote

    # ── account ───────────────────────────────────────────────────────────────

    async def get_account(self) -> Account:
        quote = self._last_quote or await self.get_quote()
        unrealized = sum(self._unrealized(p, quote) for p in self._positions.values())
        balance = self.starting_balance + self.realized_pl
        return Account(
            balance=balance,
            nav=balance + unrealized,
            unrealized_pl=unrealized,
            margin_available=balance + unrealized,
            currency="USD",
            venue="paper",
        )

    def _unrealized(self, position: Position, quote: Quote) -> float:
        exit_price = quote.bid if position.direction == "LONG" else quote.ask
        move = (
            exit_price - position.entry_price
            if position.direction == "LONG"
            else position.entry_price - exit_price
        )
        return self.spec.pnl_for_move(move, position.units)

    async def get_open_positions(self) -> list[Position]:
        quote = self._last_quote or await self.get_quote()
        for position in self._positions.values():
            position.unrealized_pl = self._unrealized(position, quote)
        return list(self._positions.values())

    # ── fill simulation ───────────────────────────────────────────────────────

    def settle(self, bars: list[Candle], quote: Quote) -> list[dict[str, Any]]:
        """
        Walk recent M1 bars and close any position whose stop or target traded.
        Returns the exits that happened, so the agent can journal them.
        """
        self._last_quote = quote
        exits: list[dict[str, Any]] = []
        for trade_id, position in list(self._positions.items()):
            for bar in bars:
                if bar.time <= position.opened_at:
                    continue
                hit = self._exit_level(position, bar)
                if hit is None:
                    continue
                price, why = hit
                exits.append(self._close(trade_id, price, why, bar.time))
                break
        return exits

    def _exit_level(self, position: Position, bar: Candle) -> tuple[float, str] | None:
        stop, target = position.stop_loss, position.take_profit
        if position.direction == "LONG":
            stop_hit = stop is not None and bar.low <= stop
            target_hit = target is not None and bar.high >= target
        else:
            stop_hit = stop is not None and bar.high >= stop
            target_hit = target is not None and bar.low <= target
        # Both inside one bar: assume the stop went first.
        if stop_hit:
            return float(stop), "STOP_LOSS"
        if target_hit:
            return float(target), "TAKE_PROFIT"
        return None

    def _close(
        self, trade_id: str, price: float, reason: str, when: dt.datetime | None = None
    ) -> dict[str, Any]:
        position = self._positions.pop(trade_id)
        move = (
            price - position.entry_price
            if position.direction == "LONG"
            else position.entry_price - price
        )
        pnl = self.spec.pnl_for_move(move, position.units)
        self.realized_pl += pnl
        record = {
            "trade_id": trade_id,
            "direction": position.direction,
            "units": position.units,
            "entry_price": position.entry_price,
            "exit_price": price,
            "realized_pl": pnl,
            "r_multiple": (move / position.initial_risk) if position.initial_risk > 0 else 0.0,
            "opened_at": position.opened_at,
            "closed_at": when or self._clock(),
            "exit_reason": reason,
        }
        self._closed.append(record)
        logger.info("Paper exit %s %s @ %.3f (%s) pnl=%.2f", position.direction, trade_id, price, reason, pnl)
        return record

    # ── orders ────────────────────────────────────────────────────────────────

    async def place_order(
        self,
        direction: str,
        units: float,
        stop_loss: float,
        take_profit: float,
        client_id: str,
        reason: str = "",
    ) -> OrderResult:
        units = self.spec.round_units(abs(units))
        if units < self.spec.min_trade_units:
            return OrderResult(accepted=False, reason="Position size below minimum trade size")

        quote = await self.get_quote()
        if not quote.tradeable:
            return OrderResult(accepted=False, reason="Market is closed")

        # Pay the spread, exactly as a real market order would.
        fill = quote.ask if direction == "LONG" else quote.bid
        self._seq += 1
        trade_id = f"paper-{self._seq}"
        position = Position(
            trade_id=trade_id,
            direction=direction,
            units=units,
            entry_price=fill,
            stop_loss=self.spec.round_price(stop_loss),
            take_profit=self.spec.round_price(take_profit),
            opened_at=self._clock(),
            initial_risk=abs(fill - stop_loss),
            metadata={"client_id": client_id, "reason": reason},
        )
        self._positions[trade_id] = position
        logger.info("Paper entry %s %s units @ %.3f", direction, units, fill)
        return OrderResult(accepted=True, trade_id=trade_id, fill_price=fill, units=units, reason="filled")

    async def modify_stop(self, trade_id: str, stop_loss: float) -> bool:
        position = self._positions.get(trade_id)
        if not position:
            return False
        position.stop_loss = self.spec.round_price(stop_loss)
        return True

    async def close_position(self, trade_id: str, reason: str = "manual") -> OrderResult:
        if trade_id not in self._positions:
            return OrderResult(accepted=False, reason="No such open paper trade")
        quote = await self.get_quote()
        position = self._positions[trade_id]
        price = quote.bid if position.direction == "LONG" else quote.ask
        record = self._close(trade_id, price, reason)
        return OrderResult(
            accepted=True,
            trade_id=trade_id,
            fill_price=price,
            units=record["units"],
            reason=reason,
        )

    def drain_closed(self) -> list[dict[str, Any]]:
        """Hand over closed trades recorded since the last call."""
        out, self._closed = self._closed, []
        return out
