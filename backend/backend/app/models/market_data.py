import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class PriceBar(Base):
    __tablename__ = "price_bars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    sentiment: Mapped[str] = mapped_column(String(20), nullable=True)  # positive/negative/neutral
    symbols: Mapped[str] = mapped_column(String(200), nullable=True)  # comma-separated
    published_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    fetched_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.utcnow
    )


class EconomicEvent(Base):
    __tablename__ = "economic_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    impact: Mapped[str] = mapped_column(String(10), nullable=False)  # low/medium/high
    scheduled_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    actual: Mapped[str] = mapped_column(String(50), nullable=True)
    forecast: Mapped[str] = mapped_column(String(50), nullable=True)
    previous: Mapped[str] = mapped_column(String(50), nullable=True)
    is_released: Mapped[bool] = mapped_column(Boolean, default=False)
