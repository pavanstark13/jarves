"""
Storage layer: the agent's memory of what it decided and what it traded.

Kept deliberately small — a handful of queries over three tables. The agent
holds no trading state that is not either in the broker's records or here.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import desc, func, select

from app.core.broker.base import Position
from app.core.risk import RiskVerdict
from app.core.strategy import Decision
from app.database.connection import SessionLocal
from app.models.records import AgentEvent, DecisionRecord, StateRecord, TradeRecord


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _jsonable(value: Any) -> Any:
    """Convert numpy scalars and datetimes so a payload always serialises."""
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dt.datetime):
        return value.isoformat()
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            return value.item()
        except (AttributeError, ValueError):
            return value
    return value


def _aware(value: dt.datetime | None) -> dt.datetime | None:
    """SQLite hands back naive datetimes; treat stored times as UTC."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=dt.timezone.utc)


class Store:
    # ── decisions ─────────────────────────────────────────────────────────────

    async def record_decision(
        self,
        decision: Decision,
        executed: bool = False,
        verdict: RiskVerdict | None = None,
    ) -> None:
        detail = _jsonable(decision.as_dict())
        if verdict is not None:
            detail["risk"] = _jsonable(verdict.as_dict())
        blocker = decision.blocker or (verdict.reason if verdict and not verdict.approved else "")
        async with SessionLocal() as db:
            db.add(
                DecisionRecord(
                    time=decision.time,
                    action=decision.action,
                    executed=executed,
                    entry=decision.entry,
                    stop_loss=decision.stop_loss,
                    take_profit=decision.take_profit,
                    blocker=blocker[:255],
                    summary=decision.summary,
                    detail=detail,
                )
            )
            await db.commit()

    async def recent_decisions(self, limit: int = 50) -> list[dict[str, Any]]:
        async with SessionLocal() as db:
            rows = (
                await db.execute(
                    select(DecisionRecord).order_by(desc(DecisionRecord.time)).limit(limit)
                )
            ).scalars().all()
        return [
            {
                "id": r.id,
                "time": _aware(r.time).isoformat(),
                "action": r.action,
                "executed": r.executed,
                "entry": r.entry,
                "stop_loss": r.stop_loss,
                "take_profit": r.take_profit,
                "blocker": r.blocker,
                "summary": r.summary,
                "detail": r.detail,
            }
            for r in rows
        ]

    # ── trades ────────────────────────────────────────────────────────────────

    async def open_trade(
        self,
        broker_trade_id: str,
        mode: str,
        venue: str,
        direction: str,
        units: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        initial_risk: float,
        risk_amount: float,
        opened_at: dt.datetime,
        session_name: str,
        entry_reason: str,
    ) -> int:
        async with SessionLocal() as db:
            record = TradeRecord(
                broker_trade_id=broker_trade_id,
                mode=mode,
                venue=venue,
                status="OPEN",
                direction=direction,
                units=units,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                initial_risk=initial_risk,
                risk_amount=risk_amount,
                opened_at=opened_at,
                session=session_name,
                entry_reason=entry_reason,
            )
            db.add(record)
            await db.commit()
            return record.id

    async def close_trade(
        self,
        broker_trade_id: str,
        exit_price: float,
        realized_pl: float,
        exit_reason: str,
        closed_at: dt.datetime | None = None,
        r_multiple: float | None = None,
    ) -> dict[str, Any] | None:
        async with SessionLocal() as db:
            record = (
                await db.execute(
                    select(TradeRecord).where(
                        TradeRecord.broker_trade_id == broker_trade_id,
                        TradeRecord.status == "OPEN",
                    )
                )
            ).scalar_one_or_none()
            if record is None:
                return None
            record.status = "CLOSED"
            record.exit_price = exit_price
            record.realized_pl = realized_pl
            record.exit_reason = exit_reason
            record.closed_at = closed_at or _utcnow()
            if r_multiple is None and record.initial_risk > 0:
                move = (
                    exit_price - record.entry_price
                    if record.direction == "LONG"
                    else record.entry_price - exit_price
                )
                r_multiple = move / record.initial_risk
            record.r_multiple = r_multiple
            await db.commit()
            return self._trade_dict(record)

    async def update_stop(self, broker_trade_id: str, stop_loss: float) -> None:
        async with SessionLocal() as db:
            record = (
                await db.execute(
                    select(TradeRecord).where(
                        TradeRecord.broker_trade_id == broker_trade_id,
                        TradeRecord.status == "OPEN",
                    )
                )
            ).scalar_one_or_none()
            if record is not None:
                record.stop_loss = stop_loss
                await db.commit()

    async def open_trades(self, mode: str | None = None) -> list[dict[str, Any]]:
        """
        Trades we believe are open. Filter by mode so a paper run never tries to
        reconcile a live trade, or the other way round.
        """
        async with SessionLocal() as db:
            stmt = select(TradeRecord).where(TradeRecord.status == "OPEN")
            if mode:
                stmt = stmt.where(TradeRecord.mode == mode)
            rows = (await db.execute(stmt)).scalars().all()
        return [self._trade_dict(r) for r in rows]

    async def open_positions(self, mode: str | None = None) -> list[Position]:
        """Rebuild simulator positions after a restart."""
        return [
            Position(
                trade_id=row["broker_trade_id"],
                direction=row["direction"],
                units=row["units"],
                entry_price=row["entry_price"],
                stop_loss=row["stop_loss"],
                take_profit=row["take_profit"],
                opened_at=dt.datetime.fromisoformat(row["opened_at"]),
                initial_risk=row["initial_risk"],
            )
            for row in await self.open_trades(mode)
        ]

    async def trades(self, limit: int = 100, status: str | None = None) -> list[dict[str, Any]]:
        async with SessionLocal() as db:
            stmt = select(TradeRecord).order_by(desc(TradeRecord.opened_at)).limit(limit)
            if status:
                stmt = stmt.where(TradeRecord.status == status.upper())
            rows = (await db.execute(stmt)).scalars().all()
        return [self._trade_dict(r) for r in rows]

    async def realized_pl(self, mode: str | None = None) -> float:
        async with SessionLocal() as db:
            stmt = select(func.coalesce(func.sum(TradeRecord.realized_pl), 0.0)).where(
                TradeRecord.status == "CLOSED"
            )
            if mode:
                stmt = stmt.where(TradeRecord.mode == mode)
            return float((await db.execute(stmt)).scalar_one())

    async def realized_pl_since(self, since: dt.datetime, mode: str | None = None) -> float:
        async with SessionLocal() as db:
            stmt = select(func.coalesce(func.sum(TradeRecord.realized_pl), 0.0)).where(
                TradeRecord.status == "CLOSED", TradeRecord.closed_at >= since
            )
            if mode:
                stmt = stmt.where(TradeRecord.mode == mode)
            return float((await db.execute(stmt)).scalar_one())

    async def trades_opened_since(self, since: dt.datetime) -> int:
        async with SessionLocal() as db:
            stmt = select(func.count(TradeRecord.id)).where(TradeRecord.opened_at >= since)
            return int((await db.execute(stmt)).scalar_one())

    async def consecutive_losses(self) -> int:
        """How many closed trades in a row lost, counting back from the latest."""
        async with SessionLocal() as db:
            rows = (
                await db.execute(
                    select(TradeRecord)
                    .where(TradeRecord.status == "CLOSED")
                    .order_by(desc(TradeRecord.closed_at))
                    .limit(20)
                )
            ).scalars().all()
        streak = 0
        for row in rows:
            if (row.realized_pl or 0.0) < 0:
                streak += 1
            else:
                break
        return streak

    # ── events ────────────────────────────────────────────────────────────────

    async def log_event(self, kind: str, message: str) -> None:
        async with SessionLocal() as db:
            db.add(AgentEvent(kind=kind, message=message[:2000]))
            await db.commit()

    async def events(self, limit: int = 50) -> list[dict[str, Any]]:
        async with SessionLocal() as db:
            rows = (
                await db.execute(select(AgentEvent).order_by(desc(AgentEvent.time)).limit(limit))
            ).scalars().all()
        return [
            {"id": r.id, "time": _aware(r.time).isoformat(), "kind": r.kind, "message": r.message}
            for r in rows
        ]

    # ── durable state ─────────────────────────────────────────────────────────

    async def get_state(self, key: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
        async with SessionLocal() as db:
            record = (
                await db.execute(select(StateRecord).where(StateRecord.key == key))
            ).scalar_one_or_none()
            return dict(record.value) if record else dict(default or {})

    async def set_state(self, key: str, value: dict[str, Any]) -> None:
        async with SessionLocal() as db:
            record = (
                await db.execute(select(StateRecord).where(StateRecord.key == key))
            ).scalar_one_or_none()
            if record is None:
                db.add(StateRecord(key=key, value=value, updated_at=_utcnow()))
            else:
                record.value = value
                record.updated_at = _utcnow()
            await db.commit()

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _trade_dict(record: TradeRecord) -> dict[str, Any]:
        opened = _aware(record.opened_at)
        closed = _aware(record.closed_at)
        return {
            "id": record.id,
            "broker_trade_id": record.broker_trade_id,
            "mode": record.mode,
            "venue": record.venue,
            "status": record.status,
            "direction": record.direction,
            "units": record.units,
            "entry_price": record.entry_price,
            "stop_loss": record.stop_loss,
            "take_profit": record.take_profit,
            "initial_risk": record.initial_risk,
            "risk_amount": record.risk_amount,
            "opened_at": opened.isoformat() if opened else None,
            "closed_at": closed.isoformat() if closed else None,
            "exit_price": record.exit_price,
            "exit_reason": record.exit_reason,
            "realized_pl": record.realized_pl,
            "r_multiple": record.r_multiple,
            "session": record.session,
            "entry_reason": record.entry_reason,
        }


store = Store()
