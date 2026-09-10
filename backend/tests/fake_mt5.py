"""
A stand-in for the MetaTrader5 package.

MetaQuotes publishes Windows wheels only, so the real package cannot be
imported on Linux or in CI. This mimics the parts the adapter uses — including
the awkward parts: lot-denominated volume, server-time timestamps, per-symbol
filling masks and the deal/position split — so the conversions can be tested
without a terminal.
"""

from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

import numpy as np

# ── constants, matching the real package's values ────────────────────────────
TIMEFRAME_M1, TIMEFRAME_M5, TIMEFRAME_M15, TIMEFRAME_M30 = 1, 5, 15, 30
TIMEFRAME_H1, TIMEFRAME_H4, TIMEFRAME_D1 = 16385, 16388, 16408

ORDER_TYPE_BUY, ORDER_TYPE_SELL = 0, 1
POSITION_TYPE_BUY, POSITION_TYPE_SELL = 0, 1
DEAL_TYPE_BUY, DEAL_TYPE_SELL = 0, 1
DEAL_ENTRY_IN, DEAL_ENTRY_OUT = 0, 1

TRADE_ACTION_DEAL, TRADE_ACTION_SLTP = 1, 6
ORDER_TIME_GTC = 0
ORDER_FILLING_FOK, ORDER_FILLING_IOC, ORDER_FILLING_RETURN = 0, 1, 2
TRADE_RETCODE_DONE = 10009
TRADE_RETCODE_INVALID_STOPS = 10016

SYMBOL_FILLING_FOK, SYMBOL_FILLING_IOC = 1, 2

RATE_DTYPE = np.dtype(
    [("time", "<i8"), ("open", "<f8"), ("high", "<f8"), ("low", "<f8"),
     ("close", "<f8"), ("tick_volume", "<u8"), ("spread", "<i4"), ("real_volume", "<u8")]
)


