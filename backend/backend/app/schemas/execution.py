from typing import Any, Optional

from pydantic import BaseModel


class ExecutionRequest(BaseModel):
    symbol: str
    direction: str  # BUY / SELL
    lot_size: float
    entry_price: Optional[float] = None  # None = market order
    stop_loss: float
    take_profit: float
    trade_id: Optional[int] = None   # internal trade ID if pre-created
    comment: Optional[str] = None


class ModifyOrderRequest(BaseModel):
    broker_order_id: str
    new_stop_loss: Optional[float] = None
    new_take_profit: Optional[float] = None


class CloseOrderRequest(BaseModel):
    broker_order_id: str
    lot_size: Optional[float] = None  # None = full close


class ExecutionResult(BaseModel):
    success: bool
    broker_order_id: Optional[str] = None
    symbol: str
    direction: str
    lot_size: float
    entry_price: Optional[float] = None
    stop_loss: float
    take_profit: float
    error: Optional[str] = None
    raw_response: Optional[dict[str, Any]] = None
