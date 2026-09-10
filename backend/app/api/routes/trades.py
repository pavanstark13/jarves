"""Trade history and measured performance."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core.agent import get_agent
from app.core.broker.base import BrokerError
from app.services import performance
from app.services.store import store

router = APIRouter()


@router.get("")
async def list_trades(
    limit: int = Query(default=100, ge=1, le=500),
    status: str | None = Query(default=None, pattern="^(OPEN|CLOSED)$"),
):
    return await store.trades(limit=limit, status=status)


@router.get("/open")
async def open_positions():
    """Positions as the broker reports them right now."""
    try:
        positions = await get_agent().broker.get_open_positions()
    except BrokerError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return [p.as_dict() for p in positions]


@router.get("/performance")
async def performance_summary(mode: str | None = Query(default=None, pattern="^(paper|live)$")):
    return await performance.summary(mode)


@router.get("/performance/today")
async def performance_today(mode: str | None = Query(default=None, pattern="^(paper|live)$")):
    return await performance.today(mode)
