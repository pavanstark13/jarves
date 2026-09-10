"""Test configuration — an isolated on-disk database, no network, no real broker."""

from __future__ import annotations

import os
import pathlib
import tempfile

# Must be set before app.config is imported anywhere.
_TMP_DB = pathlib.Path(tempfile.mkdtemp(prefix="jarves-test-")) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP_DB}"
os.environ["AGENT_MODE"] = "paper"
os.environ["EXECUTION_CONFIRMED"] = "false"
os.environ["FCS_API_KEY"] = ""

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402

from app.database.connection import Base, engine  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def fresh_database():
    """Every test starts from an empty schema."""
    import app.models.records  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def anyio_backend():
    return "asyncio"
