from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.data_collection.economic_calendar import EconomicCalendar
from app.core.data_collection.news_collector import NewsCollector
from app.core.data_collection.price_collector import PriceCollector
from app.database.connection import get_db
from app.services.feature_engineering import enrich_bars

router = APIRouter()


@router.get("/{symbol}")
async def get_market_data(
    symbol: str,
    timeframe: str = Query(default="H1", description="Timeframe: M1, M5, M15, M30, H1, H4, D1"),
    count: int = Query(default=300, ge=10, le=1000),
    enrich: bool = Query(default=False, description="Add EMA/RSI/ATR indicators"),
    db: AsyncSession = Depends(get_db),
):
    """Fetch OHLCV price bars for a symbol."""
    collector = PriceCollector()
    try:
        bars = await collector.fetch(symbol=symbol, timeframe=timeframe, count=count)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch market data: {exc}")

    if enrich:
        bars = enrich_bars(bars)

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(bars),
        "bars": bars,
    }


@router.get("/{symbol}/quote")
async def get_quote(symbol: str):
    """Fetch real-time price quote for a symbol."""
    collector = PriceCollector()
    try:
        quote = await collector.get_quote(symbol=symbol)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return quote


@router.get("/{symbol}/news")
async def get_market_news(
    symbol: str,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Fetch recent news items for a symbol."""
    collector = NewsCollector()
    try:
        news = await collector.fetch(symbols=[symbol], limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch news: {exc}")

    return {"symbol": symbol, "count": len(news), "news": news}


@router.get("/calendar/events")
async def get_economic_calendar(
    currencies: Optional[str] = Query(default=None, description="Comma-separated currency codes"),
    impact: Optional[str] = Query(default=None, description="low, medium, high"),
    days_ahead: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """Fetch upcoming economic calendar events."""
    calendar = EconomicCalendar()
    currency_list = currencies.split(",") if currencies else None
    try:
        events = await calendar.fetch(
            currencies=currency_list,
            impact=impact,
            days_ahead=days_ahead,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch calendar: {exc}")

    return {"count": len(events), "events": events}
