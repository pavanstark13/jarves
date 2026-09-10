"""
Open-trade management rules, shared by the live agent and the backtest so both
manage a position identically.

The single invariant: a stop only ever moves toward the position. Once risk has
been taken off, it is never put back on.
"""

from __future__ import annotations

from app.config import settings
from app.core.broker.base import Position


def improved_stop(position: Position, price: float, r: float, atr: float) -> float | None:
    """
    The better stop for this position right now, or None if the current one is
    already at least as good.

      * at +1R (BREAKEVEN_AT_R) the stop moves to the entry price;
      * from +1.5R (TRAIL_START_R) it trails the price by an ATR multiple.
    """
    candidate: float | None = None
    if r >= settings.TRAIL_START_R and atr > 0:
        candidate = (
            price - settings.TRAIL_ATR_MULTIPLE * atr
            if position.direction == "LONG"
            else price + settings.TRAIL_ATR_MULTIPLE * atr
        )
    elif r >= settings.BREAKEVEN_AT_R:
        candidate = position.entry_price

    if candidate is None:
        return None

    current = position.stop_loss
    if current is None:
        return candidate
    if position.direction == "LONG":
        return candidate if candidate > current + 1e-6 else None
    return candidate if candidate < current - 1e-6 else None


def time_stop_hit(age_hours: float, r: float) -> bool:
    """A trade that has not reached 1R within the time limit is dead capital."""
    return age_hours >= settings.MAX_TRADE_HOURS and r < settings.BREAKEVEN_AT_R
