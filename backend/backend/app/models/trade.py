import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY / SELL
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")  # OPEN/CLOSED/CANCELLED

    # Entry
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    entry_time: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    lot_size: Mapped[float] = mapped_column(Float, nullable=False)
    stop_loss: Mapped[float] = mapped_column(Float, nullable=True)
    take_profit: Mapped[float] = mapped_column(Float, nullable=True)

    # Exit
    exit_price: Mapped[float] = mapped_column(Float, nullable=True)
    exit_time: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_reason: Mapped[str] = mapped_column(String(100), nullable=True)

    # P&L
    pnl: Mapped[float] = mapped_column(Float, nullable=True)
    pnl_pct: Mapped[float] = mapped_column(Float, nullable=True)
    r_multiple: Mapped[float] = mapped_column(Float, nullable=True)

    # Metadata
    setup_quality: Mapped[float] = mapped_column(Float, nullable=True)
    risk_reward: Mapped[float] = mapped_column(Float, nullable=True)
    session: Mapped[str] = mapped_column(String(30), nullable=True)
    broker_order_id: Mapped[str] = mapped_column(String(100), nullable=True)


class TradeJournal(Base):
    __tablename__ = "trade_journals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    trade_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)

    # Conditions at trade time
    trend_signal: Mapped[str] = mapped_column(String(20), nullable=True)
    trend_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    structure_signal: Mapped[str] = mapped_column(String(30), nullable=True)
    liquidity_signal: Mapped[str] = mapped_column(String(30), nullable=True)
    smart_money_signal: Mapped[str] = mapped_column(String(30), nullable=True)
    session: Mapped[str] = mapped_column(String(30), nullable=True)
    news_score: Mapped[float] = mapped_column(Float, nullable=True)
    volatility_signal: Mapped[str] = mapped_column(String(20), nullable=True)
    setup_quality: Mapped[float] = mapped_column(Float, nullable=True)

    # AI explanation
    ai_explanation: Mapped[str] = mapped_column(Text, nullable=True)

    # Entry/exit info
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[float] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float] = mapped_column(Float, nullable=True)
    take_profit: Mapped[float] = mapped_column(Float, nullable=True)
    r_multiple: Mapped[float] = mapped_column(Float, nullable=True)
    pnl: Mapped[float] = mapped_column(Float, nullable=True)
    result: Mapped[str] = mapped_column(String(10), nullable=True)  # WIN/LOSS/BE

    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.utcnow, index=True
    )
