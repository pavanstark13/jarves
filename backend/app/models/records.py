"""Persisted records: what the agent decided, what it traded, what happened."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class TradeRecord(Base):
    """One gold position, from entry to exit."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    broker_trade_id: Mapped[str] = mapped_column(String(64), index=True)
    mode: Mapped[str] = mapped_column(String(10))            # paper | live
    venue: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(10), default="OPEN", index=True)

    direction: Mapped[str] = mapped_column(String(5))        # LONG | SHORT
    units: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    take_profit: Mapped[float] = mapped_column(Float)
    initial_risk: Mapped[float] = mapped_column(Float)       # $/oz entry to stop
    risk_amount: Mapped[float] = mapped_column(Float, default=0.0)

    opened_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    closed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_reason: Mapped[str] = mapped_column(String(32), default="")
    realized_pl: Mapped[float | None] = mapped_column(Float, nullable=True)
    r_multiple: Mapped[float | None] = mapped_column(Float, nullable=True)

    session: Mapped[str] = mapped_column(String(32), default="")
    entry_reason: Mapped[str] = mapped_column(Text, default="")


class DecisionRecord(Base):
    """Every evaluation the agent made, taken or not — the audit trail."""

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    action: Mapped[str] = mapped_column(String(16), index=True)
    executed: Mapped[bool] = mapped_column(Boolean, default=False)
    entry: Mapped[float] = mapped_column(Float, default=0.0)
    stop_loss: Mapped[float] = mapped_column(Float, default=0.0)
    take_profit: Mapped[float] = mapped_column(Float, default=0.0)
    blocker: Mapped[str] = mapped_column(String(255), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class AgentEvent(Base):
    """Lifecycle and error log — starts, stops, halts, rejected orders."""

    __tablename__ = "agent_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    message: Mapped[str] = mapped_column(Text, default="")


class StateRecord(Base):
    """
    Small key/value store for state that must survive a restart — the equity
    peak the drawdown limit is measured from, and any active halt. A crash
    must not hand the agent a clean slate on its risk limits.
    """

    __tablename__ = "agent_state"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
