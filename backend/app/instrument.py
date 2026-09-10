"""
The one instrument this system trades: spot gold, XAU/USD.

Everything that used to be a per-symbol lookup table lives here as a single
concrete specification. The whole system reasons in **troy ounces**, because
that is the unit gold's price is quoted in: a $1 move on 1 ounce is $1 of P&L,
which makes the risk arithmetic exact.

Venues disagree about how to express size. OANDA takes ounces directly. MT5
takes lots, where one lot is `contract_size` ounces — 100 at most brokers. That
conversion belongs to the broker adapter; nothing above it needs to know.

The defaults below are only a fallback. Each adapter replaces them at startup
with what the venue actually reports for the account, so price rounding and
minimum size always follow the broker rather than an assumption in this file.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

SYMBOL = "XAUUSD"
OANDA_INSTRUMENT = "XAU_USD"
DISPLAY_NAME = "Gold / US Dollar"
QUOTE_CURRENCY = "USD"


@dataclass(frozen=True)
class InstrumentSpec:
    """Contract details needed to size, round and price an order."""

    symbol: str = SYMBOL
    oanda_name: str = OANDA_INSTRUMENT
    # Price decimals the venue accepts. Sending more precision than this is the
    # classic gold integration failure: OANDA wants 3, most MT5 servers 2.
    price_precision: int = 3
    # Smallest meaningful price increment, $/oz.
    tick_size: float = 0.01

    # ── size, always expressed in troy ounces ────────────────────────────────
    units_per_ounce: float = 1.0
    units_precision: int = 0
    # The real granularity the venue enforces. On MT5 this is the volume step
    # multiplied by the contract size (0.01 lots x 100 oz = 1 oz).
    units_step: float = 1.0
    min_trade_units: float = 1.0
    max_trade_units: float = 10_000.0
    # Ounces in one lot. 1.0 for venues that trade ounces directly.
    contract_size: float = 1.0
    # Minimum distance a stop must sit from the market, $/oz. MT5 servers
    # enforce this and reject anything closer; OANDA reports 0.
    min_stop_distance: float = 0.0

    # ── prices ───────────────────────────────────────────────────────────────

    def round_price(self, price: float) -> float:
        return round(float(price), self.price_precision)

    def format_price(self, price: float) -> str:
        return f"{float(price):.{self.price_precision}f}"

    # ── size ─────────────────────────────────────────────────────────────────

    def round_units(self, units: float) -> float:
        """
        Round down to the venue's granularity. Always down: rounding up would
        risk more than the position size was calculated to risk.
        """
        units = float(units)
        if self.units_step > 0:
            units = math.floor(round(units / self.units_step, 9)) * self.units_step
        if self.units_precision <= 0:
            return float(int(units))
        return round(units, self.units_precision)

    def units_to_lots(self, units: float) -> float:
        """Ounces to the lot volume an MT5-style venue expects."""
        if self.contract_size <= 0:
            return float(units)
        return round(float(units) / self.contract_size, 8)

    def lots_to_units(self, lots: float) -> float:
        return round(float(lots) * self.contract_size, 8)

    # ── money ────────────────────────────────────────────────────────────────

    def pnl_for_move(self, price_move: float, units: float) -> float:
        """USD profit for a price move of `price_move` $/oz on `units` ounces."""
        return price_move * units * self.units_per_ounce


# Module-level default; replaced with broker-reported values at startup.
GOLD = InstrumentSpec()
