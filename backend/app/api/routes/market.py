"""Live gold market data — price, candles, the clock, the calendar."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core.agent import get_agent
from app.core.broker.base import BrokerError
from app.core.market import session as session_clock
from app.core.market.calendar import EconomicCalendar
from app.instrument import DISPLAY_NAME, OANDA_INSTRUMENT, SYMBOL

router = APIRouter()
_calendar = EconomicCalendar()


@router.get("/instrument")
async def instrument():
    agent = get_agent()
    return {
        "symbol": SYMBOL,
        "name": DISPLAY_NAME,
        "broker_instrument": OANDA_INSTRUMENT,
        "price_precision": agent.broker.spec.price_precision
        if hasattr(agent.broker, "spec")
        else 3,
        "unit": "troy ounce",
    }


@router.get("/price")
async def price():
    """Current bid, ask and spread."""
    try:
        quote = await get_agent().broker.get_quote()
    except BrokerError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return quote.as_dict()


@router.get("/candles")
async def candles(
    timeframe: str = Query(default="M15", pattern="^(M1|M5|M15|M30|H1|H4|D1)$"),
    count: int = Query(default=200, ge=10, le=1000),
):
    """Completed OHLC candles. Forming bars are never returned."""
    try:
        bars = await get_agent().broker.get_candles(timeframe, count)
    except BrokerError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {
        "symbol": SYMBOL,
        "timeframe": timeframe,
        "count": len(bars),
        "candles": [b.as_dict() for b in bars],
    }


@router.get("/session")
async def session():
    """Which trading window we are in, and whether entries are allowed."""
    return session_clock.evaluate().as_dict()


@router.get("/calendar")
async def calendar(hours: int = Query(default=48, ge=1, le=168)):
    """Upcoming US releases and whether one is currently blocking trading."""
    blackout = await _calendar.blackout()
    events = await _calendar.upcoming(hours=hours)
    return {
        "source": _calendar.source,
        "blackout": blackout.as_dict(),
        "events": [e.as_dict() for e in events],
    }
