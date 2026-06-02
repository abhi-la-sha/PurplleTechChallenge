"""Domain-layer test fixtures (in-memory async SQLite)."""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles

from app.db.base import Base
from app.models import Camera, Event, Transaction, VisitorSession, Zone  # noqa: F401


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(_type: JSONB, compiler: object, **kwargs: object) -> str:
    """Map PostgreSQL JSONB to SQLite JSON for in-memory domain tests."""
    return "JSON"


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()
