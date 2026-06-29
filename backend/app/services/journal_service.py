"""
JournalService — CRUD operations for TradeJournal and Trade models.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import Trade, TradeJournal
from app.schemas.trade import TradeCreate, TradeJournalCreate, TradeUpdate


class JournalService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # --- Trade CRUD ---

    async def create_trade(self, data: TradeCreate) -> Trade:
        trade = Trade(**data.model_dump())
        self._db.add(trade)
        await self._db.flush()
        await self._db.refresh(trade)
        return trade

    async def get_trade(self, trade_id: int) -> Trade | None:
        result = await self._db.execute(select(Trade).where(Trade.id == trade_id))
        return result.scalar_one_or_none()

    async def list_trades(
        self, symbol: str | None = None, status: str | None = None, limit: int = 100
    ) -> list[Trade]:
        stmt = select(Trade)
        if symbol:
            stmt = stmt.where(Trade.symbol == symbol)
        if status:
            stmt = stmt.where(Trade.status == status)
        stmt = stmt.order_by(Trade.entry_time.desc()).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def update_trade(self, trade_id: int, data: TradeUpdate) -> Trade | None:
        trade = await self.get_trade(trade_id)
        if not trade:
            return None
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(trade, field, value)
        await self._db.flush()
        await self._db.refresh(trade)
        return trade

    async def delete_trade(self, trade_id: int) -> bool:
        trade = await self.get_trade(trade_id)
        if not trade:
            return False
        await self._db.delete(trade)
        return True

    # --- Journal CRUD ---

    async def create_journal_entry(self, data: TradeJournalCreate) -> TradeJournal:
        entry = TradeJournal(**data.model_dump())
        self._db.add(entry)
        await self._db.flush()
        await self._db.refresh(entry)
        return entry

    async def get_journal_entry(self, entry_id: int) -> TradeJournal | None:
        result = await self._db.execute(
            select(TradeJournal).where(TradeJournal.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def list_journal_entries(
        self, symbol: str | None = None, result_filter: str | None = None, limit: int = 100
    ) -> list[TradeJournal]:
        stmt = select(TradeJournal)
        if symbol:
            stmt = stmt.where(TradeJournal.symbol == symbol)
        if result_filter:
            stmt = stmt.where(TradeJournal.result == result_filter)
        stmt = stmt.order_by(TradeJournal.created_at.desc()).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def update_journal_entry(
        self, entry_id: int, updates: dict
    ) -> TradeJournal | None:
        entry = await self.get_journal_entry(entry_id)
        if not entry:
            return None
        for field, value in updates.items():
            if hasattr(entry, field):
                setattr(entry, field, value)
        await self._db.flush()
        await self._db.refresh(entry)
        return entry
