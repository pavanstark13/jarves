from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai.ai_orchestrator import AIOrchestrator
from app.database.connection import get_db
from app.schemas.trade import (
    TradeCreate,
    TradeJournalCreate,
    TradeJournalRead,
    TradeRead,
    TradeUpdate,
)
from app.services.journal_service import JournalService

router = APIRouter()


# --- Trades ---

@router.post("/trades", response_model=TradeRead, status_code=201)
async def create_trade(data: TradeCreate, db: AsyncSession = Depends(get_db)):
    service = JournalService(db)
    return await service.create_trade(data)


@router.get("/trades", response_model=list[TradeRead])
async def list_trades(
    symbol: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    service = JournalService(db)
    return await service.list_trades(symbol=symbol, status=status, limit=limit)


@router.get("/trades/{trade_id}", response_model=TradeRead)
async def get_trade(trade_id: int, db: AsyncSession = Depends(get_db)):
    service = JournalService(db)
    trade = await service.get_trade(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.patch("/trades/{trade_id}", response_model=TradeRead)
async def update_trade(trade_id: int, data: TradeUpdate, db: AsyncSession = Depends(get_db)):
    service = JournalService(db)
    trade = await service.update_trade(trade_id, data)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.delete("/trades/{trade_id}", status_code=204)
async def delete_trade(trade_id: int, db: AsyncSession = Depends(get_db)):
    service = JournalService(db)
    deleted = await service.delete_trade(trade_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Trade not found")


# --- Journal Entries ---

@router.post("/entries", response_model=TradeJournalRead, status_code=201)
async def create_journal_entry(data: TradeJournalCreate, db: AsyncSession = Depends(get_db)):
    service = JournalService(db)
    return await service.create_journal_entry(data)


@router.get("/entries", response_model=list[TradeJournalRead])
async def list_journal_entries(
    symbol: Optional[str] = Query(default=None),
    result: Optional[str] = Query(default=None, description="WIN, LOSS, BE"),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    service = JournalService(db)
    return await service.list_journal_entries(
        symbol=symbol, result_filter=result, limit=limit
    )


@router.get("/entries/{entry_id}", response_model=TradeJournalRead)
async def get_journal_entry(entry_id: int, db: AsyncSession = Depends(get_db)):
    service = JournalService(db)
    entry = await service.get_journal_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return entry


@router.get("/insights")
async def get_journal_insights(
    symbol: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=5, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI-powered insights from trade journal history."""
    service = JournalService(db)
    entries = await service.list_journal_entries(symbol=symbol, limit=limit)

    trades_data = [
        {
            "symbol": e.symbol,
            "direction": e.direction,
            "session": e.session,
            "setup_quality": e.setup_quality,
            "result": e.result,
            "r_multiple": e.r_multiple,
            "pnl": e.pnl,
            "trend_signal": e.trend_signal,
            "structure_signal": e.structure_signal,
        }
        for e in entries
    ]

    try:
        ai = AIOrchestrator()
        insight = ai.generate_journal_insight(trades_data)
    except Exception as exc:
        insight = f"[AI insights unavailable: {exc}]"

    return {"trade_count": len(entries), "insights": insight}
