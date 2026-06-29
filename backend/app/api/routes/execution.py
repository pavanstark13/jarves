from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.execution.execution_engine import ExecutionEngine
from app.core.risk.risk_engine import RiskEngine
from app.database.connection import get_db
from app.schemas.execution import (
    CloseOrderRequest,
    ExecutionRequest,
    ExecutionResult,
    ModifyOrderRequest,
)
from app.schemas.risk import RiskCheckRequest, RiskCheckResult

router = APIRouter()
_execution_engine = ExecutionEngine()
_risk_engine = RiskEngine()


@router.post("/place", response_model=ExecutionResult)
async def place_order(
    execution_request: ExecutionRequest,
    risk_result: RiskCheckResult,
    db: AsyncSession = Depends(get_db),
):
    """
    Place a trade order.  Requires a pre-computed RiskCheckResult.
    The ExecutionEngine will refuse to place the order if risk_result.approved is False.
    """
    if not risk_result.approved:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot execute: risk check not approved. Reason: {risk_result.rejection_reason}",
        )

    result = _execution_engine.place_order(execution_request, risk_result)
    if not result.success:
        raise HTTPException(status_code=502, detail=result.error)
    return result


@router.post("/modify")
async def modify_order(request: ModifyOrderRequest, db: AsyncSession = Depends(get_db)):
    """Modify an existing order's SL/TP."""
    return _execution_engine.modify_order(request)


@router.post("/close")
async def close_order(request: CloseOrderRequest, db: AsyncSession = Depends(get_db)):
    """Close an open position (fully or partially)."""
    return _execution_engine.close_order(request)


@router.post("/breakeven/{broker_order_id}")
async def move_to_breakeven(
    broker_order_id: str,
    entry_price: float,
    db: AsyncSession = Depends(get_db),
):
    """Move stop loss to entry price (breakeven)."""
    return _execution_engine.move_to_breakeven(broker_order_id, entry_price)
