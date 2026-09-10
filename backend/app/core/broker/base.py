"""
Broker interface.

The agent talks only to this interface, so the identical decision, sizing and
trade-management code runs against the simulator and against OANDA. Any
divergence between paper and live results comes from fills, never from logic.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


class BrokerError(RuntimeError):
    """Raised when the venue rejects a request or cannot be reached."""


@dataclass(frozen=True)
class Candle:
    """One completed OHLC bar. Forming bars are never handed to the strategy."""

    time: dt.datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    complete: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "time": self.time.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


@dataclass(frozen=True)
class Quote:
    """Current two-sided market. `spread` is what an entry actually costs."""

    time: dt.datetime
    bid: float
    ask: float
    tradeable: bool = True

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    @property
    def spread(self) -> float:
        return self.ask - self.bid

    def as_dict(self) -> dict[str, Any]:
        return {
            "time": self.time.isoformat(),
            "bid": round(self.bid, 3),
            "ask": round(self.ask, 3),
            "mid": round(self.mid, 3),
            "spread": round(self.spread, 3),
            "tradeable": self.tradeable,
        }


@dataclass(frozen=True)
class Account:
    balance: float
    nav: float
    unrealized_pl: float
    margin_available: float
    currency: str = "USD"
    venue: str = "unknown"

    def as_dict(self) -> dict[str, Any]:
        return {
            "balance": round(self.balance, 2),
            "nav": round(self.nav, 2),
            "unrealized_pl": round(self.unrealized_pl, 2),
            "margin_available": round(self.margin_available, 2),
            "currency": self.currency,
            "venue": self.venue,
        }


@dataclass
class Position:
    """An open gold position as the venue currently reports it."""

    trade_id: str
    direction: str            # LONG | SHORT
    units: float              # always positive; direction carries the sign
    entry_price: float
    stop_loss: float | None
    take_profit: float | None
    opened_at: dt.datetime
    unrealized_pl: float = 0.0
    initial_risk: float = 0.0     # $/oz between entry and the original stop
    metadata: dict[str, Any] = field(default_factory=dict)

    def r_multiple(self, price: float) -> float:
        """Open profit measured in units of the trade's initial risk."""
        if self.initial_risk <= 0:
            return 0.0
        move = price - self.entry_price if self.direction == "LONG" else self.entry_price - price
        return move / self.initial_risk

    def as_dict(self) -> dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "direction": self.direction,
            "units": self.units,
            "entry_price": round(self.entry_price, 3),
            "stop_loss": round(self.stop_loss, 3) if self.stop_loss else None,
            "take_profit": round(self.take_profit, 3) if self.take_profit else None,
            "opened_at": self.opened_at.isoformat(),
            "unrealized_pl": round(self.unrealized_pl, 2),
            "initial_risk": round(self.initial_risk, 3),
        }


@dataclass(frozen=True)
class OrderResult:
    accepted: bool
    trade_id: str = ""
    fill_price: float = 0.0
    units: float = 0.0
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "trade_id": self.trade_id,
            "fill_price": round(self.fill_price, 3),
            "units": self.units,
            "reason": self.reason,
        }


@runtime_checkable
class MarketClient(Protocol):
    """
    A real venue: everything a Broker does, plus the things only a live
    connection can answer — whether it is configured, what the contract
    actually looks like, and how a trade ended.
    """

    name: str
    spec: Any

    @property
    def configured(self) -> bool: ...

    async def load_instrument_spec(self) -> Any: ...
    async def get_closed_trades(self, count: int = 50) -> list[dict[str, Any]]: ...


@runtime_checkable
class Broker(Protocol):
    """Minimum surface the agent needs from a venue."""

    name: str

    async def get_candles(self, granularity: str, count: int) -> list[Candle]: ...
    async def get_quote(self) -> Quote: ...
    async def get_account(self) -> Account: ...
    async def get_open_positions(self) -> list[Position]: ...
    async def place_order(
        self,
        direction: str,
        units: float,
        stop_loss: float,
        take_profit: float,
        client_id: str,
        reason: str = "",
    ) -> OrderResult: ...
    async def modify_stop(self, trade_id: str, stop_loss: float) -> bool: ...
    async def close_position(self, trade_id: str, reason: str = "") -> OrderResult: ...
