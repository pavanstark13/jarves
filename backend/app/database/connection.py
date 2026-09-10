"""
Database wiring. SQLite by default so the agent runs with no extra services;
point DATABASE_URL at Postgres to move it without touching any other code.
"""

from __future__ import annotations

import pathlib
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


def _prepare_sqlite_path(url: str) -> None:
    """Make sure the directory for a file-backed SQLite database exists."""
    marker = "sqlite+aiosqlite:///"
    if not url.startswith(marker):
        return
    path = url[len(marker):]
    if path in ("", ":memory:"):
        return
    pathlib.Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)


_prepare_sqlite_path(settings.DATABASE_URL)

engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)

SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Create tables on first boot. Schema changes here are additive only."""
    from app.models import records  # noqa: F401  (registers the mappings)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
