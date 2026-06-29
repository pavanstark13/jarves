import datetime
from typing import Optional

from pydantic import BaseModel


class TradeCreate(BaseModel):
    symbol: str
    direction: str  # BUY / SELL
    entry_price: float
    entry_time: datetime.datetime
    lot_size: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    setup_quality: Optional[float] = None
    risk_reward: Optional[float] = None
    session: Optional[str] = None
    broker_order_id: Optional[str] = None


class TradeUpdate(BaseModel):
    exit_price: Optional[float] = None
    exit_time: Optional[datetime.datetime] = None
    exit_reason: Optional[str] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    r_multiple: Optional[float] = None
    status: Optional[str] = None


class TradeRead(TradeCreate):
    id: int
    status: str
    exit_price: Optional[float] = None
    exit_time: Optional[datetime.datetime] = None
    exit_reason: Optional[str] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    r_multiple: Optional[float] = None

    model_config = {"from_attributes": True}


class TradeJournalCreate(BaseModel):
    trade_id: int
    symbol: str
    direction: str
    trend_signal: Optional[str] = None
    trend_confidence: Optional[float] = None
    structure_signal: Optional[str] = None
    liquidity_signal: Optional[str] = None
    smart_money_signal: Optional[str] = None
    session: Optional[str] = None
    news_score: Optional[float] = None
    volatility_signal: Optional[str] = None
    setup_quality: Optional[float] = None
    ai_explanation: Optional[str] = None
    entry_price: float
    exit_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    r_multiple: Optional[float] = None
    pnl: Optional[float] = None
    result: Optional[str] = None
    notes: Optional[str] = None


class TradeJournalRead(TradeJournalCreate):
    id: int
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
