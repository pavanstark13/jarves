"""
The one instrument this system trades: spot gold, XAU/USD.

Everything that used to be a per-symbol lookup table lives here as a single
concrete specification. Defaults match OANDA's published XAU_USD contract and
are replaced at runtime by whatever the broker actually reports for the
account (see OandaClient.load_instrument_spec), so sizing and price rounding
always follow the venue rather than an assumption baked into the code.
"""

from __future__ import annotations

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
    # Price decimals accepted by the venue. OANDA rejects orders priced more
    # precisely than this, which is the classic gold integration failure.
    price_precision: int = 3
    # Smallest meaningful price increment, $/oz.
    tick_size: float = 0.01
    # One unit is one troy ounce, so a $1 move on 1 unit is $1 of P&L.
    units_per_ounce: float = 1.0
    # Whole ounces only.
    units_precision: int = 0
    min_trade_units: float = 1.0
    max_trade_units: float = 10_000.0

    def round_price(self, price: float) -> float:
        return round(float(price), self.price_precision)

    def round_units(self, units: float) -> float:
        """Round toward zero so sizing never exceeds the intended risk."""
        if self.units_precision <= 0:
            return float(int(units))
        factor = 10 ** self.units_precision
        return int(units * factor) / factor

    def format_price(self, price: float) -> str:
        return f"{float(price):.{self.price_precision}f}"

    def pnl_for_move(self, price_move: float, units: float) -> float:
        """USD profit for a price move of `price_move` $/oz on `units` ounces."""
        return price_move * units * self.units_per_ounce


# Module-level default; replaced with broker-reported values at startup.
GOLD = InstrumentSpec()
