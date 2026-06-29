from typing import Optional
import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/performance")
async def get_performance(
    symbol: Optional[str] = Query(default=None),
    since_days: int = Query(default=90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Compute full performance metrics from trade journal.
    Returns win rate, profit factor, expectancy, max drawdown,
    R multiples, and per-session performance.
    """
    since = datetime.datetime.utcnow() - datetime.timedelta(days=since_days)
    service = AnalyticsService(db)
    metrics = await service.compute_performance(symbol=symbol, since=since)
    return metrics


@router.post("/performance/snapshot")
async def save_performance_snapshot(
    symbol: Optional[str] = Query(default=None),
    since_days: int = Query(default=90),
    db: AsyncSession = Depends(get_db),
):
    """Compute performance and persist a snapshot to the database."""
    since = datetime.datetime.utcnow() - datetime.timedelta(days=since_days)
    service = AnalyticsService(db)
    metrics = await service.compute_performance(symbol=symbol, since=since)
    if metrics.get("total_trades", 0) == 0:
        return {"message": "No trades to snapshot"}
    snapshot = await service.save_snapshot(metrics, symbol=symbol)
    return {"snapshot_id": snapshot.id, "metrics": metrics}


@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(get_db)):
    """Quick all-time summary across all symbols."""
    service = AnalyticsService(db)
    return await service.compute_performance()