class FakeTerminal:
    """
    One scripted MT5 terminal. Install it with `install()`, which puts it in
    sys.modules under the name the adapter imports.
    """

    def __init__(
        self,
        symbols: list[str] | None = None,
        server_offset_hours: float = 3.0,   # MultiBank-style UTC+3
        digits: int = 2,
        contract_size: float = 100.0,
        volume_step: float = 0.01,
        volume_min: float = 0.01,
        volume_max: float = 100.0,
        stops_level: float = 0.0,
        filling_mask: int = SYMBOL_FILLING_IOC,
        bid: float = 2400.00,
        ask: float = 2400.30,
        trade_mode: int = 4,
        now: dt.datetime | None = None,
    ) -> None:
        self.symbol_names = symbols if symbols is not None else ["EURUSD", "XAUUSD", "USDJPY"]
        self.server_offset = dt.timedelta(hours=server_offset_hours)
        self.digits = digits
        self.point = 10 ** -digits
        self.contract_size = contract_size
        self.volume_step = volume_step
        self.volume_min = volume_min
        self.volume_max = volume_max
        self.stops_level = stops_level
        self.filling_mask = filling_mask
        self.bid, self.ask = bid, ask
        self.trade_mode = trade_mode
        self.now = now or dt.datetime.now(dt.timezone.utc)

        self.initialized = False
        self.selected: list[str] = []
        self.sent: list[dict] = []          # every order_send request, in order
        self.positions: list[SimpleNamespace] = []
        self.deals: list[SimpleNamespace] = []
        self.error = (0, "no error")
        self.tick_age = dt.timedelta(0)     # push this out to simulate a stale tick
        self._next_ticket = 5_000_100

    # ── module surface ────────────────────────────────────────────────────────

    def install(self, monkeypatch) -> "FakeTerminal":
        import sys
        import types

        module = types.ModuleType("MetaTrader5")
        for name in dir(self):
            if not name.startswith("_") and callable(getattr(self, name)):
                setattr(module, name, getattr(self, name))
        for name, value in globals().items():
            if name.isupper():
                setattr(module, name, value)
        monkeypatch.setitem(sys.modules, "MetaTrader5", module)
        return self

    # ── connection ────────────────────────────────────────────────────────────

    def initialize(self, **kwargs) -> bool:
        self.init_kwargs = kwargs
        self.initialized = True
        return True

    def shutdown(self) -> None:
        self.initialized = False

    def last_error(self) -> tuple[int, str]:
        return self.error

    # ── symbols ───────────────────────────────────────────────────────────────

    def symbols_get(self):
        return [SimpleNamespace(name=name) for name in self.symbol_names]

    def symbol_select(self, name: str, enable: bool = True) -> bool:
        if name not in self.symbol_names:
            return False
        self.selected.append(name)
        return True

    def symbol_info(self, name: str):
        if name not in self.symbol_names:
            return None
        return SimpleNamespace(
            name=name,
            digits=self.digits,
            point=self.point,
            trade_contract_size=self.contract_size,
            volume_step=self.volume_step,
            volume_min=self.volume_min,
            volume_max=self.volume_max,
            trade_stops_level=self.stops_level,
            filling_mode=self.filling_mask,
            trade_mode=self.trade_mode,
        )

    def symbol_info_tick(self, name: str):
        if name not in self.symbol_names:
            return None
        stamp = self.now + self.server_offset - self.tick_age
        return SimpleNamespace(
            time=int(stamp.timestamp()), bid=self.bid, ask=self.ask, last=self.bid
        )

    # ── market data ───────────────────────────────────────────────────────────

    def copy_rates_from_pos(self, name: str, timeframe: int, start: int, count: int):
        """Position 0 is the forming bar; the adapter must ask for 1."""
        minutes = {1: 1, 5: 5, 15: 15, 30: 30, 16385: 60, 16388: 240, 16408: 1440}[timeframe]
        rows = []
        for index in range(count):
            # index 0 is the oldest of the returned window
            bars_back = start + count - 1 - index
            when = self.now + self.server_offset - dt.timedelta(minutes=minutes * bars_back)
            base = 2400.0 - bars_back * 0.1
            rows.append(
                (int(when.timestamp()), base, base + 0.6, base - 0.6, base + 0.2, 500, 30, 0)
            )
        return np.array(rows, dtype=RATE_DTYPE)

    # ── account ───────────────────────────────────────────────────────────────

    def account_info(self):
        return SimpleNamespace(
            balance=10_000.0, equity=10_050.0, profit=50.0,
            margin_free=9_500.0, currency="USD", login=123456,
        )

    # ── positions and orders ──────────────────────────────────────────────────

    def positions_get(self, symbol: str | None = None, ticket: int | None = None):
        found = self.positions
        if ticket is not None:
            found = [p for p in found if p.ticket == ticket]
        if symbol is not None:
            found = [p for p in found if p.symbol == symbol]
        return tuple(found)

    def order_send(self, request: dict):
        self.sent.append(dict(request))

        if request["action"] == TRADE_ACTION_SLTP:
            for position in self.positions:
                if position.ticket == request["position"]:
                    position.sl = request["sl"]
                    return SimpleNamespace(retcode=TRADE_RETCODE_DONE, comment="ok",
                                           order=0, deal=0, price=0.0, volume=0.0)
            return SimpleNamespace(retcode=TRADE_RETCODE_INVALID_STOPS, comment="no position",
                                   order=0, deal=0, price=0.0, volume=0.0)

        closing = request.get("position")
        if closing is not None:
            self.positions = [p for p in self.positions if p.ticket != closing]
            return SimpleNamespace(
                retcode=TRADE_RETCODE_DONE, comment="closed", order=self._ticket(),
                deal=self._ticket(), price=request["price"], volume=request["volume"],
            )

        # A new market order: open a position and record the entry deal.
        ticket = self._ticket()
        deal_ticket = self._ticket()
        is_long = request["type"] == ORDER_TYPE_BUY
        self.positions.append(
            SimpleNamespace(
                ticket=ticket,
                symbol=request["symbol"],
                type=POSITION_TYPE_BUY if is_long else POSITION_TYPE_SELL,
                volume=request["volume"],
                price_open=request["price"],
                sl=request.get("sl", 0.0),
                tp=request.get("tp", 0.0),
                time=int((self.now + self.server_offset).timestamp()),
                profit=0.0,
                magic=request["magic"],
                comment=request.get("comment", ""),
            )
        )
        self.deals.append(
            SimpleNamespace(
                ticket=deal_ticket, position_id=ticket, entry=DEAL_ENTRY_IN,
                type=DEAL_TYPE_BUY if is_long else DEAL_TYPE_SELL,
                volume=request["volume"], price=request["price"],
                profit=0.0, swap=0.0, commission=0.0,
                magic=request["magic"],
                time=int((self.now + self.server_offset).timestamp()),
            )
        )
        return SimpleNamespace(
            retcode=TRADE_RETCODE_DONE, comment="filled", order=ticket,
            deal=deal_ticket, price=request["price"], volume=request["volume"],
        )

    def history_deals_get(self, *args, **kwargs):
        if "ticket" in kwargs:
            return tuple(d for d in self.deals if d.ticket == kwargs["ticket"])
        if "position" in kwargs:
            return tuple(d for d in self.deals if d.position_id == kwargs["position"])
        return tuple(self.deals)

    # ── helpers for tests ─────────────────────────────────────────────────────

    def _ticket(self) -> int:
        self._next_ticket += 1
        return self._next_ticket

    def add_closed_position(
        self, magic: int, entry: float = 2400.0, exit_price: float = 2410.0,
        volume: float = 0.05, profit: float = 50.0, commission: float = -2.0, swap: float = -1.0,
    ) -> int:
        """Record a finished round trip as MT5 would: one entry deal, one exit."""
        position_id = self._ticket()
        opened = self.now + self.server_offset - dt.timedelta(hours=2)
        closed = self.now + self.server_offset - dt.timedelta(hours=1)
        self.deals.append(
            SimpleNamespace(
                ticket=self._ticket(), position_id=position_id, entry=DEAL_ENTRY_IN,
                type=DEAL_TYPE_BUY, volume=volume, price=entry, profit=0.0,
                swap=0.0, commission=commission, magic=magic,
                time=int(opened.timestamp()),
            )
        )
        self.deals.append(
            SimpleNamespace(
                ticket=self._ticket(), position_id=position_id, entry=DEAL_ENTRY_OUT,
                type=DEAL_TYPE_SELL, volume=volume, price=exit_price, profit=profit,
                swap=swap, commission=0.0, magic=magic,
                time=int(closed.timestamp()),
            )
        )
        return position_id
