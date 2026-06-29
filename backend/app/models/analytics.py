import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class PerformanceSnapshot(Base):
    __tablename__ = "performance_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    snapshot_date: Mapped[datetime.date] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=True)  # None = all symbols

    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    breakeven_trades: Mapped[int] = mapped_column(Integer, default=0)

    win_rate: Mapped[float] = mapped_column(Float, nullable=True)
    profit_factor: Mapped[float] = mapped_column(Float, nullable=True)
    expectancy: Mapped[float] = mapped_column(Float, nullable=True)  # in R
    average_r: Mapped[float] = mapped_column(Float, nullable=True)

    total_pnl: Mapped[float] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=True)
    max_drawdown_pct: Mapped[float] = mapped_column(Float, nullable=True)

    # Session breakdown
    london_win_rate: Mapped[float] = mapped_column(Float, nullable=True)
    ny_win_rate: Mapped[float] = mapped_column(Float, nullable=True)
    overlap_win_rate: Mapped[float] = mapped_column(Float, nullable=True)
    asia_win_rate: Mapped[float] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.utcnow
    )
